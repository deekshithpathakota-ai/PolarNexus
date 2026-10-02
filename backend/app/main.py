"""PolarNexus API — FastAPI application entry point."""
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.api import admin, ai, auth, ingestion, knowledge, misc, workflow
from app.core.config import settings
from app.core.database import Base, SessionLocal, detect_vector_backend, engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("polarnexus")

@asynccontextmanager
async def lifespan(_: FastAPI):
    startup()
    yield


app = FastAPI(
    lifespan=lifespan,
    title="PolarNexus API",
    version="1.0.0",
    description="Evidence-grounded polar knowledge repository, discovery, AI assistance and outreach workflow (SIH26063 prototype).",
)

app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def timing_and_security_headers(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Server-Timing"] = f"app;dur={(time.perf_counter() - start) * 1000:.1f}"
    return response


@app.exception_handler(HTTPException)
async def http_error(_: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail, "status": exc.status_code})


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    msgs = []
    for e in exc.errors():
        loc = ".".join(str(x) for x in e.get("loc", []) if x not in {"body", "query", "path"})
        msgs.append(f"{loc}: {e.get('msg')}" if loc else e.get("msg"))
    return JSONResponse(status_code=422, content={"detail": "; ".join(msgs) or "Invalid request.", "status": 422})


@app.exception_handler(Exception)
async def unhandled(_: Request, exc: Exception):
    log.exception("Unhandled error: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Something went wrong on the server. Please try again.", "status": 500})


def startup() -> None:
    detect_vector_backend()
    Base.metadata.create_all(engine)
    if settings.DEMO_MODE:
        from app.seed.seed_demo_data import run

        result = run(if_empty=True)
        if result:
            log.info("Empty database detected — demo data seeded: %s", result)
    with SessionLocal() as db:
        from app.rag.indexer import ensure_fulltext_index

        try:
            ensure_fulltext_index(db)
        except Exception as exc:  # non-fatal
            log.warning("Could not create full-text index: %s", exc)
    if settings.JWT_SECRET == "dev-only-change-me" and settings.ENVIRONMENT == "production":
        log.warning("JWT_SECRET is using the development default — set a strong secret in production!")


for r in (auth.router, knowledge.router, misc.router, ai.router, workflow.router, ingestion.router, admin.router):
    app.include_router(r)


@app.get("/")
def root():
    return {"name": "PolarNexus API", "docs": "/docs", "health": "/health"}
