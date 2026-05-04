"use client";

import { useState } from "react";


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

  const customValid = FIVE_DIGITS.test(custom);

  const handleConfirmSuggested = (): void => {
    if (disabled) return;
    onConfirm(suggested);
  };

  const handleConfirmCustom = (): void => {
    if (disabled || !customValid) return;
    onConfirm(Number.parseInt(custom, 10));
  };

  if (editing) {
    return (
      <div
        role="group"
        aria-label="Digite o número alternativo"
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
            if (e.key === "Escape") {
              e.preventDefault();
              setEditing(false);
              setCustom("");
            }
          }}
          maxLength={5}
          placeholder="ex: 26025"
          aria-label="Número do projeto"
          aria-invalid={custom.length > 0 && !customValid}
          disabled={disabled}
          className="w-32 rounded-md border border-[var(--sidebar-border,rgba(255,255,255,0.15))] bg-[var(--sidebar-popover-bg,rgba(0,0,0,0.4))] px-3 py-2 text-sm text-[var(--sidebar-text)] placeholder:text-[var(--sidebar-text-muted)] outline-none focus:border-[var(--sidebar-active,#3b82f6)]"
        />
        <button
          type="button"
          onClick={handleConfirmCustom}
          disabled={disabled || !customValid}
          className="rounded-full bg-white px-4 py-2 text-sm font-medium text-zinc-900 transition-colors hover:bg-zinc-200 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Usar este número
        </button>
        <button
          type="button"
          onClick={() => {
            setEditing(false);
            setCustom("");
          }}
          disabled={disabled}
          className="rounded-full border border-[var(--sidebar-border,rgba(255,255,255,0.15))] bg-transparent px-3 py-2 text-sm text-[var(--sidebar-text-muted)] transition-colors hover:bg-[var(--sidebar-hover)] hover:text-[var(--sidebar-text)]"
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
      className="flex items-center gap-2"
    >
      <button
        type="button"
        onClick={handleConfirmSuggested}
        disabled={disabled}
        className="rounded-full bg-white px-4 py-2 text-sm font-medium text-zinc-900 transition-colors hover:bg-zinc-200 disabled:cursor-not-allowed disabled:opacity-50"
      >
        ✓ Confirmar {suggested}
      </button>
      <button
        type="button"
        onClick={() => setEditing(true)}
        disabled={disabled}
        className="rounded-full border border-[var(--sidebar-border,rgba(255,255,255,0.15))] bg-transparent px-4 py-2 text-sm font-medium text-[var(--sidebar-text)] transition-colors hover:bg-[var(--sidebar-hover)]"
      >
        ✏️ Outro número
      </button>
    </div>
  );
}
