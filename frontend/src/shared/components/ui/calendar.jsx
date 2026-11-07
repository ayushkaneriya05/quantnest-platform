import PropTypes from "prop-types";
import { ChevronLeft, ChevronRight } from "lucide-react"
import { DayPicker } from "react-day-picker"

import { cn } from "@/shared/lib/utils"
import { buttonVariants } from "@/shared/components/ui/button"

function Calendar({
  className,
  classNames,
  showOutsideDays = true,
  hideHeader = false,
  ...props
}) {
  const components = {
    IconLeft: () => <ChevronLeft className="h-4 w-4" />,
    IconRight: () => <ChevronRight className="h-4 w-4" />,
    ...(hideHeader ? { Caption: () => null } : {}),
    ...props.components,
  }

  return (
    <DayPicker
      showOutsideDays={showOutsideDays}
      className={cn("p-3", className)}
      classNames={{
        months: "flex flex-col sm:flex-row space-y-4 sm:space-x-4 sm:space-y-0",
        month: "space-y-4",
        caption: hideHeader ? "hidden" : "flex justify-center pt-1 relative items-center",
        caption_label: hideHeader ? "hidden" : "text-sm font-medium text-foreground",
        nav: hideHeader ? "hidden" : "space-x-1 flex items-center",
        nav_button: cn(
          buttonVariants({ variant: "outline" }),
          "h-7 w-7 bg-transparent border-border p-0 text-muted-foreground opacity-70 hover:opacity-100 hover:bg-secondary hover:text-foreground"
        ),
        nav_button_previous: "absolute left-1",
        nav_button_next: "absolute right-1",
        table: "w-full border-collapse space-y-1",
        head_row: "flex w-full justify-between",
        head_cell: "text-muted-foreground rounded-md w-9 font-medium text-[0.75rem] text-center",
        row: "flex w-full mt-2 justify-between",
        cell: cn(
          "relative h-9 w-9 text-center text-sm p-0",
          "focus-within:relative focus-within:z-20",
          "[&:has([aria-selected])]:bg-brand/10 [&:has([aria-selected])]:rounded-md"
        ),
        day: cn(
          buttonVariants({ variant: "ghost" }),
          "h-9 w-9 p-0 font-normal hover:bg-muted/70 aria-selected:bg-brand aria-selected:text-brand-foreground aria-selected:opacity-100"
        ),
        day_range_end: "day-range-end",
        day_selected: "rounded-md hover:bg-brand/90 hover:text-brand-foreground focus:bg-brand focus:text-brand-foreground",
        day_today: "rounded-md bg-secondary font-semibold ring-1 ring-brand/40",
        day_outside: "day-outside text-muted-foreground opacity-40 aria-selected:opacity-50",
        day_disabled: "text-muted-foreground opacity-30",
        day_range_middle: "aria-selected:bg-brand/10 aria-selected:text-foreground",
        day_hidden: "invisible",
        vhidden: "sr-only",
        ...classNames,
      }}
      components={components}
      {...props}
    />
  )
}
Calendar.displayName = "Calendar"

export { Calendar }

Calendar.propTypes = {
  ...Calendar.propTypes,
  className: PropTypes.string,
  classNames: PropTypes.object,
  components: PropTypes.object,
  hideHeader: PropTypes.bool,
  orientation: PropTypes.string,
  showOutsideDays: PropTypes.bool,
};
