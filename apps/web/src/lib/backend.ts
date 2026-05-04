import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";


export async function proxyToBackend(
  request: NextRequest,
  path: string,
  options: { method?: string; body?: unknown } = {},
): Promise<NextResponse> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const auth = request.headers.get("authorization");
  if (auth) headers["Authorization"] = auth;

  const init: RequestInit = {
    method: options.method ?? request.method,
    headers,
  };
  if (options.body !== undefined) {
    init.body = JSON.stringify(options.body);
  } else if (request.method !== "GET" && request.method !== "HEAD") {
    const text = await request.text();
    if (text) init.body = text;
  }

  let response: Response;
  try {
    response = await fetch(`${BACKEND_URL}${path}`, init);
  } catch (e) {
    return NextResponse.json(
      {
        error: "Backend indisponível",
        detail: e instanceof Error ? e.message : String(e),
      },
      { status: 502 },
    );
  }

  const text = await response.text();
  let payload: unknown;
  try {
    payload = text ? JSON.parse(text) : null;
  } catch {
    payload = { raw: text };
  }

  return NextResponse.json(payload, { status: response.status });
}
