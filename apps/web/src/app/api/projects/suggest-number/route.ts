import { NextResponse } from "next/server";
import type { SuggestNumberResponse } from "@/features/create-project/types";

// MOCK: substituir por chamada real ao backend (apps/ai) quando pronto.
// Backend deveria consultar projects table e retornar próximo número disponível.

async function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function POST(): Promise<NextResponse<SuggestNumberResponse>> {
  await delay(600);
  return NextResponse.json({ suggested: 26024 });
}
