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
    <Collapsible className="bg-[var(--sidebar-popover-bg)] border border-[var(--sidebar-border)] rounded-lg overflow-hidden">
      <CollapsibleTrigger className="group flex items-center gap-2 w-full px-4 py-2.5 text-xs font-semibold text-[var(--sidebar-text)] hover:bg-[var(--sidebar-hover)] transition-colors">
        <ChevronRight className="h-3.5 w-3.5 text-[var(--sidebar-text-muted)] transition-transform duration-200 group-data-[state=open]:rotate-90" />
        <span>Fontes ({sources.length})</span>
      </CollapsibleTrigger>
      <CollapsibleContent className="overflow-hidden data-[state=open]:animate-collapsible-down data-[state=closed]:animate-collapsible-up">
        <ol className="space-y-1.5 px-4 pb-3 pt-1">
          {sources.map((s, idx) => (
            <li
              key={s.node_id}
              className="text-xs text-[var(--sidebar-text-muted)] leading-relaxed"
            >
              <span className="font-mono text-[var(--sidebar-text-muted)]/70">[{idx + 1}]</span>{" "}
              <span className="font-medium text-[var(--sidebar-text)]">
                Item {s.item_code}
              </span>
              {s.disciplina && (
                <span className="text-[var(--sidebar-text-muted)]"> - {s.disciplina}</span>
              )}
              {s.tipo && <span className="text-[var(--sidebar-text-muted)]"> - {s.tipo}</span>}
              <span className="text-[var(--sidebar-text-muted)]/70"> - score {s.score.toFixed(2)}</span>
            </li>
          ))}
        </ol>
      </CollapsibleContent>
    </Collapsible>
  );
}
