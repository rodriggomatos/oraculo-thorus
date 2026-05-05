import type { Message, Thread, ThreadAgentResult } from "./types";

const THREADS_KEY = "threads";
const CURRENT_THREAD_KEY = "current_thread_id";

function isBrowser(): boolean {
  return typeof window !== "undefined";
}


function deriveTitulo(messages: Message[]): string {
  const firstUser = messages.find((m) => m.role === "user");
  if (firstUser) {
    return firstUser.content.slice(0, 50) + (firstUser.content.length > 50 ? "..." : "");
  }
  // Fluxo agêntico abre com mensagem do assistant. Usa esse conteúdo até o user
  // mandar a primeira mensagem dele — aí o título já vai ter sido sobrescrito
  // (não fazemos isso aqui pra evitar churn; quando dá pra trocar a primeira
  // user message a thread é re-upserted com título novo via firstUserMessage
  // se vier explicitamente).
  const firstAny = messages[0];
  if (firstAny) {
    return firstAny.content.slice(0, 50) + (firstAny.content.length > 50 ? "..." : "");
  }
  return "Nova conversa";
}


export function listThreads(): Thread[] {
  if (!isBrowser()) return [];
  const raw = window.localStorage.getItem(THREADS_KEY);
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw) as Thread[];
    return [...parsed].sort(
      (a, b) =>
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
    );
  } catch {
    return [];
  }
}

export function getThread(threadId: string): Thread | null {
  return listThreads().find((t) => t.thread_id === threadId) ?? null;
}


export type UpsertOptions = {
  agentResult?: ThreadAgentResult | null;
  /**
   * Override do título — usado quando o caller já sabe a primeira user
   * message (ex.: sendMessage). Se omitido, título é derivado das messages.
   */
  titleHint?: string;
};


export function upsertThread(
  threadId: string,
  messages: Message[],
  options: UpsertOptions = {},
): void {
  if (!isBrowser()) return;
  const all = listThreads();
  const existing = all.find((t) => t.thread_id === threadId);
  if (existing) {
    existing.messages = messages;
    if (options.agentResult !== undefined) {
      existing.agent_result = options.agentResult;
    }
    // Título vira hint apenas se ainda for "Nova conversa" (placeholder).
    if (options.titleHint && existing.titulo === "Nova conversa") {
      existing.titulo = options.titleHint.slice(0, 50) +
        (options.titleHint.length > 50 ? "..." : "");
    }
  } else {
    const titulo = options.titleHint
      ? options.titleHint.slice(0, 50) + (options.titleHint.length > 50 ? "..." : "")
      : deriveTitulo(messages);
    all.push({
      thread_id: threadId,
      titulo,
      created_at: new Date().toISOString(),
      messages,
      agent_result: options.agentResult ?? null,
    });
  }
  window.localStorage.setItem(THREADS_KEY, JSON.stringify(all));
}

export function deleteThread(threadId: string): void {
  if (!isBrowser()) return;
  const remaining = listThreads().filter((t) => t.thread_id !== threadId);
  window.localStorage.setItem(THREADS_KEY, JSON.stringify(remaining));
}

export function renameThread(threadId: string, newTitle: string): void {
  if (!isBrowser()) return;
  const all = listThreads();
  const target = all.find((t) => t.thread_id === threadId);
  if (!target) return;
  target.titulo = newTitle.trim() || target.titulo;
  window.localStorage.setItem(THREADS_KEY, JSON.stringify(all));
}

export function getCurrentThreadId(): string | null {
  if (!isBrowser()) return null;
  return window.localStorage.getItem(CURRENT_THREAD_KEY);
}

export function setCurrentThreadId(threadId: string | null): void {
  if (!isBrowser()) return;
  if (threadId === null) {
    window.localStorage.removeItem(CURRENT_THREAD_KEY);
  } else {
    window.localStorage.setItem(CURRENT_THREAD_KEY, threadId);
  }
}
