export function ThinkingIndicator(): React.ReactElement {
  return (
    <div className="flex justify-start">
      <div className="flex items-center gap-3 px-1 py-2">
        <div className="flex gap-1">
          <span className="w-1.5 h-1.5 bg-[var(--sidebar-text-muted)] rounded-full animate-bounce [animation-delay:-0.3s]" />
          <span className="w-1.5 h-1.5 bg-[var(--sidebar-text-muted)] rounded-full animate-bounce [animation-delay:-0.15s]" />
          <span className="w-1.5 h-1.5 bg-[var(--sidebar-text-muted)] rounded-full animate-bounce" />
        </div>
        <span className="text-sm text-[var(--sidebar-text-muted)]">Thor está pensando...</span>
      </div>
    </div>
  );
}
