import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/lib/types/certification";

export function MessageBubble({ message }: { message: ChatMessage }) {
  const isTutor = message.role === "tutor";

  return (
    <div className={cn("flex", isTutor ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[75%] rounded-2xl px-4 py-2 text-sm whitespace-pre-wrap",
          isTutor
            ? "bg-primary text-primary-foreground"
            : "bg-muted text-foreground",
        )}
      >
        {message.content}
      </div>
    </div>
  );
}
