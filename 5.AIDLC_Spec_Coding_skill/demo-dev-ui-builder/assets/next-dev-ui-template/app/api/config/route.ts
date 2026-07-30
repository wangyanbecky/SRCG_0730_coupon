import { NextResponse } from "next/server";
import { readConfig, writeConfig } from "@/lib/config";
import { unauthorizedIfNoSso } from "@/lib/sso";

export async function GET(request: Request) {
  const unauthorized = await unauthorizedIfNoSso(request);
  if (unauthorized) return unauthorized;
  return NextResponse.json(await readConfig());
}

export async function POST(request: Request) {
  const unauthorized = await unauthorizedIfNoSso(request);
  if (unauthorized) return unauthorized;
  const config = await request.json();
  await writeConfig(config);
  return NextResponse.json({ ok: true, config });
}
