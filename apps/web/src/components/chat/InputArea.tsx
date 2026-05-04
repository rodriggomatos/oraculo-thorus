"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowUp } from "lucide-react";
import { AttachmentMenu } from "./AttachmentMenu";
import {
  ChatDropZone,
  validateFile,
} from "./ChatDropZone";


export type InputAreaProps = {
  onSend: (content: string) => Promise<void> | void;
  onFileAccepted?: (file: File) => Promise<void> | void;
  onCreateProject?: () => void;
  canCreateProject: boolean;
  acceptingFiles: boolean;
  isLoading: boolean;
  parsing?: boolean;
  placeholder?: string;
};


export function InputArea({
  onSend,
  onFileAccepted,
  onCreateProject,
  canCreateProject,
  acceptingFiles,
  isLoading,
  parsing = false,
  placeholder = "Pergunte alguma coisa",
}: InputAreaProps): React.ReactElement {
  const inputDisabled = isLoading || parsing;
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const openPickerRef = useRef<(() => void) | null>(null);

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
    if (!trimmed || inputDisabled) return;
    setValue("");
    await onSend(trimmed);
  };

  const handleAttachFile = (): void => {
    openPickerRef.current?.();
  };

  const handleCreateProject = (): void => {
    onCreateProject?.();
  };

  const handleFileAccepted = async (file: File): Promise<void> => {
    if (!onFileAccepted) return;
    if (validateFile(file)) return;
    await onFileAccepted(file);
  };

  return (
    <ChatDropZone
      active={acceptingFiles && !parsing}
      onFileAccepted={handleFileAccepted}
      registerOpenPicker={(open) => {
        openPickerRef.current = open;
      }}
      parsing={parsing}
      className="w-full"
    >
      <div className="flex w-full items-end gap-2 rounded-3xl bg-[var(--sidebar-popover-bg)] px-3 py-2">
        <AttachmentMenu
          canCreateProject={canCreateProject}
          onAttachFile={handleAttachFile}
          onCreateProject={handleCreateProject}
          disabled={inputDisabled}
        />
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
          placeholder={parsing ? "Analisando a planilha…" : placeholder}
          className="flex-1 self-center resize-none bg-transparent py-2 min-h-[28px] max-h-[200px] text-[var(--sidebar-text)] placeholder:text-[var(--sidebar-text-muted)] outline-none"
          rows={1}
          disabled={inputDisabled}
        />
        <button
          type="button"
          onClick={() => void handleSubmit()}
          disabled={!value.trim() || inputDisabled}
          aria-label="Enviar"
          className="shrink-0 rounded-full bg-white p-2 text-zinc-900 transition-colors hover:bg-zinc-200 disabled:bg-[var(--sidebar-active)] disabled:text-[var(--sidebar-text-muted)]"
        >
          <ArrowUp className="h-4 w-4" />
        </button>
      </div>
    </ChatDropZone>
  );
}
