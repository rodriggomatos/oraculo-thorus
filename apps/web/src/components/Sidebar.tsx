"use client";

import { formatDistanceToNow } from "date-fns";
import { ptBR } from "date-fns/locale";
import { MoreHorizontal, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
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
              className={cn(
                "group relative flex items-center rounded-md transition-colors",
                "hover:bg-zinc-100",
                currentThreadId === t.thread_id && "bg-zinc-200 hover:bg-zinc-200",
              )}
            >
              <div
                role="button"
                tabIndex={0}
                onClick={() => onSwitch(t.thread_id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onSwitch(t.thread_id);
                  }
                }}
                className="flex-1 min-w-0 p-3 cursor-pointer"
              >
                <p className="text-sm font-medium text-zinc-800 truncate pr-6">
                  {t.titulo}
                </p>
                <p className="text-xs text-zinc-500 mt-1">
                  {formatDistanceToNow(new Date(t.created_at), {
                    addSuffix: true,
                    locale: ptBR,
                  })}
                </p>
              </div>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button
                    onClick={(e) => e.stopPropagation()}
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-md text-zinc-400 hover:text-zinc-700 hover:bg-zinc-200 opacity-0 group-hover:opacity-100 data-[state=open]:opacity-100 transition-opacity"
                    title="Ações"
                    aria-label="Ações"
                  >
                    <MoreHorizontal className="h-4 w-4" />
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-40">
                  <DropdownMenuItem
                    onClick={() => onDelete(t.thread_id)}
                    className="text-red-600 focus:text-red-700 focus:bg-red-50 cursor-pointer"
                  >
                    <Trash2 className="h-4 w-4 mr-2" />
                    Deletar
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          ))}
        </div>
      </ScrollArea>
    </aside>
  );
}