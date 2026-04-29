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
        <div className="bg-blue-50 border border-blue-100 rounded-lg px-4 py-2.5 max-w-[75%]">
          <p className="whitespace-pre-wrap text-sm text-zinc-800">
            {message.content}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="flex flex-col gap-2 max-w-[75%]">
        <div className="bg-white border border-zinc-200 rounded-lg px-4 py-3">
          <div className="prose prose-sm prose-zinc max-w-none">
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
