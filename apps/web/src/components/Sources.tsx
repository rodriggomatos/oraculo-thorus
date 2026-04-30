"use client";

import { ChevronRight } from "lucide-react";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import type { Citation } from "@/lib/types";


export function Sources({
  sources,
}: {
  sources: Citation[];
}): React.ReactElement {
  return (
    <Collapsible className="bg-zinc-50 border border-zinc-200 rounded-lg overflow-hidden">
      <CollapsibleTrigger className="group flex items-center gap-2 w-full px-4 py-2.5 text-xs font-semibold text-zinc-700 hover:bg-zinc-100 transition-colors">
        <ChevronRight className="h-3.5 w-3.5 text-zinc-500 transition-transform duration-200 group-data-[state=open]:rotate-90" />
        <span>Fontes ({sources.length})</span>
      </CollapsibleTrigger>
      <CollapsibleContent className="overflow-hidden data-[state=open]:animate-collapsible-down data-[state=closed]:animate-collapsible-up">
        <ol className="space-y-1.5 px-4 pb-3 pt-1">
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
      </CollapsibleContent>
    </Collapsible>
  );
}
