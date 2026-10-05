import { type RefObject, useEffect } from "react";

/**
 * Closes an open popover on Escape (returning focus to its trigger) and on a pointer press outside of it and
 * its trigger, the way the report menu does.
 */
export function useDismiss(
  open: boolean,
  close: () => void,
  popover: RefObject<HTMLElement | null>,
  trigger: RefObject<HTMLElement | null>,
) {
  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      close();
      trigger.current?.focus();
    };
    const onPointerDown = (event: PointerEvent) => {
      const target = event.target as Node;
      if (popover.current?.contains(target) || trigger.current?.contains(target)) return;
      close();
    };
    document.addEventListener("keydown", onKeyDown);
    document.addEventListener("pointerdown", onPointerDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.removeEventListener("pointerdown", onPointerDown);
    };
  }, [open, close, popover, trigger]);
}
