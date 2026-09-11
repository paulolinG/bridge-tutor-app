"use client";

import { useEffect, useRef } from "react";
import {
  Tldraw,
  getSnapshot,
  loadSnapshot,
  type Editor,
  type TLRecord,
  type TLStoreSnapshot,
} from "tldraw";
import "tldraw/tldraw.css";
import type { Whiteboard, WhiteboardSnapshot } from "@/lib/types/session";

const SNAPSHOT_SAVE_DEBOUNCE_MS: number = 3000;

interface WhiteboardDiffPayload {
  added: TLRecord[];
  updated: TLRecord[];
  removed: TLRecord["id"][];
}

// What a persisted snapshot has to look like for `loadSnapshot` to take its
// `TLStoreSnapshot` branch. Anything else reaches `migrateStoreSnapshot`,
// which throws on failure.
function isStoreSnapshot(
  snapshot: WhiteboardSnapshot,
): snapshot is WhiteboardSnapshot & TLStoreSnapshot {
  return (
    typeof snapshot.store === "object" &&
    snapshot.store !== null &&
    typeof snapshot.schema === "object" &&
    snapshot.schema !== null
  );
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
  const unlistenRef = useRef<(() => void) | null>(null);
  const hasRemoteChangesRef = useRef(false);

  useEffect(
    () =>
      on("whiteboard-diff", (payload) => {
        const editor = editorRef.current;
        if (!editor) return;
        hasRemoteChangesRef.current = true;
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
      unlistenRef.current?.();
      editorRef.current = null;
    };
  }, []);

  function handleMount(editor: Editor) {
    editorRef.current = editor;

    void getWhiteboard()
      .then(({ snapshot }) => {
        // The board is live and editable while this request is in flight, so
        // anything drawn or received meanwhile outranks a snapshot that was
        // already stale when it was sent.
        if (!snapshot || editorRef.current !== editor) return;
        if (hasRemoteChangesRef.current) return;
        if (editor.store.query.records("shape").get().length) return;
        if (!isStoreSnapshot(snapshot)) return;
        loadSnapshot(editor.store, snapshot);
      })
      .catch(() => {
        // `loadSnapshot` throws on a snapshot it cannot migrate, and the throw
        // tears the canvas down to an empty tl-container. Losing a saved
        // drawing is bad; losing the whiteboard mid-session is worse.
      });

    unlistenRef.current = editor.store.listen(
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
