import { NextResponse } from "next/server";
import { getSsoSession } from "@/lib/sso";

export async function GET(request: Request) {
  return NextResponse.json(await getSsoSession(request));
}
