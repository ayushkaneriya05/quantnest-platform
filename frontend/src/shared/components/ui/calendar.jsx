import * as React from "react"
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
        caption_label: hideHeader ? "hidden" : "text-sm font-medium text-slate-200",
        nav: hideHeader ? "hidden" : "space-x-1 flex items-center",
        nav_button: cn(
          buttonVariants({ variant: "outline" }),
          "h-7 w-7 bg-transparent border-gray-700 p-0 text-slate-400 opacity-70 hover:opacity-100 hover:bg-gray-800 hover:text-slate-200"
        ),
        nav_button_previous: "absolute left-1",
        nav_button_next: "absolute right-1",
        month_grid: "w-full border-collapse space-y-1",
        weekdays: "flex w-full justify-between",
        weekday: "text-slate-500 rounded-md w-9 font-medium text-[0.75rem] text-center",
        week: "flex w-full mt-2 justify-between",
        day: cn(
          "relative h-9 w-9 text-center text-sm p-0",
          "focus-within:relative focus-within:z-20",
          "[&:has([aria-selected])]:bg-indigo-600/10 [&:has([aria-selected])]:rounded-md"
        ),
        day_button: cn(
          buttonVariants({ variant: "ghost" }),
          "h-9 w-9 p-0 font-normal text-slate-300 hover:bg-gray-700/70 hover:text-slate-100 aria-selected:opacity-100 transition-colors"
        ),
        range_end: "day-range-end",
        selected: "bg-indigo-600 text-white hover:bg-indigo-500 hover:text-white focus:bg-indigo-600 focus:text-white rounded-md",
        today: "bg-gray-800 text-slate-100 font-semibold ring-1 ring-indigo-500/40 rounded-md",
        outside: "day-outside text-slate-600 opacity-40 aria-selected:bg-indigo-600/5 aria-selected:text-slate-500 aria-selected:opacity-30",
        disabled: "text-slate-600 opacity-30",
        range_middle: "aria-selected:bg-indigo-600/10 aria-selected:text-slate-200",
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
