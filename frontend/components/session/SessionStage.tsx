"use client";

import { useEffect, useRef } from "react";
import DailyIframe, { type DailyCall } from "@daily-co/daily-js";

export function SessionStage({
  roomUrl,
  token,
}: {
  roomUrl: string;
  token: string;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const callRef = useRef<DailyCall | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const call = DailyIframe.createFrame(container, {
      iframeStyle: { width: "100%", height: "100%", border: "0" },
      showLeaveButton: false,
    });
    callRef.current = call;
    void call.join({ url: roomUrl, token });

    // A leaked iframe keeps a participant "in" the room and burns free-tier
    // participant-minutes, so this must run on every unmount.
    return () => {
      call.destroy();
      callRef.current = null;
    };
  }, [roomUrl, token]);

  return (
    <div
      ref={containerRef}
      className="aspect-video w-full overflow-hidden rounded-lg border bg-muted"
    />
  );
}
