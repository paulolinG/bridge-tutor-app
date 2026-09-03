import { ScrollArea } from "@/components/ui/scroll-area";
import { MessageBubble } from "@/components/chat/MessageBubble";
import type { ChatMessage } from "@/lib/types/certification";

export function ChatWindow({ messages }: { messages: ChatMessage[] }) {
  return (
    <ScrollArea className="h-[60vh] rounded-md border p-4">
      <div className="flex flex-col gap-3">
        {messages.map((message, index) => (
          <MessageBubble key={index} message={message} />
        ))}
      </div>
    </ScrollArea>
  );
}
