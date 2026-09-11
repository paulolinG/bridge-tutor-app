"use client";

import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertCircleIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import type { SenderRole, SessionMessage } from "@/lib/types/session";

export function SessionChat({
  role,
  listMessages,
  sendMessage,
  send,
  on,
}: {
  role: SenderRole;
  listMessages: () => Promise<SessionMessage[]>;
  sendMessage: (content: string) => Promise<SessionMessage>;
  send: (event: string, payload: unknown) => void;
  on: (event: string, handler: (payload: unknown) => void) => () => void;
}) {
  const { data } = useQuery({ queryKey: ["session-messages"], queryFn: listMessages });
  const [messages, setMessages] = useState<SessionMessage[]>([]);
  const [seededFrom, setSeededFrom] = useState<SessionMessage[] | null>(null);
  const [value, setValue] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  // History loads once via GET; live updates arrive over the channel — see
  // https://react.dev/learn/you-might-not-need-an-effect#adjusting-some-state-when-a-prop-changes
  if (data && data !== seededFrom) {
    setSeededFrom(data);
    setMessages(data);
  }

  useEffect(
    () => on("chat-message", (payload) => setMessages((prev) => [...prev, payload as SessionMessage])),
    [on],
  );

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length]);

  const sendMutation = useMutation({
    mutationFn: sendMessage,
    onSuccess: (message) => {
      setMessages((prev) => [...prev, message]);
      send("chat-message", message);
      setValue("");
    },
  });

  function handleSend() {
    const trimmed = value.trim();
    if (!trimmed || sendMutation.isPending) return;
    sendMutation.mutate(trimmed);
  }

  return (
    <div className="flex flex-1 flex-col gap-2">
      <ScrollArea className="flex-1 rounded-md border p-3">
        {messages.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
            No messages yet.
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            {messages.map((message) => (
              <div
                key={message.id}
                className={cn(
                  "flex",
                  message.sender_role === role ? "justify-end" : "justify-start",
                )}
              >
                <div
                  className={cn(
                    "max-w-[85%] rounded-2xl px-3 py-1.5 text-sm whitespace-pre-wrap",
                    message.sender_role === role
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-foreground",
                  )}
                >
                  {message.content}
                </div>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </ScrollArea>
      {sendMutation.isError && (
        <Alert variant="destructive">
          <AlertCircleIcon />
          <AlertDescription>Could not send. Try again.</AlertDescription>
        </Alert>
      )}
      <div className="flex items-end gap-2">
        <Textarea
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              handleSend();
            }
          }}
          placeholder="Message..."
          className="min-h-[44px] resize-none"
        />
        <Button size="sm" onClick={handleSend} disabled={!value.trim() || sendMutation.isPending}>
          Send
        </Button>
      </div>
    </div>
  );
}
