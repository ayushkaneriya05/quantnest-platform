import * as React from "react"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { DayPicker } from "react-day-picker"

import { cn } from "@/shared/lib/utils"
import { buttonVariants } from "@/shared/components/ui/button"

// Empty caption component to fully suppress DayPicker's built-in header
function EmptyCaption() {
  return null
}

function Calendar({
  className,
  classNames,
  showOutsideDays = true,
  hideHeader = false,
  ...props
}) {
  // Merge custom components with the option to suppress the header
  const components = {
    IconLeft: ({ ...iconProps }) => <ChevronLeft className="h-4 w-4" />,
    IconRight: ({ ...iconProps }) => <ChevronRight className="h-4 w-4" />,
    ...(hideHeader ? { Caption: EmptyCaption } : {}),
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
        caption_label: hideHeader ? "hidden" : "text-sm font-medium text-slate-200",
        nav: hideHeader ? "hidden" : "space-x-1 flex items-center",
        nav_button: cn(
          buttonVariants({ variant: "outline" }),
          "h-7 w-7 bg-transparent border-gray-700 p-0 text-slate-400 opacity-70 hover:opacity-100 hover:bg-gray-800 hover:text-slate-200"
        ),
        nav_button_previous: "absolute left-1",
        nav_button_next: "absolute right-1",
        table: "w-full border-collapse space-y-1",
        head_row: "flex w-full justify-between",
        head_cell:
          "text-slate-500 rounded-md w-9 font-medium text-[0.75rem] text-center",
        row: "flex w-full mt-2 justify-between",
        cell: cn(
          "relative h-9 w-9 text-center text-sm p-0",
          "focus-within:relative focus-within:z-20",
          "[&:has([aria-selected])]:bg-indigo-600/10 [&:has([aria-selected])]:rounded-md"
        ),
        day: cn(
          buttonVariants({ variant: "ghost" }),
          "h-9 w-9 p-0 font-normal text-slate-300 hover:bg-gray-700/70 hover:text-slate-100 aria-selected:opacity-100 transition-colors"
        ),
        day_range_end: "day-range-end",
        day_selected:
          "bg-indigo-600 text-white hover:bg-indigo-500 hover:text-white focus:bg-indigo-600 focus:text-white rounded-md",
        day_today:
          "bg-gray-800 text-slate-100 font-semibold ring-1 ring-indigo-500/40 rounded-md",
        day_outside:
          "day-outside text-slate-600 opacity-40 aria-selected:bg-indigo-600/5 aria-selected:text-slate-500 aria-selected:opacity-30",
        day_disabled: "text-slate-600 opacity-30",
        day_range_middle:
          "aria-selected:bg-indigo-600/10 aria-selected:text-slate-200",
        day_hidden: "invisible",
        ...classNames,
      }}
      components={components}
      {...props}
    />
  )
}
Calendar.displayName = "Calendar"

export { Calendar }
