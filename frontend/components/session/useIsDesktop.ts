"use client";

import { useEffect, useState } from "react";

// Matches Tailwind's default `md` breakpoint — kept as a real JS check
// (not a CSS `hidden md:flex` pair) so the desktop and mobile session
// layouts never both mount at once: each holds a live Daily call, a
// Realtime subscription, and a tldraw editor, and doubling any of those
// up is not just wasteful, it duplicates side effects.
const DESKTOP_BREAKPOINT_QUERY: string = "(min-width: 768px)";

export function useIsDesktop(): boolean {
  const [isDesktop, setIsDesktop] = useState(() =>
    typeof window === "undefined" ? true : window.matchMedia(DESKTOP_BREAKPOINT_QUERY).matches,
  );

  useEffect(() => {
    const mediaQuery = window.matchMedia(DESKTOP_BREAKPOINT_QUERY);
    const handleChange = () => setIsDesktop(mediaQuery.matches);
    handleChange();
    mediaQuery.addEventListener("change", handleChange);
    return () => mediaQuery.removeEventListener("change", handleChange);
  }, []);

  return isDesktop;
}
