import { NextRequest, NextResponse } from "next/server";
import type {
  CreateProjectRequest,
  CreateProjectResponse,
} from "@/features/create-project/types";

// MOCK: substituir por chamada real ao backend (apps/ai) quando pronto.
// Backend deveria: criar registro na tabela projects, persistir metadata,
// preparar pasta no Drive (próximo sprint) e retornar projectId real.

async function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function POST(
  request: NextRequest,
): Promise<NextResponse<CreateProjectResponse | { error: string }>> {
  await delay(1500);

  const body = (await request.json()) as Partial<CreateProjectRequest>;
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

  const response: CreateProjectResponse = {
    projectId: `mock-${body.confirmedNumber}-${Date.now()}`,
    projectNumber: body.confirmedNumber,
    totalContratado: 147387.5,
    margem: 24.33,
    driveFolderPending: true,
  };

  return NextResponse.json(response);
}
