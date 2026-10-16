import { useEffect, useState } from "react";

type Health = { status: string };

export default function App() {
  const [status, setStatus] = useState<string>("...");

  useEffect(() => {
    fetch("/healthz")
      .then((r) => (r.ok ? (r.json() as Promise<Health>) : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((h) => setStatus(h.status))
      .catch((e: unknown) => setStatus(`error: ${e instanceof Error ? e.message : String(e)}`));
  }, []);

  return (
    <main style={{ fontFamily: "monospace", background: "#000", color: "#33ff33", minHeight: "100vh", padding: "1rem" }}>
      <h1>bookterm</h1>
      <p>
        api: <span data-testid="health">{status}</span>
      </p>
    </main>
  );
}
