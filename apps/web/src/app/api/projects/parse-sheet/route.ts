import { NextRequest, NextResponse } from "next/server";
import { proxyToBackend } from "@/lib/backend";


type IncomingPayload = {
  spreadsheetId?: string;
  spreadsheet_id?: string;
};


export async function POST(request: NextRequest): Promise<NextResponse> {
  const incoming = (await request.json().catch(() => ({}))) as IncomingPayload;
  const spreadsheet_id = incoming.spreadsheet_id ?? incoming.spreadsheetId;
  if (!spreadsheet_id) {
    return NextResponse.json(
      { error: "spreadsheet_id obrigatório" },
      { status: 400 },
    );
  }

  const upstream = await proxyToBackend(request, "/projects/parse-sheet", {
    method: "POST",
    body: { spreadsheet_id },
  });

  if (!upstream.ok) {
    return upstream;
  }

  const data = (await upstream.json()) as {
    validation: { ok: boolean; errors: unknown[]; warnings: unknown[] };
  };
  return NextResponse.json(data.validation, { status: 200 });
}
