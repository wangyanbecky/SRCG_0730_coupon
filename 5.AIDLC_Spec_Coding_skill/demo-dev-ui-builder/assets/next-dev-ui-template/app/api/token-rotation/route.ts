import { NextResponse } from "next/server";
import { readConfig } from "@/lib/config";
import { unauthorizedIfNoSso } from "@/lib/sso";

export async function POST(request: Request) {
  const unauthorized = await unauthorizedIfNoSso(request);
  if (unauthorized) return unauthorized;
  const config = await readConfig();
  if (!config.endpoints.tokenRotationUrl) {
    return NextResponse.json({ error: "Token rotation URL is not configured" }, { status: 400 });
  }

  const response = await fetch(config.endpoints.tokenRotationUrl, { method: "POST" });
  return NextResponse.json({ ok: response.ok, status: response.status });
}
