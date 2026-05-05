"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { sendQuery } from "@/lib/api";
import {
  deleteThread as deleteThreadStorage,
  getCurrentThreadId,
  getThread,
  listThreads,
  renameThread as renameThreadStorage,
  setCurrentThreadId,
  upsertThread,
} from "@/lib/threads";
import type { Message, Thread, ThreadAgentResult } from "@/lib/types";


export type UseChatReturn = {
  threads: Thread[];
  threadId: string | null;
  messages: Message[];
  agentResult: ThreadAgentResult | null;
  isLoading: boolean;
  sendMessage: (content: string) => Promise<void>;
  switchThread: (threadId: string) => void;
  newThread: () => void;
  deleteThread: (threadId: string) => void;
  renameThread: (threadId: string, newTitle: string) => void;
  appendUserMessage: (content: string) => void;
  appendAssistantMessage: (content: string) => void;
  setAgentResult: (result: ThreadAgentResult | null) => void;
};


function generateThreadId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  // Fallback pra ambientes sem crypto.randomUUID (testes JSDOM antigos).
  return `thr-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}


export function useChat(): UseChatReturn {
  const [threads, setThreads] = useState<Thread[]>([]);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [agentResult, setAgentResultState] = useState<ThreadAgentResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Refs pra leitura síncrona dos appends (evita stale closure ao chain
  // appendUserMessage → appendAssistantMessage rapidamente).
  const threadIdRef = useRef<string | null>(null);
  const messagesRef = useRef<Message[]>([]);
  const agentResultRef = useRef<ThreadAgentResult | null>(null);

  useEffect(() => {
    threadIdRef.current = threadId;
  }, [threadId]);
  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);
  useEffect(() => {
    agentResultRef.current = agentResult;
  }, [agentResult]);

  useEffect(() => {
    setThreads(listThreads());
    const tid = getCurrentThreadId();
    if (tid) {
      const thread = getThread(tid);
      if (thread) {
        setThreadId(tid);
        threadIdRef.current = tid;
        setMessages(thread.messages);
        messagesRef.current = thread.messages;
        const restored = thread.agent_result ?? null;
        setAgentResultState(restored);
        agentResultRef.current = restored;
      }
    }
  }, []);

  const persistAppend = useCallback(
    (next: Message[], agentOverride?: ThreadAgentResult | null): string => {
      let tid = threadIdRef.current;
      if (!tid) {
        tid = generateThreadId();
        threadIdRef.current = tid;
        setThreadId(tid);
        setCurrentThreadId(tid);
      }
      const agentToSave =
        agentOverride !== undefined ? agentOverride : agentResultRef.current;
      upsertThread(tid, next, { agentResult: agentToSave });
      setThreads(listThreads());
      return tid;
    },
    [],
  );

  const sendMessage = useCallback(
    async (content: string): Promise<void> => {
      const userMsg: Message = {
        role: "user",
        content,
        timestamp: new Date().toISOString(),
      };
      const optimistic = [...messagesRef.current, userMsg];
      messagesRef.current = optimistic;
      setMessages(optimistic);
      setIsLoading(true);

      try {
        const response = await sendQuery(content, threadIdRef.current ?? undefined);
        const finalThreadId = response.thread_id;

        const assistantMsg: Message = {
          role: "assistant",
          content: response.answer,
          sources: response.sources,
          timestamp: new Date().toISOString(),
        };
        const merged = [...optimistic, assistantMsg];
        messagesRef.current = merged;
        setMessages(merged);

        if (!threadIdRef.current) {
          threadIdRef.current = finalThreadId;
          setThreadId(finalThreadId);
          setCurrentThreadId(finalThreadId);
        }
        upsertThread(finalThreadId, merged, {
          agentResult: agentResultRef.current,
          titleHint: content,
        });
        setThreads(listThreads());
      } catch (e) {
        toast.error(
          e instanceof Error ? e.message : "Falha ao enviar mensagem",
        );
        const restored = messages;
        messagesRef.current = restored;
        setMessages(restored);
      } finally {
        setIsLoading(false);
      }
    },
    [messages],
  );

  const switchThread = useCallback((tid: string): void => {
    const thread = getThread(tid);
    if (!thread) return;
    threadIdRef.current = tid;
    setThreadId(tid);
    setCurrentThreadId(tid);
    messagesRef.current = thread.messages;
    setMessages(thread.messages);
    const restored = thread.agent_result ?? null;
    agentResultRef.current = restored;
    setAgentResultState(restored);
  }, []);

  const newThread = useCallback((): void => {
    threadIdRef.current = null;
    setThreadId(null);
    setCurrentThreadId(null);
    messagesRef.current = [];
    setMessages([]);
    agentResultRef.current = null;
    setAgentResultState(null);
  }, []);

  const deleteThread = useCallback(
    (tid: string): void => {
      deleteThreadStorage(tid);
      setThreads(listThreads());
      if (tid === threadId) {
        threadIdRef.current = null;
        setThreadId(null);
        setCurrentThreadId(null);
        messagesRef.current = [];
        setMessages([]);
        agentResultRef.current = null;
        setAgentResultState(null);
      }
    },
    [threadId],
  );

  const renameThread = useCallback((tid: string, newTitle: string): void => {
    renameThreadStorage(tid, newTitle);
    setThreads(listThreads());
  }, []);

  const appendUserMessage = useCallback(
    (content: string): void => {
      const next: Message[] = [
        ...messagesRef.current,
        {
          role: "user",
          content,
          timestamp: new Date().toISOString(),
        },
      ];
      messagesRef.current = next;
      setMessages(next);
      persistAppend(next);
    },
    [persistAppend],
  );

  const appendAssistantMessage = useCallback(
    (content: string): void => {
      const next: Message[] = [
        ...messagesRef.current,
        {
          role: "assistant",
          content,
          timestamp: new Date().toISOString(),
        },
      ];
      messagesRef.current = next;
      setMessages(next);
      persistAppend(next);
    },
    [persistAppend],
  );

  const setAgentResult = useCallback(
    (result: ThreadAgentResult | null): void => {
      agentResultRef.current = result;
      setAgentResultState(result);
      // Persist se já existir thread; senão deixa pra próxima append (que cria).
      if (threadIdRef.current) {
        upsertThread(threadIdRef.current, messagesRef.current, {
          agentResult: result,
        });
        setThreads(listThreads());
      }
    },
    [],
  );

  return {
    threads,
    threadId,
    messages,
    agentResult,
    isLoading,
    sendMessage,
    switchThread,
    newThread,
    deleteThread,
    renameThread,
    appendUserMessage,
    appendAssistantMessage,
    setAgentResult,
  };
}
