"use client";

import { RotateCw, Save } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import type { DemoUiConfig } from "@/lib/config";
import { UserMenu } from "@/components/UserMenu";

export default function SettingsPage() {
  const [config, setConfig] = useState<DemoUiConfig | null>(null);
  const [message, setMessage] = useState("");

  useEffect(() => {
    fetch("/api/config").then((response) => response.json()).then(setConfig);
  }, []);

  async function save() {
    await fetch("/api/config", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(config)
    });
    setMessage("Settings saved");
  }

  async function rotateToken() {
    if (!config?.endpoints.tokenRotationUrl) return;
    const response = await fetch("/api/token-rotation", { method: "POST" });
    setMessage(response.ok ? "Token rotation requested" : "Token rotation failed");
  }

  if (!config) return <main className="shell">Loading settings...</main>;

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Configuration</p>
          <h1>Settings</h1>
        </div>
        <nav>
          <Link href="/">Dashboard</Link>
          <Link href="/settings">Settings</Link>
          <UserMenu />
        </nav>
      </header>

      <section className="settings-grid">
        <div className="panel">
          <h2>Endpoints</h2>
          {Object.entries(config.endpoints).map(([key, value]) => (
            <label key={key}>
              <span>{key}</span>
              <input
                value={value ?? ""}
                onChange={(event) =>
                  setConfig({ ...config, endpoints: { ...config.endpoints, [key]: event.target.value } })
                }
              />
            </label>
          ))}
        </div>

        <div className="panel">
          <h2>Runtime</h2>
          {Object.entries(config.runtime).map(([key, value]) => (
            <label key={key}>
              <span>{key}</span>
              <input
                type="number"
                value={value}
                onChange={(event) =>
                  setConfig({ ...config, runtime: { ...config.runtime, [key]: Number(event.target.value) } })
                }
              />
            </label>
          ))}
        </div>

        <div className="panel">
          <h2>Features</h2>
          {Object.entries(config.features).map(([key, value]) => (
            <label className="switch-row" key={key}>
              <span>{key}</span>
              <input
                type="checkbox"
                checked={value}
                onChange={(event) =>
                  setConfig({ ...config, features: { ...config.features, [key]: event.target.checked } })
                }
              />
            </label>
          ))}
        </div>
      </section>

      <section className="actions">
        <button className="primary" onClick={save}>
          <Save size={16} /> Save settings
        </button>
        {config.endpoints.tokenRotationUrl ? (
          <button onClick={rotateToken}>
            <RotateCw size={16} /> Rotate API token
          </button>
        ) : null}
        <span>{message}</span>
      </section>
    </main>
  );
}
