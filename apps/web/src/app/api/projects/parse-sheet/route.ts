import { NextRequest, NextResponse } from "next/server";
import type { ValidationResult } from "@/features/create-project/types";

// MOCK: substituir por chamada real ao backend (apps/ai) quando pronto.
// Backend deveria baixar a planilha do Drive, parsear via document_ai e
// retornar inconsistências reais detectadas pelo schema validator.

async function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function POST(_request: NextRequest): Promise<NextResponse<ValidationResult>> {
  await delay(1200);

  const result: ValidationResult = {
    ok: false,
    errors: [],
    warnings: [
      {
        code: "discipline_not_in_template",
        message: "Disciplina 'Geotermia' não está no template oficial Thórus",
        field: "disciplina",
        value: "Geotermia",
      },
      {
        code: "invalid_value",
        message: "Coluna 'legal' tem valor 'misto' (esperado: executivo ou legal)",
        field: "legal",
        value: "misto",
      },
    ],
  };

  return NextResponse.json(result);
}
