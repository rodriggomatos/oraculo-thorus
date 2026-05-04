"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";


export type NumberConfirmBarProps = {
  suggested: number;
  onConfirm: (confirmed: number) => void;
  disabled?: boolean;
};


const FIVE_DIGITS = /^\d{5}$/;


export function NumberConfirmBar({
  suggested,
  onConfirm,
  disabled = false,
}: NumberConfirmBarProps): React.ReactElement {
  const [editing, setEditing] = useState(false);
  const [custom, setCustom] = useState("");
  const [submitted, setSubmitted] = useState<"suggested" | "custom" | null>(null);

  const customValid = FIVE_DIGITS.test(custom);
  const isLocked = disabled || submitted !== null;

  const handleConfirmSuggested = (): void => {
    if (isLocked) return;
    setSubmitted("suggested");
    onConfirm(suggested);
  };

  const handleConfirmCustom = (): void => {
    if (isLocked || !customValid) return;
    setSubmitted("custom");
    onConfirm(Number.parseInt(custom, 10));
  };

  if (editing) {
    return (
      <div
        role="group"
        aria-label="Digite o número alternativo"
        aria-busy={submitted === "custom"}
        className="flex items-center gap-2"
      >
        <input
          type="text"
          inputMode="numeric"
          autoFocus
          value={custom}
          onChange={(e) => setCustom(e.target.value.replace(/\D/g, "").slice(0, 5))}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              handleConfirmCustom();
            }
            if (e.key === "Escape" && submitted === null) {
              e.preventDefault();
              setEditing(false);
              setCustom("");
            }
          }}
          maxLength={5}
          placeholder="ex: 26025"
          aria-label="Número do projeto"
          aria-invalid={custom.length > 0 && !customValid}
          disabled={isLocked}
          className="w-32 rounded-md border border-[var(--sidebar-border,rgba(255,255,255,0.15))] bg-[var(--sidebar-popover-bg,rgba(0,0,0,0.4))] px-3 py-2 text-sm text-[var(--sidebar-text)] placeholder:text-[var(--sidebar-text-muted)] outline-none focus:border-[var(--sidebar-active,#3b82f6)] disabled:opacity-60"
        />
        <button
          type="button"
          onClick={handleConfirmCustom}
          disabled={isLocked || !customValid}
          className="flex items-center gap-2 rounded-full bg-white px-4 py-2 text-sm font-medium text-zinc-900 transition-colors hover:bg-zinc-200 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {submitted === "custom" ? (
            <>
              <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
              <span>Confirmando…</span>
            </>
          ) : (
            <span>Usar este número</span>
          )}
        </button>
        <button
          type="button"
          onClick={() => {
            setEditing(false);
            setCustom("");
          }}
          disabled={isLocked}
          className="rounded-full border border-[var(--sidebar-border,rgba(255,255,255,0.15))] bg-transparent px-3 py-2 text-sm text-[var(--sidebar-text-muted)] transition-colors hover:bg-[var(--sidebar-hover)] hover:text-[var(--sidebar-text)] disabled:cursor-not-allowed disabled:opacity-50"
        >
          Cancelar
        </button>
      </div>
    );
  }

  return (
    <div
      role="group"
      aria-label="Confirmar número do projeto"
      aria-busy={submitted === "suggested"}
      className="flex items-center gap-2"
    >
      <button
        type="button"
        onClick={handleConfirmSuggested}
        disabled={isLocked}
        className="flex items-center gap-2 rounded-full bg-white px-4 py-2 text-sm font-medium text-zinc-900 transition-colors hover:bg-zinc-200 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {submitted === "suggested" ? (
          <>
            <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
            <span>Confirmando…</span>
          </>
        ) : (
          <span>✓ Confirmar {suggested}</span>
        )}
      </button>
      <button
        type="button"
        onClick={() => setEditing(true)}
        disabled={isLocked}
        className="rounded-full border border-[var(--sidebar-border,rgba(255,255,255,0.15))] bg-transparent px-4 py-2 text-sm font-medium text-[var(--sidebar-text)] transition-colors hover:bg-[var(--sidebar-hover)] disabled:cursor-not-allowed disabled:opacity-50"
      >
        ✏️ Outro número
      </button>
    </div>
  );
}
