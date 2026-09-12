"use client";

import { useEffect, useRef, useState } from "react";
import { Tldraw, getSnapshot, type Editor, type TLRecord, type TLStoreSnapshot } from "tldraw";
import "tldraw/tldraw.css";
import { Skeleton } from "@/components/ui/skeleton";
import type { Whiteboard, WhiteboardSnapshot } from "@/lib/types/session";

const SNAPSHOT_SAVE_DEBOUNCE_MS: number = 3000;

interface WhiteboardDiffPayload {
  added: TLRecord[];
  updated: TLRecord[];
  removed: TLRecord["id"][];
}

// What a persisted snapshot has to look like to be a `TLStoreSnapshot`.
// Anything else is discarded rather than handed to tldraw, which throws on a
// snapshot it cannot migrate.
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

  // Diffs that arrive while the saved snapshot is still loading. The editor
  // does not exist yet to receive them, and dropping them would silently
  // diverge the two boards.
  const pendingDiffsRef = useRef<WhiteboardDiffPayload[]>([]);

  // The stored snapshot is applied by constructing the editor around it, not
  // by loading it into a running one: `loadSnapshot` swaps the store out from
  // under a mounted editor, and a failure there crashes the editor into an
  // empty container rather than degrading to a blank board.
  const [initialSnapshot, setInitialSnapshot] = useState<TLStoreSnapshot | null | undefined>();

  // `getWhiteboard` is an inline closure from the page, so it is a new
  // function every render. Capturing the mount-time one keeps the fetch keyed
  // to mount instead of re-firing on every render.
  const getWhiteboardRef = useRef(getWhiteboard);

  useEffect(() => {
    let active = true;
    getWhiteboardRef
      .current()
      .then(({ snapshot }) => {
        if (!active) return;
        setInitialSnapshot(snapshot && isStoreSnapshot(snapshot) ? snapshot : null);
      })
      .catch(() => {
        // An unreachable backend must not cost the session its whiteboard.
        if (active) setInitialSnapshot(null);
      });
    return () => {
      active = false;
    };
  }, []);

  function applyDiff(editor: Editor, { added, updated, removed }: WhiteboardDiffPayload) {
    editor.store.mergeRemoteChanges(() => {
      if (added.length || updated.length) editor.store.put([...added, ...updated]);
      if (removed.length) editor.store.remove(removed);
    });
  }

  useEffect(
    () =>
      on("whiteboard-diff", (payload) => {
        const diff = payload as WhiteboardDiffPayload;
        const editor = editorRef.current;
        if (!editor) {
          pendingDiffsRef.current.push(diff);
          return;
        }
        applyDiff(editor, diff);
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

    for (const diff of pendingDiffsRef.current) applyDiff(editor, diff);
    pendingDiffsRef.current = [];

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
      {initialSnapshot === undefined ? (
        <Skeleton className="size-full" />
      ) : (
        <Tldraw snapshot={initialSnapshot ?? undefined} onMount={handleMount} />
      )}
    </div>
  );
}
