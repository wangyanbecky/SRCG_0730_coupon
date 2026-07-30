import { NextResponse } from "next/server";
import { readConfig } from "@/lib/config";
import { unauthorizedIfNoSso } from "@/lib/sso";

export async function POST(request: Request) {
  const unauthorized = await unauthorizedIfNoSso(request);
  if (unauthorized) return unauthorized;
  const config = await readConfig();
  const payload = await request.json();
  const response = await fetch(config.endpoints.testSessionUrl, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload)
  });

  const body = await response.text();
  return NextResponse.json({
    ok: response.ok,
    status: response.status,
    body,
    receivedAt: new Date().toISOString()
  });
}
