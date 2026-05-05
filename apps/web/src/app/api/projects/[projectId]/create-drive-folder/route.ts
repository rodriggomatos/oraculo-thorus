import { NextRequest, NextResponse } from "next/server";
import { proxyToBackend } from "@/lib/backend";
import type { CreateDriveFolderResponse } from "@/features/create-project/types";


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
    `/projects/${encodeURIComponent(projectId)}/create-drive-folder`,
    { method: "POST", body: {} },
  );

  if (!upstream.ok) {
    return upstream;
  }

  const data = (await upstream.json()) as {
    folder_id: string;
    folder_url: string;
    folder_name: string;
  };

  const remapped: CreateDriveFolderResponse = {
    folderId: data.folder_id,
    folderUrl: data.folder_url,
    folderName: data.folder_name,
  };

  return NextResponse.json(remapped, { status: 200 });
}
