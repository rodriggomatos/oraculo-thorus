"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";
import type { ProjectMetadata } from "./types";


export type MetadataFormProps = {
  onConfirm: (metadata: ProjectMetadata) => void;
  loading?: boolean;
  errorMessage?: string | null;
  disabled?: boolean;
};


type FieldKey = "cliente" | "empreendimento" | "cidade" | "estado";


const LABEL_BY_FIELD: Record<FieldKey, string> = {
  cliente: "Cliente",
  empreendimento: "Empreendimento",
  cidade: "Cidade",
  estado: "Estado (opcional)",
};


const REQUIRED: ReadonlySet<FieldKey> = new Set(["cliente", "empreendimento", "cidade"]);


const FIELD_CLASSES =
  "w-full rounded-md border border-[var(--sidebar-border,rgba(255,255,255,0.15))] bg-[var(--sidebar-popover-bg,rgba(0,0,0,0.4))] px-3 py-2 text-sm text-[var(--sidebar-text)] placeholder:text-[var(--sidebar-text-muted)] outline-none transition-colors focus:border-[var(--sidebar-active,#3b82f6)] disabled:opacity-60";

const FIELD_INVALID_CLASSES =
  "border-red-500/70 focus:border-red-500";


export function MetadataForm({
  onConfirm,
  loading = false,
  errorMessage = null,
  disabled = false,
}: MetadataFormProps): React.ReactElement {
  const [values, setValues] = useState<Record<FieldKey, string>>({
    cliente: "",
    empreendimento: "",
    cidade: "",
    estado: "",
  });
  const [showErrors, setShowErrors] = useState(false);

  const isDisabled = disabled || loading;

  const trimmed = (k: FieldKey): string => values[k].trim();
  const missingRequired = (Array.from(REQUIRED) as FieldKey[]).filter(
    (k) => trimmed(k).length === 0,
  );
  const isValid = missingRequired.length === 0;

  const setField = (key: FieldKey, value: string): void => {
    if (key === "estado") {
      setValues((prev) => ({ ...prev, estado: value.toUpperCase().slice(0, 2) }));
      return;
    }
    setValues((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    if (isDisabled) return;
    if (!isValid) {
      setShowErrors(true);
      return;
    }
    onConfirm({
      cliente: trimmed("cliente"),
      empreendimento: trimmed("empreendimento"),
      cidade: trimmed("cidade"),
      estado: trimmed("estado") || undefined,
    });
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="flex w-full max-w-md flex-col gap-3 rounded-2xl border border-[var(--sidebar-border,rgba(255,255,255,0.1))] bg-[var(--sidebar-popover-bg,rgba(0,0,0,0.3))] p-4"
      aria-label="Metadados do projeto"
      aria-busy={loading}
    >
      {(Object.keys(LABEL_BY_FIELD) as FieldKey[]).map((key) => {
        const isRequired = REQUIRED.has(key);
        const invalid = showErrors && isRequired && trimmed(key).length === 0;
        return (
          <label key={key} className="flex flex-col gap-1 text-xs text-[var(--sidebar-text-muted)]">
            <span>
              {LABEL_BY_FIELD[key]}
              {isRequired ? <span className="text-red-400"> *</span> : null}
            </span>
            <input
              type="text"
              value={values[key]}
              onChange={(e) => setField(key, e.target.value)}
              maxLength={key === "estado" ? 2 : undefined}
              autoComplete="off"
              autoCapitalize={key === "estado" ? "characters" : "words"}
              spellCheck={false}
              disabled={isDisabled}
              aria-invalid={invalid}
              aria-required={isRequired}
              className={`${FIELD_CLASSES} ${invalid ? FIELD_INVALID_CLASSES : ""}`}
            />
          </label>
        );
      })}
      {errorMessage ? (
        <p
          role="alert"
          className="rounded-md border border-red-500/40 bg-red-500/10 px-3 py-2 text-xs text-red-300"
        >
          {errorMessage}
        </p>
      ) : null}
      <div className="flex items-center justify-end gap-2 pt-1">
        <button
          type="submit"
          disabled={isDisabled || !isValid}
          className="flex items-center gap-2 rounded-full bg-white px-4 py-2 text-sm font-medium text-zinc-900 transition-colors hover:bg-zinc-200 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? (
            <>
              <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
              <span>Criando…</span>
            </>
          ) : (
            <span>Confirmar</span>
          )}
        </button>
      </div>
    </form>
  );
}
