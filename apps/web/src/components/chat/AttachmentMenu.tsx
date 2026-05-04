"use client";

import { Paperclip, Plus, Sparkles, FilePlus2 } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuPortal,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";


export type AttachmentMenuProps = {
  canCreateProject: boolean;
  onAttachFile: () => void;
  onCreateProject: () => void;
  disabled?: boolean;
};


const TRIGGER_CLASSES =
  "p-2 rounded-full text-[var(--sidebar-text-muted)] hover:text-[var(--sidebar-text)] hover:bg-[var(--sidebar-hover)] shrink-0 transition-colors disabled:opacity-50 disabled:cursor-not-allowed";

const PANEL_CLASSES =
  "min-w-[220px] rounded-xl border border-white/10 bg-[var(--sidebar-popover-bg,#1f1f23)] p-1 text-[var(--sidebar-text,#fafafa)] shadow-2xl backdrop-blur";

const ITEM_CLASSES =
  "flex cursor-pointer items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-[var(--sidebar-text)] outline-none focus:bg-[var(--sidebar-hover,#3f3f46)] focus:text-[var(--sidebar-text)] data-[state=open]:bg-[var(--sidebar-hover,#3f3f46)]";

const ICON_CLASSES = "h-4 w-4 text-[var(--sidebar-text-muted)]";


export function AttachmentMenu({
  canCreateProject,
  onAttachFile,
  onCreateProject,
  disabled = false,
}: AttachmentMenuProps): React.ReactElement {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          aria-label="Abrir menu de anexar e ações do agente"
          className={TRIGGER_CLASSES}
          disabled={disabled}
        >
          <Plus className="h-5 w-5" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuPortal>
        <DropdownMenuContent
          side="top"
          align="start"
          sideOffset={8}
          className={PANEL_CLASSES}
        >
          <DropdownMenuItem
            className={ITEM_CLASSES}
            onSelect={(event) => {
              event.preventDefault();
              onAttachFile();
            }}
          >
            <Paperclip className={ICON_CLASSES} />
            <span>Anexar arquivo</span>
          </DropdownMenuItem>

          {canCreateProject ? (
            <DropdownMenuSub>
              <DropdownMenuSubTrigger className={ITEM_CLASSES}>
                <Sparkles className={ICON_CLASSES} />
                <span>Agente</span>
              </DropdownMenuSubTrigger>
              <DropdownMenuPortal>
                <DropdownMenuSubContent
                  sideOffset={8}
                  className={PANEL_CLASSES}
                >
                  <DropdownMenuItem
                    className={ITEM_CLASSES}
                    onSelect={(event) => {
                      event.preventDefault();
                      onCreateProject();
                    }}
                  >
                    <FilePlus2 className={ICON_CLASSES} />
                    <span>Criar projeto novo</span>
                  </DropdownMenuItem>
                </DropdownMenuSubContent>
              </DropdownMenuPortal>
            </DropdownMenuSub>
          ) : null}
        </DropdownMenuContent>
      </DropdownMenuPortal>
    </DropdownMenu>
  );
}
