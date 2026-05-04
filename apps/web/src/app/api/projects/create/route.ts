import { NextRequest, NextResponse } from "next/server";
import { proxyToBackend } from "@/lib/backend";
import type {
  CreateProjectRequest,
  CreateProjectResponse,
} from "@/features/create-project/types";


export async function POST(request: NextRequest): Promise<NextResponse> {
  const body = (await request.json().catch(() => ({}))) as Partial<CreateProjectRequest>;
  if (
    typeof body.confirmedNumber !== "number" ||
    typeof body.spreadsheetId !== "string" ||
    !body.metadata
  ) {
    return NextResponse.json(
      { error: "campos obrigatórios ausentes" },
      { status: 400 },
    );
  }

  const upstream = await proxyToBackend(request, "/projects/create", {
    method: "POST",
    body: {
      spreadsheet_id: body.spreadsheetId,
      confirmed_number: body.confirmedNumber,
      metadata: body.metadata,
    },
  });

  if (!upstream.ok) {
    return upstream;
  }

  const data = (await upstream.json()) as {
    project_id: string;
    project_number: number;
    total_contratado: number | null;
    margem: number | null;
    drive_folder_pending: boolean;
  };

  const remapped: CreateProjectResponse = {
    projectId: data.project_id,
    projectNumber: data.project_number,
    totalContratado: data.total_contratado ?? 0,
    margem: data.margem ?? 0,
    driveFolderPending: data.drive_folder_pending,
  };

  return NextResponse.json(remapped, { status: 200 });
}
