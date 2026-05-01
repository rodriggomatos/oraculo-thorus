"use client";

import { useCallback, useEffect, useState } from "react";
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
import type { Message, Thread } from "@/lib/types";


export type UseChatReturn = {
  threads: Thread[];
  threadId: string | null;
  messages: Message[];
  isLoading: boolean;
  sendMessage: (content: string) => Promise<void>;
  switchThread: (threadId: string) => void;
  newThread: () => void;
  deleteThread: (threadId: string) => void;
  renameThread: (threadId: string, newTitle: string) => void;
};


export function useChat(): UseChatReturn {
  const [threads, setThreads] = useState<Thread[]>([]);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    setThreads(listThreads());
    const tid = getCurrentThreadId();
    if (tid) {
      const thread = getThread(tid);
      if (thread) {
        setThreadId(tid);
        setMessages(thread.messages);
      }
    }
  }, []);

  const sendMessage = useCallback(
    async (content: string): Promise<void> => {
      const userMsg: Message = {
        role: "user",
        content,
        timestamp: new Date().toISOString(),
      };
      const optimistic = [...messages, userMsg];
      setMessages(optimistic);
      setIsLoading(true);

      try {
        const response = await sendQuery(content, threadId ?? undefined);
        const finalThreadId = response.thread_id;

        const assistantMsg: Message = {
          role: "assistant",
          content: response.answer,
          sources: response.sources,
          timestamp: new Date().toISOString(),
        };
        const merged = [...optimistic, assistantMsg];
        setMessages(merged);

        if (!threadId) {
          setThreadId(finalThreadId);
          setCurrentThreadId(finalThreadId);
        }
        upsertThread(finalThreadId, content, merged);
        setThreads(listThreads());
      } catch (e) {
        toast.error(
          e instanceof Error ? e.message : "Falha ao enviar mensagem",
        );
        setMessages(messages);
      } finally {
        setIsLoading(false);
      }
    },
    [messages, threadId],
  );

  const switchThread = useCallback((tid: string): void => {
    const thread = getThread(tid);
    if (!thread) return;
    setThreadId(tid);
    setCurrentThreadId(tid);
    setMessages(thread.messages);
  }, []);

  const newThread = useCallback((): void => {
    setThreadId(null);
    setCurrentThreadId(null);
    setMessages([]);
  }, []);

  const deleteThread = useCallback(
    (tid: string): void => {
      deleteThreadStorage(tid);
      setThreads(listThreads());
      if (tid === threadId) {
        setThreadId(null);
        setCurrentThreadId(null);
        setMessages([]);
      }
    },
    [threadId],
  );

  const renameThread = useCallback((tid: string, newTitle: string): void => {
    renameThreadStorage(tid, newTitle);
    setThreads(listThreads());
  }, []);

  return {
    threads,
    threadId,
    messages,
    isLoading,
    sendMessage,
    switchThread,
    newThread,
    deleteThread,
    renameThread,
  };
}
