import PropTypes from "prop-types";
import { Dialog, DialogContent, DialogTitle, DialogDescription } from "@/shared/components/ui/dialog";
import { cn } from "@/shared/lib/utils";

export default function ResearchDrawer({ open, onOpenChange, title, children, wide = false }) {
  return <Dialog open={open} onOpenChange={onOpenChange}><DialogContent data-layout={wide ? "dialog" : "sheet"} className={cn(
    "flex min-h-0 flex-col gap-0 overflow-hidden border-border bg-background p-0 sm:p-0",
    wide ? "h-[calc(var(--viewport-height)_-_2rem)] max-w-6xl" : "left-auto right-0 top-0 h-[var(--viewport-height)] w-full max-w-[420px] translate-x-0 translate-y-0 rounded-none sm:rounded-none data-[state=open]:slide-in-from-right data-[state=closed]:slide-out-to-right",
  )}>
    <div className="shrink-0 border-b border-border p-5 pr-14"><DialogTitle className="text-foreground">{title}</DialogTitle><DialogDescription className="sr-only">Research details. Press Escape or use Close to return to the conversation.</DialogDescription></div>
    <div className="scrollbar-theme min-h-0 min-w-0 flex-1 overflow-x-hidden overflow-y-auto overscroll-contain p-4 sm:p-6">{children}</div>
  </DialogContent></Dialog>;
}
ResearchDrawer.propTypes = { open: PropTypes.bool.isRequired, onOpenChange: PropTypes.func.isRequired, title: PropTypes.string.isRequired, children: PropTypes.node, wide: PropTypes.bool };
