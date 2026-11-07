import { useEffect } from "react";
import PropTypes from "prop-types";
import { PanelLeft, PanelLeftClose } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { useSidebar } from "@/shared/hooks/useSidebar";

export default function MainContentHeader({
  title,
  subtitle,
  actions,
  customContent,
}) {
  const { toggle, isOpen } = useSidebar();
  useEffect(() => {
    const handleKeyDown = (event) => {
      if (
        (event.ctrlKey || event.metaKey) &&
        event.key === "b" &&
        !event.target.closest("input, textarea, [contenteditable=true]")
      ) {
        event.preventDefault();
        toggle();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [toggle]);
  return (
    <header className="workspace-header scrollbar-thin-theme z-20 border-b bg-card/95 backdrop-blur">
      <div className="workspace-header-main">
        <Button
          id="workspace-navigation-toggle"
          variant="ghost"
          size="icon"
          onClick={toggle}
          className="shrink-0"
          aria-expanded={isOpen}
          aria-label={isOpen ? "Close navigation" : "Open navigation"}
        >
          {isOpen ? (
            <PanelLeftClose className="h-5 w-5" />
          ) : (
            <PanelLeft className="h-5 w-5" />
          )}
        </Button>
        <div className="min-w-0 flex-1">
          {customContent || (
            <>
              <h1 className="truncate text-base font-semibold">{title}</h1>
              {subtitle && (
                <p className="hidden truncate text-xs text-muted-foreground md:block">
                  {subtitle}
                </p>
              )}
            </>
          )}
        </div>
      </div>
      {actions && <div className="workspace-header-actions">{actions}</div>}
    </header>
  );
}
MainContentHeader.propTypes = {
  title: PropTypes.string,
  subtitle: PropTypes.string,
  actions: PropTypes.node,
  customContent: PropTypes.node,
};
