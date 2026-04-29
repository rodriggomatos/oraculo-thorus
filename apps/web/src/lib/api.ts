import type { ProjectDTO, QueryRequest, QueryResponse } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function sendQuery(
  question: string,
  threadId?: string,
  projectNumber?: number,
  topK = 5,
): Promise<QueryResponse> {
  const body: QueryRequest = {
    question,
    thread_id: threadId,
    project_number: projectNumber,
    top_k: topK,
  };

  const response = await fetch(`${API_URL}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const text = await response.text().catch(() => response.statusText);
    throw new Error(`POST /query falhou (${response.status}): ${text}`);
  }

  return (await response.json()) as QueryResponse;
}

export async function getProjects(): Promise<ProjectDTO[]> {
  const response = await fetch(`${API_URL}/projects`);
  if (!response.ok) {
    const text = await response.text().catch(() => response.statusText);
    throw new Error(`GET /projects falhou (${response.status}): ${text}`);
  }
  return (await response.json()) as ProjectDTO[];
}
