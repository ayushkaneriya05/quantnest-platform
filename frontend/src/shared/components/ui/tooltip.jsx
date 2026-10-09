import * as React from "react";
import PropTypes from "prop-types";
import * as TooltipPrimitive from "@radix-ui/react-tooltip";

import { cn } from "@/shared/lib/utils";

function TooltipProvider({ delayDuration = 250, ...props }) {
  return <TooltipPrimitive.Provider delayDuration={delayDuration} {...props} />;
}
TooltipProvider.propTypes = { delayDuration: PropTypes.number };

const Tooltip = TooltipPrimitive.Root;

const TooltipTrigger = TooltipPrimitive.Trigger;

// Tooltip portals can be outside a parent modal's scroll lock.
const TooltipContent = React.forwardRef(
  ({ className, sideOffset = 6, onWheelCapture, onTouchMoveCapture, ...props }, ref) => (
    <TooltipPrimitive.Portal>
    <TooltipPrimitive.Content
      ref={ref}
      sideOffset={sideOffset}
      className={cn(
        "scrollbar-thin-theme pointer-events-auto z-[60] max-h-[min(20rem,var(--radix-tooltip-content-available-height))] max-w-[min(24rem,calc(100vw_-_2rem))] overflow-y-auto overscroll-contain whitespace-pre-wrap break-words rounded-md border bg-popover px-3 py-2 text-sm text-popover-foreground shadow-lg animate-in fade-in-0 zoom-in-95 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:zoom-in-95 data-[state=closed]:zoom-out-95 data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2",
        className
      )}
      onWheelCapture={(event) => {
        onWheelCapture?.(event);
        event.stopPropagation();
      }}
      onTouchMoveCapture={(event) => {
        onTouchMoveCapture?.(event);
        event.stopPropagation();
      }}
      {...props}
    />
    </TooltipPrimitive.Portal>
  )
);
TooltipContent.displayName = TooltipPrimitive.Content.displayName;
TooltipContent.propTypes = { className: PropTypes.string, sideOffset: PropTypes.number,
  onWheelCapture: PropTypes.func, onTouchMoveCapture: PropTypes.func };

function TooltipHint({ content, children }) {
  if (!content) return children;
  return <TooltipProvider><Tooltip>
    <TooltipTrigger asChild>{children}</TooltipTrigger>
    <TooltipContent>{content}</TooltipContent>
  </Tooltip></TooltipProvider>;
}
TooltipHint.propTypes = { content: PropTypes.node, children: PropTypes.element.isRequired };

// Shared truncation handling for select values, version notes, and other long labels.
function OverflowTooltip({ children, className, active }) {
  const labelRef = React.useRef(null);
  const [truncated, setTruncated] = React.useState(false);
  const [hovered, setHovered] = React.useState(false);
  React.useLayoutEffect(() => {
    const label = labelRef.current;
    if (!label) return;
    const measure = () => setTruncated(label.scrollWidth > label.clientWidth);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(label);
    return () => observer.disconnect();
  }, [children]);
  return <TooltipProvider><Tooltip open={truncated && (active ?? hovered)} onOpenChange={setHovered}>
    <TooltipTrigger asChild><span ref={labelRef} className={cn("block min-w-0 truncate", className)}>{children}</span></TooltipTrigger>
    {truncated && <TooltipContent onPointerEnter={() => setHovered(true)}>{children}</TooltipContent>}
  </Tooltip></TooltipProvider>;
}
OverflowTooltip.propTypes = { children: PropTypes.node, className: PropTypes.string, active: PropTypes.bool };

export { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider, TooltipHint, OverflowTooltip };
