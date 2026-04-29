"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Message as MessageComponent } from "./Message";
import { ThinkingIndicator } from "./ThinkingIndicator";
import type { Message } from "@/lib/types";


type Props = {
  threadId: string | null;
  messages: Message[];
  isLoading: boolean;
  onSend: (content: string) => Promise<void>;
};


export function ChatWindow({
  threadId,
  messages,
  isLoading,
  onSend,
}: Props): React.ReactElement {
  const [value, setValue] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!scrollRef.current) return;
    scrollRef.current.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, isLoading]);

  useEffect(() => {
    if (!textareaRef.current) return;
    textareaRef.current.style.height = "auto";
    textareaRef.current.style.height = `${Math.min(
      textareaRef.current.scrollHeight,
      200,
    )}px`;
  }, [value]);

  const handleSubmit = async (): Promise<void> => {
    const trimmed = value.trim();
    if (!trimmed || isLoading) return;
    setValue("");
    await onSend(trimmed);
  };

  const headerTitle =
    threadId && messages.length > 0 ? "Conversa" : "Nova conversa";

  return (
    <main className="flex-1 flex flex-col">
      <header className="border-b border-zinc-200 px-6 py-4">
        <h1 className="text-base font-semibold text-zinc-800">{headerTitle}</h1>
      </header>

      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-6 py-4 space-y-4"
      >
        {messages.length === 0 && !isLoading && (
          <div className="flex flex-col items-center justify-center h-full text-center text-zinc-500">
            <p className="text-lg font-medium text-zinc-700">
              Pergunte ao Thor sobre seus projetos
            </p>
            <p className="text-sm mt-2">
              Exemplo: <span className="font-mono">qual o material do gás @26002</span>
            </p>
          </div>
        )}
        {messages.map((m, i) => (
          <MessageComponent key={i} message={m} />
        ))}
        {isLoading && <ThinkingIndicator />}
      </div>

      <footer className="border-t border-zinc-200 p-4">
        <div className="flex gap-2 items-end max-w-4xl mx-auto">
          <Textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void handleSubmit();
              }
            }}
            placeholder="Pergunte algo... (Shift+Enter pra quebra de linha)"
            className="resize-none min-h-[40px] max-h-[200px] flex-1"
            rows={1}
            disabled={isLoading}
          />
          <Button
            onClick={() => void handleSubmit()}
            disabled={!value.trim() || isLoading}
          >
            Enviar
          </Button>
        </div>
      </footer>
    </main>
  );
}
