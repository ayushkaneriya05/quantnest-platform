import PropTypes from "prop-types";
import * as React from "react";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import { Slot } from "@radix-ui/react-slot";
import { cn } from "@/shared/lib/utils";

// Route navigation, controlled view switches and Radix panels share one appearance.
// Only the panel tabs use Radix's tablist/tabpanel keyboard and ARIA relationships.
const listClass = "ui-tab-bar scrollbar-thin-theme inline-flex w-fit min-w-0 max-w-full items-center gap-1 overflow-x-auto";
const triggerClass = "ui-tab inline-flex h-[var(--control-height)] shrink-0 items-center justify-center gap-1.5 whitespace-nowrap rounded-md border border-transparent px-2.5 py-1 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted/50 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand disabled:pointer-events-none disabled:opacity-50 data-[state=active]:border-brand/40 data-[state=active]:bg-brand/10 data-[state=active]:text-brand data-[state=active]:hover:bg-brand/10 [&_svg]:h-4 [&_svg]:w-4 [&_svg]:shrink-0";
const listAppearance = (appearance) => appearance === "plain" ? "p-0" : "rounded-lg border border-border p-1";

const Tabs = TabsPrimitive.Root;

const TabBar = React.forwardRef(({ className, appearance = "outline", ...props }, ref) => (
  <div ref={ref} data-ui="tab-bar" className={cn(listClass, listAppearance(appearance), className)} {...props} />
));
TabBar.displayName = "TabBar";
TabBar.propTypes = { className: PropTypes.string, appearance: PropTypes.oneOf(["plain", "outline"]) };

const TabButton = React.forwardRef(({ className, active = false, asChild = false, ...props }, ref) => {
  const Comp = asChild ? Slot : "button";
  // Tooltip triggers also provide data-state; selection belongs to this control.
  return <Comp ref={ref} {...(!asChild && { type: "button" })} {...props}
    data-ui="tab" data-state={active ? "active" : "inactive"} className={cn(triggerClass, className)} />;
});
TabButton.displayName = "TabButton";
TabButton.propTypes = { className: PropTypes.string, active: PropTypes.bool, asChild: PropTypes.bool };

const TabsList = React.forwardRef(({ className, appearance = "outline", ...props }, ref) => (
  <TabsPrimitive.List ref={ref} data-ui="tab-bar" className={cn(listClass, listAppearance(appearance), className)} {...props} />
));
TabsList.displayName = TabsPrimitive.List.displayName;
TabsList.propTypes = TabBar.propTypes;

const TabsTrigger = React.forwardRef(({ className, ...props }, ref) => (
  <TabsPrimitive.Trigger ref={ref} data-ui="tab" className={cn(triggerClass, className)} {...props} />
));
TabsTrigger.displayName = TabsPrimitive.Trigger.displayName;
TabsTrigger.propTypes = { className: PropTypes.string };

const TabsContent = React.forwardRef(({ className, ...props }, ref) => (
  <TabsPrimitive.Content ref={ref} className={cn("mt-3 min-w-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand", className)} {...props} />
));
TabsContent.displayName = TabsPrimitive.Content.displayName;
TabsContent.propTypes = { className: PropTypes.string };

export { Tabs, TabBar, TabButton, TabsList, TabsTrigger, TabsContent };
