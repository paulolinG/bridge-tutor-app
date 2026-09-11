"use client";

import { useEffect, useRef } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MessageBubble } from "@/components/chat/MessageBubble";
import type { ChatMessage } from "@/lib/types/certification";

export function ChatWindow({
  messages,
  pendingReply,
}: {
  messages: ChatMessage[];
  pendingReply?: boolean;
}) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, pendingReply]);

  return (
    <ScrollArea className="h-[60vh] rounded-md border p-4">
      {messages.length === 0 ? (
        <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
          The conversation will start here.
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {messages.map((message, index) => (
            <MessageBubble key={index} message={message} />
          ))}
          {pendingReply && (
            <div className="flex justify-start">
              <div className="flex items-center gap-1 rounded-2xl bg-muted px-4 py-3">
                <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.3s]" />
                <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.15s]" />
                <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground" />
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      )}
    </ScrollArea>
  );
}
