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
    Chevron: (props) => {
      if (props.orientation === "left") {
        return <ChevronLeft className="h-4 w-4" />
      }
      return <ChevronRight className="h-4 w-4" />
    },
    ...(hideHeader ? { MonthCaption: () => null } : {}),
    ...props.components,
  }

  return (
    <DayPicker
      showOutsideDays={showOutsideDays}
      className={cn("p-3", className)}
      hideNavigation={hideHeader}
      classNames={{
        months: "flex flex-col sm:flex-row space-y-4 sm:space-x-4 sm:space-y-0",
        month: "space-y-4",
        month_caption: hideHeader ? "hidden" : "flex justify-center pt-1 relative items-center",
        caption_label: hideHeader ? "hidden" : "text-sm font-medium text-foreground",
        nav: hideHeader ? "hidden" : "space-x-1 flex items-center",
        nav_button: cn(
          buttonVariants({ variant: "outline" }),
          "h-7 w-7 bg-transparent border-border p-0 text-muted-foreground opacity-70 hover:opacity-100 hover:bg-secondary hover:text-foreground"
        ),
        nav_button_previous: "absolute left-1",
        nav_button_next: "absolute right-1",
        month_grid: "w-full border-collapse space-y-1",
        weekdays: "flex w-full justify-between",
        weekday: "text-muted-foreground rounded-md w-9 font-medium text-[0.75rem] text-center",
        week: "flex w-full mt-2 justify-between",
        day: cn(
          "relative h-9 w-9 text-center text-sm p-0",
          "focus-within:relative focus-within:z-20",
          "[&:has([aria-selected])]:bg-indigo-600/10 [&:has([aria-selected])]:rounded-md"
        ),
        day_button: cn(
          buttonVariants({ variant: "ghost" }),
          "h-9 w-9 p-0 font-normal text-foreground hover:bg-muted/70 hover:text-foreground aria-selected:opacity-100 transition-colors"
        ),
        range_end: "day-range-end",
        selected: "bg-indigo-600 text-white hover:bg-indigo-700 hover:text-white focus:bg-indigo-600 focus:text-white rounded-md",
        today: "bg-secondary text-foreground font-semibold ring-1 ring-indigo-500/40 rounded-md",
        outside: "day-outside text-muted-foreground opacity-40 aria-selected:bg-indigo-600/5 aria-selected:text-muted-foreground aria-selected:opacity-30",
        disabled: "text-muted-foreground opacity-30",
        range_middle: "aria-selected:bg-indigo-600/10 aria-selected:text-foreground",
        hidden: "invisible",
        ...classNames,
      }}
      components={components}
      {...props}
    />
  )
}
Calendar.displayName = "Calendar"

export { Calendar }
