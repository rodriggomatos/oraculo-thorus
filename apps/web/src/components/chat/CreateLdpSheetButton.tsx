"use client";

import { useState } from "react";
import { ExternalLink, FileSpreadsheet, Loader2 } from "lucide-react";

import { createLdpSheet } from "@/features/create-project/mock";


export type CreateLdpSheetButtonProps = {
  projectId: string;
  initialSheetsId?: string | null;
  disabled?: boolean;
  disabledReason?: string;
  onCreated?: (sheetsId: string) => void;
};


type Status = "idle" | "loading" | "success" | "error";


function sheetUrlFor(sheetsId: string): string {
  return `https://docs.google.com/spreadsheets/d/${sheetsId}/edit`;
}


export function CreateLdpSheetButton({
  projectId,
  initialSheetsId = null,
  disabled = false,
  disabledReason,
  onCreated,
}: CreateLdpSheetButtonProps): React.ReactElement {
  const [status, setStatus] = useState<Status>(initialSheetsId ? "success" : "idle");
  const [sheetsUrl, setSheetsUrl] = useState<string | null>(
    initialSheetsId ? sheetUrlFor(initialSheetsId) : null,
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleClick = async (): Promise<void> => {
    if (status === "loading" || status === "success") return;
    setStatus("loading");
    setErrorMessage(null);
    try {
      const result = await createLdpSheet(projectId);
      setSheetsUrl(result.sheetsUrl);
      setStatus("success");
      onCreated?.(result.sheetsId);
    } catch (e) {
      setErrorMessage(e instanceof Error ? e.message : "Falha desconhecida");
      setStatus("error");
    }
  };

  if (status === "success" && sheetsUrl) {
    return (
      <a
        href={sheetsUrl}
        target="_blank"
        rel="noreferrer"
        className="inline-flex items-center gap-2 self-start rounded-full border border-emerald-400/40 bg-emerald-500/10 px-4 py-2 text-sm font-medium text-emerald-300 transition-colors hover:bg-emerald-500/20"
      >
        <ExternalLink className="h-4 w-4" aria-hidden />
        <span>✅ Planilha LDP criada — abrir no Sheets</span>
      </a>
    );
  }

  const isDisabled = disabled || status === "loading";

  return (
    <div className="flex flex-col gap-2">
      <button
        type="button"
        onClick={handleClick}
        disabled={isDisabled}
        aria-busy={status === "loading"}
        title={disabled ? disabledReason : undefined}
        className="inline-flex items-center gap-2 self-start rounded-full bg-white px-4 py-2 text-sm font-medium text-zinc-900 transition-colors hover:bg-zinc-200 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {status === "loading" ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
            <span>Criando planilha LDP…</span>
          </>
        ) : (
          <>
            <FileSpreadsheet className="h-4 w-4" aria-hidden />
            <span>Criar planilha LDP</span>
          </>
        )}
      </button>
      {disabled && disabledReason ? (
        <p className="text-xs text-[var(--sidebar-text-muted)]">{disabledReason}</p>
      ) : null}
      {status === "error" && errorMessage ? (
        <p role="alert" className="text-sm text-red-400">
          {errorMessage}
        </p>
      ) : null}
    </div>
  );
}
