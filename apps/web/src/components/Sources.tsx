import type { Citation } from "@/lib/types";


export function Sources({
  sources,
}: {
  sources: Citation[];
}): React.ReactElement {
  return (
    <div className="bg-zinc-50 border border-zinc-200 rounded-lg px-4 py-3">
      <p className="text-xs font-semibold text-zinc-700 mb-2">
        Fontes ({sources.length}):
      </p>
      <ol className="space-y-1.5">
        {sources.map((s, idx) => (
          <li
            key={s.node_id}
            className="text-xs text-zinc-600 leading-relaxed"
          >
            <span className="font-mono text-zinc-400">[{idx + 1}]</span>{" "}
            <span className="font-medium text-zinc-800">
              Item {s.item_code}
            </span>
            {s.disciplina && (
              <span className="text-zinc-600"> - {s.disciplina}</span>
            )}
            {s.tipo && <span className="text-zinc-600"> - {s.tipo}</span>}
            <span className="text-zinc-400"> - score {s.score.toFixed(2)}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}
