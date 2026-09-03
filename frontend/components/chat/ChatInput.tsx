"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

export function ChatInput({
  onSend,
  disabled,
}: {
  onSend: (content: string) => Promise<void>;
  disabled?: boolean;
}) {
  const [value, setValue] = useState("");

  async function handleSend() {
    const trimmed = value.trim();
    if (!trimmed) return;
    try {
      await onSend(trimmed);
      setValue("");
    } catch {
      // Keep the typed text so it isn't lost — the parent surfaces the error.
    }
  }

  return (
    <div className="flex gap-2">
      <Textarea
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            void handleSend();
          }
        }}
        placeholder="Respond as the tutor..."
        disabled={disabled}
        className="min-h-[60px] resize-none"
      />
      <Button onClick={() => void handleSend()} disabled={disabled || !value.trim()}>
        Send
      </Button>
    </div>
  );
}
