"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Loader2, Paperclip, X } from "lucide-react";
import { cn } from "@/lib/utils";


export const SHEET_EXTENSIONS = [".gsheet"] as const;
export const MAX_FILE_BYTES = 10 * 1024 * 1024;


type ChatDropZoneProps = {
  active: boolean;
  onFileAccepted: (file: File) => void;
  onError?: (message: string) => void;
  registerOpenPicker?: (open: () => void) => void;
  parsing?: boolean;
  className?: string;
  children?: React.ReactNode;
};


type Pending = {
  file: File;
};


export function validateFile(file: File): string | null {
  const lowerName = file.name.toLowerCase();
  const accepted = SHEET_EXTENSIONS.some((ext) => lowerName.endsWith(ext));
  if (!accepted) {
    return `Tipo de arquivo inválido. Aceito: ${SHEET_EXTENSIONS.join(", ")}`;
  }
  if (file.size > MAX_FILE_BYTES) {
    const limitMB = Math.round(MAX_FILE_BYTES / (1024 * 1024));
    return `Arquivo maior que ${limitMB}MB`;
  }
  return null;
}


export function ChatDropZone({
  active,
  onFileAccepted,
  onError,
  registerOpenPicker,
  parsing = false,
  className,
  children,
}: ChatDropZoneProps): React.ReactElement {
  const [isDragOver, setIsDragOver] = useState(false);
  const [pending, setPending] = useState<Pending | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dragDepthRef = useRef(0);

  const reportError = useCallback(
    (message: string): void => {
      setError(message);
      onError?.(message);
    },
    [onError],
  );

  const acceptFile = useCallback(
    (file: File): void => {
      const validationError = validateFile(file);
      if (validationError) {
        reportError(validationError);
        return;
      }
      setError(null);
      setPending({ file });
    },
    [reportError],
  );

  const openPicker = useCallback((): void => {
    if (!active) return;
    fileInputRef.current?.click();
  }, [active]);

  useEffect(() => {
    if (!registerOpenPicker) return;
    registerOpenPicker(openPicker);
  }, [registerOpenPicker, openPicker]);

  const handleDragEnter = useCallback(
    (e: React.DragEvent<HTMLDivElement>): void => {
      if (!active) return;
      e.preventDefault();
      e.stopPropagation();
      dragDepthRef.current += 1;
      if (e.dataTransfer.types.includes("Files")) {
        setIsDragOver(true);
      }
    },
    [active],
  );

  const handleDragOver = useCallback(
    (e: React.DragEvent<HTMLDivElement>): void => {
      if (!active) return;
      e.preventDefault();
      e.stopPropagation();
      e.dataTransfer.dropEffect = "copy";
    },
    [active],
  );

  const handleDragLeave = useCallback(
    (e: React.DragEvent<HTMLDivElement>): void => {
      if (!active) return;
      e.preventDefault();
      e.stopPropagation();
      dragDepthRef.current = Math.max(0, dragDepthRef.current - 1);
      if (dragDepthRef.current === 0) {
        setIsDragOver(false);
      }
    },
    [active],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>): void => {
      if (!active) return;
      e.preventDefault();
      e.stopPropagation();
      dragDepthRef.current = 0;
      setIsDragOver(false);
      const file = e.dataTransfer.files?.[0];
      if (!file) return;
      acceptFile(file);
    },
    [active, acceptFile],
  );

  const handleFileInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>): void => {
      const file = e.target.files?.[0];
      if (file) acceptFile(file);
      e.target.value = "";
    },
    [acceptFile],
  );

  const handleSendPending = useCallback((): void => {
    if (!pending) return;
    onFileAccepted(pending.file);
    setPending(null);
  }, [pending, onFileAccepted]);

  const handleCancelPending = useCallback((): void => {
    setPending(null);
  }, []);

  return (
    <div
      onDragEnter={handleDragEnter}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={cn("relative", className)}
      data-dropzone-active={active ? "true" : "false"}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept={SHEET_EXTENSIONS.join(",")}
        className="sr-only"
        onChange={handleFileInputChange}
        aria-label="Selecionar planilha"
      />

      {children}

      {isDragOver && active && !parsing ? (
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 z-30 flex items-center justify-center rounded-2xl border-2 border-dashed border-[var(--sidebar-active,#3b82f6)] bg-[var(--sidebar-popover-bg,rgba(0,0,0,0.6))]/80 text-[var(--sidebar-text,#fff)]"
        >
          <span className="text-sm font-medium">Solte o arquivo aqui</span>
        </div>
      ) : null}

      {parsing ? (
        <div
          role="status"
          aria-live="polite"
          className="pointer-events-none absolute inset-0 z-30 flex items-center justify-center gap-2 rounded-2xl border border-[var(--sidebar-border,rgba(255,255,255,0.15))] bg-[var(--sidebar-popover-bg,rgba(0,0,0,0.7))]/90 text-[var(--sidebar-text,#fff)]"
        >
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
          <span className="text-sm font-medium">Analisando a planilha…</span>
        </div>
      ) : null}

      {pending ? (
        <div className="absolute -top-14 left-0 right-0 z-20 mx-auto flex max-w-md items-center gap-2 rounded-xl bg-[var(--sidebar-popover-bg,#27272a)] p-2 text-sm text-[var(--sidebar-text,#fff)] shadow-lg">
          <Paperclip className="h-4 w-4 shrink-0 text-[var(--sidebar-text-muted,#a1a1aa)]" />
          <span className="flex-1 truncate" title={pending.file.name}>
            {pending.file.name}
          </span>
          <button
            type="button"
            onClick={handleSendPending}
            className="rounded-md bg-white px-2.5 py-1 text-xs font-medium text-zinc-900 hover:bg-zinc-200"
          >
            Enviar
          </button>
          <button
            type="button"
            onClick={handleCancelPending}
            className="rounded-md p-1 text-[var(--sidebar-text-muted,#a1a1aa)] hover:bg-[var(--sidebar-hover,#3f3f46)] hover:text-[var(--sidebar-text,#fff)]"
            aria-label="Cancelar"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      ) : null}

      {error ? (
        <div
          role="alert"
          className="absolute -top-9 left-0 right-0 z-20 mx-auto max-w-md rounded-md bg-red-900/90 px-3 py-1.5 text-center text-xs text-red-100"
          onClick={() => setError(null)}
        >
          {error}
        </div>
      ) : null}
    </div>
  );
}
