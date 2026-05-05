import type { Message, Thread, ThreadAgentState } from "./types";

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
  // Flow agêntico abre com mensagem do assistant. Usa esse conteúdo até o user
  // mandar a primeira mensagem dele — o título é trocado quando vier um titleHint
  // mais específico (ver UpsertOptions.titleHint).
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
  /**
   * Estado opaco do agente em curso. `undefined` mantém o que estava;
   * `null` apaga; objeto sobrescreve.
   */
  agentState?: ThreadAgentState | null;
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
    if (options.agentState !== undefined) {
      existing.agent_state = options.agentState;
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
      agent_state: options.agentState ?? null,
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
