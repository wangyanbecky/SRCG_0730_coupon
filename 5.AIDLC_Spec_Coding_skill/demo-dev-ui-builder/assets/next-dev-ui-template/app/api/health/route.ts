import { NextResponse } from "next/server";
import { readConfig } from "@/lib/config";
import { unauthorizedIfNoSso } from "@/lib/sso";

async function check(url: string, timeoutMs: number) {
  const started = Date.now();
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, { cache: "no-store", signal: controller.signal });
    return {
      url,
      ok: response.ok,
      status: response.status,
      latencyMs: Date.now() - started,
      checkedAt: new Date().toISOString()
    };
  } catch (error) {
    return {
      url,
      ok: false,
      status: 0,
      latencyMs: Date.now() - started,
      error: error instanceof Error ? error.message : "Unknown error",
      checkedAt: new Date().toISOString()
    };
  } finally {
    clearTimeout(timeout);
  }
}

export async function GET(request: Request) {
  const unauthorized = await unauthorizedIfNoSso(request);
  if (unauthorized) return unauthorized;
  const config = await readConfig();
  const checks = await Promise.all([
    check(config.endpoints.healthUrl, config.runtime.requestTimeoutMs),
    check(config.endpoints.apiBaseUrl, config.runtime.requestTimeoutMs)
  ]);

  return NextResponse.json({
    frontend: { ok: true, checkedAt: new Date().toISOString() },
    checks
  });
}
