import PropTypes from "prop-types";
import { cn } from "@/shared/lib/utils";

export default function PageTabs({ items, value, onValueChange, label = "Page sections", className }) {
  return <div role="group" aria-label={label} className={cn("scrollbar-thin-theme flex min-w-0 max-w-full items-center gap-1 overflow-x-auto rounded-lg border bg-muted/40 p-1", className)}>
    {items.map(({ value: key, label: text, icon: Icon }) => <button type="button" key={key} aria-pressed={value === key} onClick={() => onValueChange(key)} className={cn("flex min-h-10 shrink-0 items-center justify-center gap-2 whitespace-nowrap rounded-md px-3 text-xs font-medium focus-ring sm:text-sm", value === key ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:bg-accent hover:text-foreground")}>
      {Icon && <Icon aria-hidden="true" className="hidden h-4 w-4 sm:block" />}{text}
    </button>)}
  </div>;
}
PageTabs.propTypes = { items: PropTypes.arrayOf(PropTypes.shape({ value: PropTypes.string.isRequired, label: PropTypes.string.isRequired, icon: PropTypes.elementType })).isRequired, value: PropTypes.string.isRequired, onValueChange: PropTypes.func.isRequired, label: PropTypes.string, className: PropTypes.string };
