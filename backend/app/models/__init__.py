from app.models.knowledge import (  # noqa: F401
    Dataset,
    DatasetRecord,
    Document,
    DocumentChunk,
    EmbeddingModelStore,
    Expedition,
    InstitutionalActivity,
    Media,
    Provenance,
    Researcher,
    ResourceLink,
    ResourceTopic,
    Station,
    Topic,
)
from app.models.telemetry import AIQuery, AnalyticsEvent, AuditLog, SearchLog  # noqa: F401
from app.models.user import Role, User  # noqa: F401
from app.models.workflow import (  # noqa: F401
    Citation,
    GeneratedContent,
    IngestionJob,
    Notification,
    Review,
    SavedItem,
)

RESOURCE_MODELS = {
    "document": Document,
    "dataset": Dataset,
    "media": Media,
    "expedition": Expedition,
    "station": Station,
    "researcher": Researcher,
    "topic": Topic,
    "activity": InstitutionalActivity,
}
