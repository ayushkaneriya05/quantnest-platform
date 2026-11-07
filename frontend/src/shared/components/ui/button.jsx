import * as React from "react";
import PropTypes from "prop-types";
import { Slot } from "@radix-ui/react-slot";
import { cva } from "class-variance-authority";

import { cn } from "@/shared/lib/utils";
import { TooltipHint } from "./tooltip";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-1.5 whitespace-nowrap rounded-md text-sm leading-tight font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default: "bg-brand text-brand-foreground hover:bg-brand/90",
        destructive:
          "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        outline:
          "border border-input/70 bg-transparent text-foreground hover:border-input hover:bg-muted/50",
        secondary:
          "bg-secondary text-secondary-foreground hover:bg-muted",
        ghost: "bg-transparent text-foreground hover:bg-muted/50",
        plain: "bg-transparent text-inherit",
        link: "text-brand underline-offset-4 hover:underline",
        selected: "border border-brand/50 bg-brand/10 text-brand hover:bg-brand/15",
        success: "bg-success text-success-foreground hover:bg-success/90",
        sell: "bg-loss text-loss-foreground hover:bg-loss/90",
        warning: "border border-warning/50 bg-warning/5 text-warning hover:bg-warning/15",
        "destructive-outline": "border border-destructive-text/40 bg-transparent text-destructive-text hover:bg-destructive/10",
      },
      size: {
        default: "h-[var(--control-height)] px-3 py-1",
        sm: "h-[var(--control-height-sm)] rounded-md px-2.5 py-1",
        lg: "h-[var(--control-height-lg)] rounded-md px-5 py-1.5",
        icon: "h-[var(--control-height)] w-[var(--control-height)] p-0",
        content: "h-auto min-w-0 p-0",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

const Button = React.forwardRef(
  ({ className, variant, size, asChild = false, title, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    const button = (
      <Comp
        data-ui="button"
        data-variant={variant || "default"}
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        aria-label={props["aria-label"] || title}
        {...props}
      />
    );
    return title ? <TooltipHint content={title}>{button}</TooltipHint> : button;
  },
);
Button.displayName = "Button";
Button.propTypes = {
  className: PropTypes.string,
  variant: PropTypes.string,
  size: PropTypes.string,
  asChild: PropTypes.bool,
  title: PropTypes.string,
  "aria-label": PropTypes.string,
};

export { Button, buttonVariants };
