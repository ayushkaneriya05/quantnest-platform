import { useEffect } from "react";

// The visual viewport shrinks for mobile keyboards even when 100dvh does not.
export function useViewportHeight() {
  useEffect(() => {
    const viewport = window.visualViewport;
    let frame;
    const update = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        if (viewport && viewport.scale !== 1) return;
        document.documentElement.style.setProperty("--viewport-height", `${viewport?.height ?? window.innerHeight}px`);
      });
    };
    update();
    viewport?.addEventListener("resize", update);
    window.addEventListener("resize", update);
    return () => {
      cancelAnimationFrame(frame);
      viewport?.removeEventListener("resize", update);
      window.removeEventListener("resize", update);
      document.documentElement.style.removeProperty("--viewport-height");
    };
  }, []);
}
