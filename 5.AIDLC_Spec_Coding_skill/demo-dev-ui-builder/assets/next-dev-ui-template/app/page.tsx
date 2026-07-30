"use client";

import { Activity, Cable, CircleStop, Play, RefreshCw, Send, Trash2 } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { UserMenu } from "@/components/UserMenu";

type LogEntry = {
  ts: string;
  level: "info" | "warn" | "error";
  message: string;
};

type HealthResponse = {
  frontend: { ok: boolean; checkedAt: string };
  checks: Array<{ url: string; ok: boolean; status: number; latencyMs: number; checkedAt: string; error?: string }>;
};

type RequestRecord = {
  id: string;
  route: string;
  sizeKb: number;
  status: number;
  durationMs: number;
  createdAt: string;
};

const starterPayload = JSON.stringify({ action: "run-demo", input: { id: "sample-001" } }, null, 2);

export default function DashboardPage() {
  const [payload, setPayload] = useState(starterPayload);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [requests, setRequests] = useState<RequestRecord[]>([]);
  const [sessionState, setSessionState] = useState<"disconnected" | "connected" | "running">("disconnected");
  const [health, setHealth] = useState<HealthResponse | null>(null);

  const statusTone = useMemo(() => {
    if (sessionState === "connected") return "good";
    if (sessionState === "running") return "busy";
    return "muted";
  }, [sessionState]);

  function append(level: LogEntry["level"], message: string) {
    setLogs((current) => [...current, { ts: new Date().toISOString(), level, message }]);
  }

  async function refreshHealth() {
    append("info", "Checking system health");
    const response = await fetch("/api/health", { cache: "no-store" });
    setHealth(await response.json());
  }

  async function runTest() {
    setSessionState("running");
    append("info", "Submitting end-to-end test payload");
    const started = performance.now();
    try {
      const response = await fetch("/api/test-session", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: payload
      });
      const data = await response.json();
      setRequests((current) => [
        {
          id: crypto.randomUUID(),
          route: "/api/test-session",
          sizeKb: Math.max(1, Math.round(new Blob([payload]).size / 1024)),
          status: data.status,
          durationMs: Math.round(performance.now() - started),
          createdAt: new Date().toISOString()
        },
        ...current
      ].slice(0, 20));
      append(data.ok ? "info" : "error", `Test response ${data.status}: ${data.body.slice(0, 500)}`);
    } catch (error) {
      append("error", error instanceof Error ? error.message : "Unknown request failure");
    } finally {
      setSessionState("connected");
    }
  }

  useEffect(() => {
    refreshHealth();
  }, []);

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Developer Console</p>
          <h1>Demo System Test UI</h1>
        </div>
        <nav>
          <Link href="/">Dashboard</Link>
          <Link href="/settings">Settings</Link>
          <UserMenu />
        </nav>
      </header>

      <section className="status-strip">
        <div className={`status-pill ${statusTone}`}>
          <Cable size={16} />
          {sessionState}
        </div>
        <button onClick={() => { setSessionState("connected"); append("info", "Session connected"); }}>
          <Play size={16} /> Connect
        </button>
        <button onClick={() => { setSessionState("disconnected"); append("warn", "Session disconnected"); }}>
          <CircleStop size={16} /> Disconnect
        </button>
        <button onClick={() => { setSessionState("connected"); append("info", "Session reconnected"); }}>
          <RefreshCw size={16} /> Reconnect
        </button>
      </section>

      <section className="workbench">
        <div className="panel">
          <div className="panel-head">
            <h2>End-to-end input</h2>
            <button className="primary" onClick={runTest}>
              <Send size={16} /> Send
            </button>
          </div>
          <textarea value={payload} onChange={(event) => setPayload(event.target.value)} spellCheck={false} />
        </div>

        <div className="panel">
          <div className="panel-head">
            <h2>Execution log</h2>
            <button onClick={() => setLogs([])}>
              <Trash2 size={16} /> Clear
            </button>
          </div>
          <div className="logbox">
            {logs.map((entry, index) => (
              <div className={`log ${entry.level}`} key={`${entry.ts}-${index}`}>
                <span>{entry.ts}</span>
                <strong>{entry.level.toUpperCase()}</strong>
                <p>{entry.message}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="monitor">
        <div className="section-head">
          <div>
            <p className="eyebrow">System</p>
            <h2>Frontend and backend status</h2>
          </div>
          <button onClick={refreshHealth}>
            <Activity size={16} /> Check now
          </button>
        </div>
        <div className="grid">
          <article className="metric">
            <span>Frontend</span>
            <strong>{health?.frontend.ok ? "Healthy" : "Unknown"}</strong>
            <p>{health?.frontend.checkedAt ?? "Not checked"}</p>
          </article>
          {health?.checks.map((check) => (
            <article className="metric" key={check.url}>
              <span>{check.url}</span>
              <strong>{check.ok ? "Healthy" : "Failing"}</strong>
              <p>{check.status} - {check.latencyMs}ms</p>
            </article>
          ))}
        </div>
      </section>

      <section className="monitor">
        <div className="section-head">
          <div>
            <p className="eyebrow">Diagnostics</p>
            <h2>Large request log</h2>
          </div>
        </div>
        <div className="table">
          <div className="table-row table-head">
            <span>Request id</span>
            <span>Route</span>
            <span>Size</span>
            <span>Status</span>
            <span>Duration</span>
            <span>Time</span>
          </div>
          {requests.map((request) => (
            <div className="table-row" key={request.id}>
              <span>{request.id.slice(0, 8)}</span>
              <span>{request.route}</span>
              <span>{request.sizeKb} KB</span>
              <span>{request.status}</span>
              <span>{request.durationMs} ms</span>
              <span>{request.createdAt}</span>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
