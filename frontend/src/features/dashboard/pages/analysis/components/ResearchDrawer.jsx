import PropTypes from "prop-types";
import { Dialog, DialogContent, DialogTitle, DialogDescription } from "@/shared/components/ui/dialog";

export default function ResearchDrawer({ open, onOpenChange, title, children }) {
  return <Dialog open={open} onOpenChange={onOpenChange}><DialogContent className="left-auto right-0 top-0 flex h-[100dvh] w-full max-w-[420px] translate-x-0 translate-y-0 flex-col rounded-none border-slate-800 bg-slate-950 p-5 data-[state=open]:slide-in-from-right data-[state=closed]:slide-out-to-right">
    <DialogTitle className="pr-8 text-slate-100">{title}</DialogTitle><DialogDescription className="sr-only">Research details. Press Escape or use Close to return to the conversation.</DialogDescription>
    <div className="scrollbar-theme min-h-0 flex-1 overflow-y-auto overscroll-contain pr-1">{children}</div>
  </DialogContent></Dialog>;
}
ResearchDrawer.propTypes = { open: PropTypes.bool.isRequired, onOpenChange: PropTypes.func.isRequired, title: PropTypes.string.isRequired, children: PropTypes.node };
