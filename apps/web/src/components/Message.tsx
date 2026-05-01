"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Sources } from "./Sources";
import type { Message as MessageType } from "@/lib/types";


export function Message({
  message,
}: {
  message: MessageType;
}): React.ReactElement {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="bg-[var(--sidebar-popover-bg)] rounded-2xl px-4 py-2.5 max-w-[75%]">
          <p className="whitespace-pre-wrap text-sm text-[var(--sidebar-text)]">
            {message.content}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="flex flex-col gap-2 max-w-[75%]">
        <div className="px-1 py-1">
          <div className="prose prose-sm prose-invert max-w-none text-[var(--sidebar-text)]">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          </div>
        </div>
        {message.sources && message.sources.length > 0 && (
          <Sources sources={message.sources} />
        )}
      </div>
    </div>
  );
}
