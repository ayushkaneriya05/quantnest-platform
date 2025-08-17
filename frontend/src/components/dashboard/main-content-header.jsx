import React, { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { PanelLeft, PanelLeftClose } from "lucide-react";
import { useSidebar } from "@/contexts/sidebar-context";

export default function MainContentHeader({
  title = "Dashboard",
  subtitle,
  actions,
}) {
  const { toggle, isOpen } = useSidebar();

  // Add keyboard shortcut (Ctrl/Cmd + B)
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "b") {
        e.preventDefault();
        toggle();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [toggle]);

  return (
    <div
      className={`sticky top-0 z-10 flex items-center justify-between border-b border-gray-800 bg-gray-950/95 backdrop-blur-sm px-3 sm:px-4 md:px-6 ${
        subtitle ? "h-16 sm:h-20" : "h-14 sm:h-16"
      }`}
    >
      <div className="flex items-center gap-2 sm:gap-4 min-w-0 flex-1">
        <Button
          variant="ghost"
          size="sm"
          onClick={toggle}
          className="text-slate-400 hover:text-slate-100 hover:bg-gray-800/70 p-1.5 sm:p-2 transition-all duration-200 rounded-lg group shrink-0 focus-ring touch-target"
          title={`${isOpen ? "Close" : "Open"} Sidebar (Ctrl+B)`}
        >
          {isOpen ? (
            <PanelLeftClose className="h-4 w-4 sm:h-5 sm:w-5 transition-transform group-hover:scale-110" />
          ) : (
            <PanelLeft className="h-4 w-4 sm:h-5 sm:w-5 transition-transform group-hover:scale-110" />
          )}
        </Button>
        <div className="flex flex-col min-w-0 flex-1">
          <h1 className="text-base sm:text-lg md:text-xl font-semibold text-slate-100 truncate">
            {title}
          </h1>
          {subtitle && (
            <p className="text-xs sm:text-sm text-slate-400 mt-0.5 sm:mt-1 truncate">
              {subtitle}
            </p>
          )}
        </div>
      </div>
      {actions && (
        <div className="flex items-center gap-1 sm:gap-2 shrink-0 ml-2">
          {actions}
        </div>
      )}
    </div>
  );
}
