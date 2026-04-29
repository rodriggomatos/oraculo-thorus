"use client";

import { useChat } from "@/hooks/useChat";
import { ChatWindow } from "./ChatWindow";
import { Sidebar } from "./Sidebar";

export function ChatLayout(): React.ReactElement {
  const chat = useChat();

  return (
    <div className="flex h-screen bg-white">
      <Sidebar
        threads={chat.threads}
        currentThreadId={chat.threadId}
        onSwitch={chat.switchThread}
        onNew={chat.newThread}
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
