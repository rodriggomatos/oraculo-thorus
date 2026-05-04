import type {
  CreateProjectRequest,
  CreateProjectResponse,
  ProjectMetadata,
  SuggestNumberResponse,
  ValidationResult,
} from "./types";


const API_BASE = "/api/projects";


export async function suggestNumber(): Promise<SuggestNumberResponse> {
  const response = await fetch(`${API_BASE}/suggest-number`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    throw new Error(`POST /suggest-number falhou (${response.status})`);
  }
  return (await response.json()) as SuggestNumberResponse;
}


export async function parseSpreadsheet(
  spreadsheetId: string,
): Promise<ValidationResult> {
  const response = await fetch(`${API_BASE}/parse-sheet`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ spreadsheetId }),
  });
  if (!response.ok) {
    throw new Error(`POST /parse-sheet falhou (${response.status})`);
  }
  return (await response.json()) as ValidationResult;
}


export async function createProject(
  request: CreateProjectRequest,
): Promise<CreateProjectResponse> {
  const response = await fetch(`${API_BASE}/create`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(`POST /create falhou (${response.status})`);
  }
  return (await response.json()) as CreateProjectResponse;
}


export function parseMetadataFreeText(text: string): ProjectMetadata {
  const lines = text
    .split(/[\n;]/)
    .map((l) => l.trim())
    .filter(Boolean);

  const findValue = (keyPatterns: RegExp[]): string => {
    for (const line of lines) {
      for (const pattern of keyPatterns) {
        const match = line.match(pattern);
        if (match && match[1]) return match[1].trim();
      }
    }
    return "";
  };

  const cliente = findValue([
    /cliente[:\s-]+(.+)/i,
    /^c(?:liente)?:\s*(.+)/i,
  ]);
  const empreendimento = findValue([
    /empreendimento[:\s-]+(.+)/i,
    /^e:\s*(.+)/i,
  ]);
  const cidade = findValue([
    /cidade[:\s-]+(.+)/i,
    /^cid?:\s*(.+)/i,
  ]);

  if (cliente || empreendimento || cidade) {
    return { cliente, empreendimento, cidade };
  }

  const fallback = lines.length >= 3 ? lines : [text];
  return {
    cliente: fallback[0] ?? "",
    empreendimento: fallback[1] ?? "",
    cidade: fallback[2] ?? "",
  };
}
