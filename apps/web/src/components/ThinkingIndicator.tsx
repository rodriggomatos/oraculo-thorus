export function ThinkingIndicator(): React.ReactElement {
  return (
    <div className="flex justify-start">
      <div className="flex items-center gap-3 bg-white border border-zinc-200 rounded-lg px-4 py-3">
        <div className="flex gap-1">
          <span className="w-1.5 h-1.5 bg-zinc-400 rounded-full animate-bounce [animation-delay:-0.3s]" />
          <span className="w-1.5 h-1.5 bg-zinc-400 rounded-full animate-bounce [animation-delay:-0.15s]" />
          <span className="w-1.5 h-1.5 bg-zinc-400 rounded-full animate-bounce" />
        </div>
        <span className="text-sm text-zinc-500">Thor está pensando...</span>
      </div>
    </div>
  );
}
