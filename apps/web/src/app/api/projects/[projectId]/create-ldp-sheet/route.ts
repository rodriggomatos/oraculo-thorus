import { NextRequest, NextResponse } from "next/server";
import { proxyToBackend } from "@/lib/backend";
import type { CreateLdpSheetResponse } from "@/features/create-project/types";


export async function POST(
  request: NextRequest,
  context: { params: Promise<{ projectId: string }> },
): Promise<NextResponse> {
  const { projectId } = await context.params;
  if (!projectId) {
    return NextResponse.json({ error: "projectId ausente" }, { status: 400 });
  }

  const upstream = await proxyToBackend(
    request,
    `/projects/${encodeURIComponent(projectId)}/create-ldp-sheet`,
    { method: "POST", body: {} },
  );

  if (!upstream.ok) {
    return upstream;
  }

  const data = (await upstream.json()) as {
    sheets_id: string;
    sheets_url: string;
    sheets_name: string;
    rows_written: number;
  };

  const remapped: CreateLdpSheetResponse = {
    sheetsId: data.sheets_id,
    sheetsUrl: data.sheets_url,
    sheetsName: data.sheets_name,
    rowsWritten: data.rows_written,
  };

  return NextResponse.json(remapped, { status: 200 });
}
