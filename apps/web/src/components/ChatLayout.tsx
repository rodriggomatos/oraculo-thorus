"use client";

import { useChat } from "@/hooks/useChat";
import { useUser } from "@/hooks/useUser";
import { ChatWindow } from "./ChatWindow";
import Sidebar from "./Sidebar";

export function ChatLayout(): React.ReactElement {
  const chat = useChat();
  const { user } = useUser();

  const sidebarUser = user
    ? { name: user.name, initials: user.initials }
    : { name: "...", initials: "?" };

  return (
    <div className="flex h-screen bg-[var(--main-bg)] text-[var(--sidebar-text)]">
      <Sidebar
        threads={chat.threads.map((t) => ({ id: t.thread_id, title: t.titulo }))}
        activeThreadId={chat.threadId}
        user={sidebarUser}
        onSelect={chat.switchThread}
        onNewChat={chat.newThread}
        onRename={chat.renameThread}
        onDelete={chat.deleteThread}
      />
      <ChatWindow
        threadId={chat.threadId}
        messages={chat.messages}
        agentResult={chat.agentResult}
        isLoading={chat.isLoading}
        onSend={chat.sendMessage}
        onAppendUser={chat.appendUserMessage}
        onAppendAssistant={chat.appendAssistantMessage}
        onAgentResult={chat.setAgentResult}
      />
    </div>
  );
}
