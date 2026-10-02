"use client";

export default function GlobalError({ reset }: { error: Error; reset: () => void }) {
  return (
    <html lang="en">
      <body style={{ fontFamily: "system-ui, sans-serif", background: "#f6fafc", color: "#0e2233" }}>
        <div style={{ maxWidth: 520, margin: "96px auto", padding: 24, textAlign: "center" }}>
          <h1 style={{ fontSize: 28, marginBottom: 12 }}>Something went wrong</h1>
          <p style={{ color: "#3d566b" }}>PolarNexus hit an unexpected error. Please retry.</p>
          <button
            onClick={reset}
            style={{ marginTop: 20, background: "#0f7fa1", color: "#fff", border: 0, borderRadius: 8, padding: "10px 18px", cursor: "pointer" }}
          >
            Retry
          </button>
        </div>
      </body>
    </html>
  );
}
