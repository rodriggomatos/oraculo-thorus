"use client";

import { useChat } from "@/hooks/useChat";
import { ChatWindow } from "./ChatWindow";
import Sidebar from "./Sidebar";

export function ChatLayout(): React.ReactElement {
  const chat = useChat();

  return (
    <div className="flex h-screen bg-[var(--main-bg)] text-[var(--sidebar-text)]">
      <Sidebar
        threads={chat.threads.map((t) => ({ id: t.thread_id, title: t.titulo }))}
        activeThreadId={chat.threadId}
        user={{ name: "Rodrigo Matos", initials: "RM" }}
        onSelect={chat.switchThread}
        onNewChat={chat.newThread}
        onRename={chat.renameThread}
        onDelete={chat.deleteThread}
      />
      <ChatWindow
        threadId={chat.threadId}
        messages={chat.messages}
        isLoading={chat.isLoading}
        onSend={chat.sendMessage}
      />
    </div>
  );
}
