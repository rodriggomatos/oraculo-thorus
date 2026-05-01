"use client";

import * as React from "react";

type Thread = {
  id: string;
  title: string;
};

type SidebarProps = {
  threads: Thread[];
  activeThreadId: string | null;
  user: {
    name: string;
    initials: string;
  };
  onSelect: (threadId: string) => void;
  onNewChat: () => void;
  onRename: (threadId: string, newTitle: string) => void;
  onDelete: (threadId: string) => void;
};

type EditingState = {
  threadId: string;
  value: string;
};

type IconProps = {
  className?: string;
};

const STORAGE_KEY = "sidebar_collapsed";

function cn(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(" ");
}

function PanelLeftIcon({ className }: IconProps): React.JSX.Element {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect width="18" height="18" x="3" y="3" rx="2" />
      <path d="M9 3v18" />
    </svg>
  );
}

function SquarePenIcon({ className }: IconProps): React.JSX.Element {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
      <path d="M18.4 2.6a2.1 2.1 0 0 1 3 3L12 15l-4 1 1-4Z" />
    </svg>
  );
}

function MoreHorizontalIcon({ className }: IconProps): React.JSX.Element {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="1" />
      <circle cx="19" cy="12" r="1" />
      <circle cx="5" cy="12" r="1" />
    </svg>
  );
}

function PencilIcon({ className }: IconProps): React.JSX.Element {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M21.2 6.8 17.2 2.8a2 2 0 0 0-2.8 0L3 14.2V21h6.8L21.2 9.6a2 2 0 0 0 0-2.8Z" />
      <path d="m14 5 5 5" />
    </svg>
  );
}

function TrashIcon({ className }: IconProps): React.JSX.Element {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M3 6h18" />
      <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
      <path d="M19 6 18 20a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
      <path d="M10 11v6" />
      <path d="M14 11v6" />
    </svg>
  );
}

export default function Sidebar({
  threads,
  activeThreadId,
  user,
  onSelect,
  onNewChat,
  onRename,
  onDelete,
}: SidebarProps): React.JSX.Element {
  const [collapsed, setCollapsed] = React.useState<boolean>(false);
  const [openMenuThreadId, setOpenMenuThreadId] = React.useState<string | null>(null);
  const [editing, setEditing] = React.useState<EditingState | null>(null);
  const inputRef = React.useRef<HTMLInputElement | null>(null);

  React.useEffect((): void => {
    const storedValue: string | null = window.localStorage.getItem(STORAGE_KEY);
    if (storedValue === "true") {
      setCollapsed(true);
    }
  }, []);

  React.useEffect((): void => {
    window.localStorage.setItem(STORAGE_KEY, String(collapsed));
  }, [collapsed]);

  React.useEffect((): void => {
    if (!editing) {
      return;
    }
    window.requestAnimationFrame((): void => {
      inputRef.current?.focus();
      inputRef.current?.select();
    });
  }, [editing]);

  React.useEffect((): (() => void) => {
    const handlePointerDown = (event: PointerEvent): void => {
      const target = event.target as HTMLElement | null;
      if (!target?.closest("[data-thread-menu]")) {
        setOpenMenuThreadId(null);
      }
    };
    window.addEventListener("pointerdown", handlePointerDown);
    return (): void => window.removeEventListener("pointerdown", handlePointerDown);
  }, []);

  const toggleCollapsed = (): void => {
    setCollapsed((current: boolean): boolean => !current);
  };

  const startRename = (thread: Thread): void => {
    setOpenMenuThreadId(null);
    setEditing({
      threadId: thread.id,
      value: thread.title,
    });
  };

  const cancelRename = (): void => {
    setEditing(null);
  };

  const commitRename = (): void => {
    if (!editing) {
      return;
    }
    const thread: Thread | undefined = threads.find(
      (item: Thread): boolean => item.id === editing.threadId,
    );
    if (!thread) {
      setEditing(null);
      return;
    }
    const nextTitle: string = editing.value.trim();
    if (nextTitle.length > 0 && nextTitle !== thread.title) {
      onRename(editing.threadId, nextTitle);
    }
    setEditing(null);
  };

  const handleInputKeyDown = (event: React.KeyboardEvent<HTMLInputElement>): void => {
    if (event.key === "Enter") {
      event.preventDefault();
      commitRename();
      return;
    }
    if (event.key === "Escape") {
      event.preventDefault();
      cancelRename();
    }
  };

  return (
    <aside
      className={cn(
        "flex h-dvh shrink-0 flex-col overflow-hidden bg-[var(--sidebar-bg)] text-[var(--sidebar-text)] transition-[width] duration-200 ease-out",
        collapsed ? "w-[60px]" : "w-[260px]",
      )}
    >
      <header className="flex h-12 shrink-0 items-center justify-between px-3">
        {!collapsed && (
          <div className="truncate text-base font-semibold tracking-[-0.01em] text-[var(--sidebar-text)]">
            Thor
          </div>
        )}
        <button
          type="button"
          aria-label={collapsed ? "Expandir sidebar" : "Colapsar sidebar"}
          onClick={toggleCollapsed}
          className={cn(
            "inline-flex size-9 items-center justify-center rounded-lg text-[var(--sidebar-text)] outline-none transition-colors hover:bg-[var(--sidebar-hover)] focus-visible:ring-2 focus-visible:ring-white/20",
            collapsed && "mx-auto",
          )}
        >
          <PanelLeftIcon className="size-5" />
        </button>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden py-1">
        <button
          type="button"
          aria-label="Novo chat"
          onClick={onNewChat}
          className={cn(
            "mx-2 flex h-9 items-center rounded-lg px-2 text-sm text-[var(--sidebar-text)] outline-none transition-colors hover:bg-[var(--sidebar-hover)] focus-visible:ring-2 focus-visible:ring-white/20",
            collapsed ? "w-11 justify-center" : "w-[calc(100%-1rem)] gap-2",
          )}
        >
          <SquarePenIcon className="size-5 shrink-0" />
          {!collapsed && <span className="truncate">Novo chat</span>}
        </button>

        {!collapsed && (
          <nav aria-label="Conversas" className="mt-1 space-y-0.5">
            {threads.map((thread: Thread): React.JSX.Element => {
              const isActive: boolean = thread.id === activeThreadId;
              const editingThis: EditingState | null =
                editing && editing.threadId === thread.id ? editing : null;
              const isMenuOpen: boolean = openMenuThreadId === thread.id;

              return (
                <div
                  key={thread.id}
                  className={cn(
                    "group relative mx-2 flex h-9 items-center rounded-lg text-sm outline-none transition-colors",
                    isActive ? "bg-[var(--sidebar-active)]" : "hover:bg-[var(--sidebar-hover)]",
                  )}
                >
                  {editingThis ? (
                    <input
                      ref={inputRef}
                      value={editingThis.value}
                      onChange={(event: React.ChangeEvent<HTMLInputElement>): void => {
                        setEditing({
                          threadId: thread.id,
                          value: event.target.value,
                        });
                      }}
                      onKeyDown={handleInputKeyDown}
                      onBlur={commitRename}
                      aria-label={`Renomear ${thread.title}`}
                      className="mx-1 h-7 w-[calc(100%-0.5rem)] rounded-md bg-[var(--sidebar-active)] px-2 text-sm text-[var(--sidebar-text)] outline-none ring-1 ring-white/15 placeholder:text-[var(--sidebar-text-muted)] focus:ring-2 focus:ring-white/20"
                    />
                  ) : (
                    <>
                      <button
                        type="button"
                        onClick={(): void => onSelect(thread.id)}
                        className="h-full min-w-0 flex-1 truncate rounded-lg px-2 pr-9 text-left outline-none focus-visible:ring-2 focus-visible:ring-white/20"
                        aria-current={isActive ? "page" : undefined}
                      >
                        <span className="block truncate">{thread.title}</span>
                      </button>

                      <div data-thread-menu className="contents">
                        <button
                          type="button"
                          aria-label={`Opções de ${thread.title}`}
                          onClick={(event: React.MouseEvent<HTMLButtonElement>): void => {
                            event.stopPropagation();
                            setOpenMenuThreadId((current: string | null): string | null =>
                              current === thread.id ? null : thread.id,
                            );
                          }}
                          className={cn(
                            "absolute right-2 top-1/2 inline-flex size-7 -translate-y-1/2 items-center justify-center rounded-md text-[var(--sidebar-text-muted)] opacity-0 outline-none transition hover:bg-[var(--sidebar-hover)] hover:text-[var(--sidebar-text)] focus-visible:opacity-100 focus-visible:ring-2 focus-visible:ring-white/20 group-hover:opacity-100",
                            isMenuOpen && "opacity-100",
                          )}
                        >
                          <MoreHorizontalIcon className="size-5" />
                        </button>

                        {isMenuOpen && (
                          <div className="absolute right-2 top-8 z-50 min-w-36 rounded-md border border-[var(--sidebar-border)] bg-[var(--sidebar-popover-bg)] p-1 text-[var(--sidebar-text)] shadow-xl">
                            <button
                              type="button"
                              onClick={(): void => startRename(thread)}
                              className="flex w-full cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm text-[var(--sidebar-text)] outline-none hover:bg-[var(--sidebar-hover)] focus:bg-[var(--sidebar-hover)]"
                            >
                              <PencilIcon className="size-4" />
                              <span>Renomear</span>
                            </button>
                            <button
                              type="button"
                              onClick={(): void => {
                                setOpenMenuThreadId(null);
                                onDelete(thread.id);
                              }}
                              className="flex w-full cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm text-[var(--danger-text)] outline-none hover:bg-[var(--danger-hover-bg)] hover:text-[var(--danger-hover-text)] focus:bg-[var(--danger-hover-bg)] focus:text-[var(--danger-hover-text)]"
                            >
                              <TrashIcon className="size-4" />
                              <span>Excluir</span>
                            </button>
                          </div>
                        )}
                      </div>
                    </>
                  )}
                </div>
              );
            })}
          </nav>
        )}
      </div>

      <footer className="shrink-0 p-2">
        <div
          className={cn(
            "flex h-10 items-center rounded-lg px-2 text-sm text-[var(--sidebar-text)]",
            collapsed ? "justify-center px-0" : "gap-2",
          )}
        >
          <div className="flex size-6 shrink-0 items-center justify-center rounded-full bg-[var(--sidebar-active)] text-xs font-medium text-[var(--sidebar-text)]">
            {user.initials}
          </div>
          {!collapsed && <div className="min-w-0 truncate">{user.name}</div>}
        </div>
      </footer>
    </aside>
  );
}
