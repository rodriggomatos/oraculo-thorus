"use client";

import { formatDistanceToNow } from "date-fns";
import { ptBR } from "date-fns/locale";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import type { Thread } from "@/lib/types";


type Props = {
  threads: Thread[];
  currentThreadId: string | null;
  onSwitch: (threadId: string) => void;
  onNew: () => void;
  onDelete: (threadId: string) => void;
};


export function Sidebar({
  threads,
  currentThreadId,
  onSwitch,
  onNew,
  onDelete,
}: Props): React.ReactElement {
  return (
    <aside className="w-[280px] bg-zinc-50 border-r border-zinc-200 flex flex-col">
      <div className="p-3 border-b border-zinc-200">
        <Button onClick={onNew} className="w-full" variant="default">
          + Nova conversa
        </Button>
      </div>
      <ScrollArea className="flex-1">
        <div className="p-2 space-y-1">
          {threads.length === 0 && (
            <p className="text-xs text-zinc-500 text-center mt-6 px-2">
              Nenhuma conversa ainda. Comece uma nova ali em cima.
            </p>
          )}
          {threads.map((t) => (
            <div
              key={t.thread_id}
              role="button"
              tabIndex={0}
              onClick={() => onSwitch(t.thread_id)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onSwitch(t.thread_id);
                }
              }}
              className={cn(
                "group flex items-start justify-between p-3 rounded-md cursor-pointer transition-colors",
                "hover:bg-zinc-100",
                currentThreadId === t.thread_id && "bg-zinc-200 hover:bg-zinc-200",
              )}
            >
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-zinc-800 truncate">
                  {t.titulo}
                </p>
                <p className="text-xs text-zinc-500 mt-1">
                  {formatDistanceToNow(new Date(t.created_at), {
                    addSuffix: true,
                    locale: ptBR,
                  })}
                </p>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(t.thread_id);
                }}
                className="opacity-0 group-hover:opacity-100 text-zinc-400 hover:text-red-500 ml-2 transition-opacity"
                title="Deletar conversa"
                aria-label="Deletar conversa"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
      </ScrollArea>
    </aside>
  );
}
