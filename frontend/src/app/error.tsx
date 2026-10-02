"use client";

import { RefreshCw, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { useEffect } from "react";

export default function RouteError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.warn("Route error boundary:", error.message);
  }, [error]);
  return (
    <div className="mx-auto flex max-w-xl flex-col items-center px-6 py-24 text-center">
      <div className="mb-5 rounded-full bg-[#fbe9e5] p-4 text-coral">
        <TriangleAlert className="h-8 w-8" />
      </div>
      <h1 className="text-3xl text-night">Something went wrong</h1>
      <p className="mt-3 text-ink-soft">This section failed to load. The rest of PolarNexus is still available — you can retry or head back to Explore.</p>
      <div className="mt-6 flex gap-3">
        <button onClick={reset} className="inline-flex h-10 items-center gap-2 rounded-lg bg-cyan-deep px-4 text-sm font-medium text-white hover:bg-[#0c6f8e]">
          <RefreshCw className="h-4 w-4" /> Retry
        </button>
        <Link href="/explore" className="inline-flex h-10 items-center rounded-lg border border-frost bg-white px-4 text-sm font-medium text-night hover:bg-ice">
          Go to Explore
        </Link>
      </div>
    </div>
  );
}
