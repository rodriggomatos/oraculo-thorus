import { NextRequest, NextResponse } from "next/server";
import { proxyToBackend } from "@/lib/backend";

export async function POST(request: NextRequest): Promise<NextResponse> {
  return proxyToBackend(request, "/projects/suggest-number");
}
