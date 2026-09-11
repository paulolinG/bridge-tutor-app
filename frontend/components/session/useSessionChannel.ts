"use client";

import { useCallback, useEffect, useRef } from "react";
import type { RealtimeChannel } from "@supabase/supabase-js";
import { supabase } from "@/lib/supabase/client";

// The one deliberate direct-Supabase exception (see ADR 0002): this reads
// no tables and writes nothing durable, it only relays ephemeral broadcast
// events between the two participants already on this session's page.
// Durable state (chat history, the whiteboard snapshot) still goes through
// FastAPI. One channel per session, shared by chat and whiteboard via the
// `on`/`send` pair below rather than each opening its own subscription.
export function useSessionChannel(sessionId: string) {
  const channelRef = useRef<RealtimeChannel | null>(null);
  const listenersRef = useRef(new Map<string, Set<(payload: unknown) => void>>());

  useEffect(() => {
    const channel = supabase
      .channel(`session:${sessionId}`)
      .on("broadcast", { event: "*" }, ({ event, payload }) => {
        listenersRef.current.get(event)?.forEach((handler) => handler(payload));
      })
      .subscribe();
    channelRef.current = channel;

    return () => {
      void supabase.removeChannel(channel);
      channelRef.current = null;
    };
  }, [sessionId]);

  const send = useCallback((event: string, payload: unknown) => {
    channelRef.current?.send({ type: "broadcast", event, payload });
  }, []);

  const on = useCallback((event: string, handler: (payload: unknown) => void) => {
    const handlers = listenersRef.current.get(event) ?? new Set();
    handlers.add(handler);
    listenersRef.current.set(event, handlers);
    return () => {
      handlers.delete(handler);
    };
  }, []);

  return { send, on };
}
