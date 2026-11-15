import { useEffect, type RefObject } from "react";

/** Keep native scrolling inside lists, and let the page take over at their edges. */
export function useWorkspaceWheel(root: RefObject<HTMLDivElement | null>, enabled = true) {
  useEffect(() => {
    const shell = root.current;
    if (!shell || !enabled) return;
    const wheel = (event: WheelEvent) => {
      if (event.defaultPrevented || event.ctrlKey || event.metaKey || event.shiftKey || !event.deltaY || Math.abs(event.deltaX) > Math.abs(event.deltaY)) return;
      const target = event.target instanceof Element ? event.target : null;
      if (!target || target.closest('dialog,[role="dialog"],select,textarea,input[type="number"]')) return;
      const down = event.deltaY > 0;
      for (let element: Element | null = target; element && shell.contains(element); element = element.parentElement) {
        const style = getComputedStyle(element);
        if (!/^(auto|scroll)$/.test(style.overflowY)) continue;
        const remaining = element.scrollHeight - element.clientHeight;
        if (remaining > 1 && (down ? element.scrollTop < remaining - 1 : element.scrollTop > 1)) return;
      }
      const page = document.scrollingElement || document.documentElement;
      const remaining = page.scrollHeight - page.clientHeight;
      if (remaining <= 1 || (down ? page.scrollTop >= remaining - 1 : page.scrollTop <= 1)) return;
      const delta = event.deltaY * (event.deltaMode === 1 ? 20 : event.deltaMode === 2 ? window.innerHeight : 1);
      event.preventDefault();
      window.scrollBy({top: delta, behavior: "instant"});
    };
    shell.addEventListener("wheel", wheel, {passive: false});
    return () => shell.removeEventListener("wheel", wheel);
  }, [root, enabled]);
}
