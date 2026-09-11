"use client";

import { useEffect, useRef } from "react";
import { Tldraw, getSnapshot, loadSnapshot, type Editor, type TLRecord } from "tldraw";
import "tldraw/tldraw.css";
import type { Whiteboard, WhiteboardSnapshot } from "@/lib/types/session";

const SNAPSHOT_SAVE_DEBOUNCE_MS: number = 3000;

interface WhiteboardDiffPayload {
  added: TLRecord[];
  updated: TLRecord[];
  removed: TLRecord["id"][];
}

export function SessionWhiteboard({
  getWhiteboard,
  putWhiteboard,
  send,
  on,
}: {
  getWhiteboard: () => Promise<Whiteboard>;
  putWhiteboard: (snapshot: WhiteboardSnapshot | null) => Promise<Whiteboard>;
  send: (event: string, payload: unknown) => void;
  on: (event: string, handler: (payload: unknown) => void) => () => void;
}) {
  const editorRef = useRef<Editor | null>(null);
  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(
    () =>
      on("whiteboard-diff", (payload) => {
        const editor = editorRef.current;
        if (!editor) return;
        const { added, updated, removed } = payload as WhiteboardDiffPayload;
        editor.store.mergeRemoteChanges(() => {
          if (added.length || updated.length) editor.store.put([...added, ...updated]);
          if (removed.length) editor.store.remove(removed);
        });
      }),
    [on],
  );

  useEffect(() => {
    return () => {
      if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current);
    };
  }, []);

  function handleMount(editor: Editor) {
    editorRef.current = editor;

    void getWhiteboard().then(({ snapshot }) => {
      if (snapshot) {
        loadSnapshot(editor.store, snapshot as never);
      }
    });

    editor.store.listen(
      (entry) => {
        const { added, updated, removed } = entry.changes;
        const addedRecords = Object.values(added);
        const updatedRecords = Object.values(updated).map(([, to]) => to);
        const removedRecords = Object.values(removed);
        if (!addedRecords.length && !updatedRecords.length && !removedRecords.length) return;

        send("whiteboard-diff", {
          added: addedRecords,
          updated: updatedRecords,
          removed: removedRecords.map((record) => record.id),
        } satisfies WhiteboardDiffPayload);

        if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current);
        saveTimeoutRef.current = setTimeout(() => {
          const snapshot = getSnapshot(editor.store);
          void putWhiteboard(snapshot.document as unknown as WhiteboardSnapshot);
        }, SNAPSHOT_SAVE_DEBOUNCE_MS);
      },
      { source: "user", scope: "document" },
    );
  }

  return (
    <div className="relative flex-1 overflow-hidden rounded-lg border">
      <Tldraw onMount={handleMount} />
    </div>
  );
}
