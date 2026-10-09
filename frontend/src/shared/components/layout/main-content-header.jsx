import { useEffect } from "react";
import PropTypes from "prop-types";
import { PanelLeft, PanelLeftClose } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { useSidebar } from "@/shared/hooks/useSidebar";

export default function MainContentHeader({ title, subtitle, actions, customContent }) {
  const { toggle, isOpen } = useSidebar();
  useEffect(() => {
    const handleKeyDown = (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key === "b" && !event.target.closest("input, textarea, [contenteditable=true]")) {
        event.preventDefault(); toggle();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [toggle]);
  return <header className="z-20 flex shrink-0 flex-wrap items-center gap-x-3 gap-y-2 border-b bg-card/95 px-3 py-2 backdrop-blur sm:px-5 sm:py-3">
    <div className="flex min-w-0 flex-1 items-center gap-2 sm:gap-4">
      <Button id="workspace-navigation-toggle" variant="ghost" size="icon" onClick={toggle} className="touch-target shrink-0" aria-expanded={isOpen} aria-label={isOpen ? "Close navigation" : "Open navigation"}>
        {isOpen ? <PanelLeftClose className="h-5 w-5" /> : <PanelLeft className="h-5 w-5" />}
      </Button>
      <div className="min-w-0 flex-1">
        {customContent || <><h1 className="truncate text-base font-semibold sm:text-xl">{title}</h1>{subtitle && <p className="mt-0.5 hidden truncate text-sm text-muted-foreground md:block">{subtitle}</p>}</>}
      </div>
    </div>
    {actions && <div className="page-toolbar w-full justify-end border-t pt-2 [&>*]:max-w-full sm:w-auto sm:border-0 sm:pt-0">{actions}</div>}
  </header>;
}
MainContentHeader.propTypes = { title: PropTypes.string, subtitle: PropTypes.string, actions: PropTypes.node, customContent: PropTypes.node };
