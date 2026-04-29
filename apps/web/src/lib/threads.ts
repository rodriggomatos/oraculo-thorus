import type { Message, Thread } from "./types";

const THREADS_KEY = "threads";
const CURRENT_THREAD_KEY = "current_thread_id";

function isBrowser(): boolean {
  return typeof window !== "undefined";
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

export function upsertThread(
  threadId: string,
  firstUserMessage: string,
  messages: Message[],
): void {
  if (!isBrowser()) return;
  const all = listThreads();
  const existing = all.find((t) => t.thread_id === threadId);
  if (existing) {
    existing.messages = messages;
  } else {
    const titulo =
      firstUserMessage.slice(0, 50) +
      (firstUserMessage.length > 50 ? "..." : "");
    all.push({
      thread_id: threadId,
      titulo,
      created_at: new Date().toISOString(),
      messages,
    });
  }
  window.localStorage.setItem(THREADS_KEY, JSON.stringify(all));
}

export function deleteThread(threadId: string): void {
  if (!isBrowser()) return;
  const remaining = listThreads().filter((t) => t.thread_id !== threadId);
  window.localStorage.setItem(THREADS_KEY, JSON.stringify(remaining));
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
