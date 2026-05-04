"use client";


export type FlowDecisionBarProps = {
  onContinue: () => void;
  onFix: () => void;
};


export function FlowDecisionBar({
  onContinue,
  onFix,
}: FlowDecisionBarProps): React.ReactElement {
  return (
    <div
      role="group"
      aria-label="Decisão sobre inconsistências da planilha"
      className="flex items-center gap-2"
    >
      <button
        type="button"
        onClick={onContinue}
        className="rounded-full bg-white px-4 py-2 text-sm font-medium text-zinc-900 transition-colors hover:bg-zinc-200"
      >
        Continuar mesmo assim
      </button>
      <button
        type="button"
        onClick={onFix}
        className="rounded-full border border-[var(--sidebar-border,rgba(255,255,255,0.15))] bg-transparent px-4 py-2 text-sm font-medium text-[var(--sidebar-text)] transition-colors hover:bg-[var(--sidebar-hover)]"
      >
        Vou corrigir
      </button>
    </div>
  );
}
