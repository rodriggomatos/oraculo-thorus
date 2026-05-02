import { getBrowserSupabase } from "./supabase/client";
import type { ProjectDTO, QueryRequest, QueryResponse } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";


async function authHeaders(): Promise<Record<string, string>> {
  const supabase = getBrowserSupabase();
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}


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

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(await authHeaders()),
  };

  const response = await fetch(`${API_URL}/query`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const text = await response.text().catch(() => response.statusText);
    throw new Error(`POST /query falhou (${response.status}): ${text}`);
  }

  return (await response.json()) as QueryResponse;
}


export async function getProjects(): Promise<ProjectDTO[]> {
  const response = await fetch(`${API_URL}/projects`, {
    headers: await authHeaders(),
  });
  if (!response.ok) {
    const text = await response.text().catch(() => response.statusText);
    throw new Error(`GET /projects falhou (${response.status}): ${text}`);
  }
  return (await response.json()) as ProjectDTO[];
}


export async function getMe(): Promise<{
  user_id: string;
  email: string;
  name: string;
  role: string;
} | null> {
  const headers = await authHeaders();
  if (!("Authorization" in headers)) return null;
  const response = await fetch(`${API_URL}/auth/me`, { headers });
  if (!response.ok) return null;
  return (await response.json()) as {
    user_id: string;
    email: string;
    name: string;
    role: string;
  };
}
