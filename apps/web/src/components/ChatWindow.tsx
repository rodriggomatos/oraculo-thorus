"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowUp, FolderOpen, ListTodo, Plus, Search } from "lucide-react";
import { Message as MessageComponent } from "./Message";
import { ThinkingIndicator } from "./ThinkingIndicator";
import type { Message } from "@/lib/types";


type Props = {
  threadId: string | null;
  messages: Message[];
  isLoading: boolean;
  onSend: (content: string) => Promise<void>;
};


type Suggestion = {
  icon: React.ReactNode;
  label: string;
  prompt: string;
};


const SUGGESTIONS: Suggestion[] = [
  {
    icon: <FolderOpen className="h-4 w-4 text-[var(--sidebar-text-muted)]" />,
    label: "Listar projetos",
    prompt: "Quais projetos temos cadastrados?",
  },
  {
    icon: <Search className="h-4 w-4 text-[var(--sidebar-text-muted)]" />,
    label: "Buscar definição",
    prompt: "Qual o material da tubulação de gás @26002?",
  },
  {
    icon: <ListTodo className="h-4 w-4 text-[var(--sidebar-text-muted)]" />,
    label: "Definições pendentes",
    prompt: "Quais definições estão pendentes em @26002?",
  },
];


export function ChatWindow({
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

  const fillSuggestion = (prompt: string): void => {
    setValue(prompt);
    textareaRef.current?.focus();
  };

  const isEmpty = messages.length === 0 && !isLoading;

  const pillInput = (
    <div className="flex items-end gap-2 w-full rounded-3xl bg-[var(--sidebar-popover-bg)] px-3 py-2">
      <button
        type="button"
        aria-label="Anexar"
        className="p-2 rounded-full text-[var(--sidebar-text-muted)] hover:text-[var(--sidebar-text)] hover:bg-[var(--sidebar-hover)] shrink-0 transition-colors"
      >
        <Plus className="h-5 w-5" />
      </button>
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            void handleSubmit();
          }
        }}
        placeholder="Pergunte alguma coisa"
        className="flex-1 bg-transparent text-[var(--sidebar-text)] placeholder:text-[var(--sidebar-text-muted)] outline-none resize-none min-h-[28px] max-h-[200px] py-2 self-center"
        rows={1}
        disabled={isLoading}
      />
      <button
        type="button"
        onClick={() => void handleSubmit()}
        disabled={!value.trim() || isLoading}
        aria-label="Enviar"
        className="p-2 rounded-full bg-white text-zinc-900 hover:bg-zinc-200 disabled:bg-[var(--sidebar-active)] disabled:text-[var(--sidebar-text-muted)] shrink-0 transition-colors"
      >
        <ArrowUp className="h-4 w-4" />
      </button>
    </div>
  );

  return (
    <main className="flex-1 flex flex-col bg-[var(--main-bg)] text-[var(--sidebar-text)] overflow-hidden">
      {isEmpty ? (
        <div className="flex-1 flex items-center justify-center px-6">
          <div className="w-full max-w-2xl flex flex-col items-center gap-8">
            <h1 className="text-3xl font-medium tracking-tight text-[var(--sidebar-text)]">
              Como posso ajudar?
            </h1>
            <div className="w-full">{pillInput}</div>
            <div className="flex flex-wrap items-center justify-center gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s.label}
                  type="button"
                  onClick={() => fillSuggestion(s.prompt)}
                  className="flex items-center gap-2 rounded-full border border-[var(--sidebar-border)] px-3.5 py-2 text-sm text-[var(--sidebar-text)] hover:bg-[var(--sidebar-hover)] transition-colors"
                >
                  {s.icon}
                  <span>{s.label}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <>
          <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 pt-6 pb-4">
            <div className="max-w-3xl mx-auto space-y-4">
              {messages.map((m, i) => (
                <MessageComponent key={i} message={m} />
              ))}
              {isLoading && <ThinkingIndicator />}
            </div>
          </div>
          <div className="px-6 pb-4">
            <div className="max-w-3xl mx-auto">{pillInput}</div>
          </div>
        </>
      )}
    </main>
  );
}
