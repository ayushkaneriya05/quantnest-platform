import * as React from "react"
import { cn } from "@/shared/lib/utils"

export const TimePicker = React.forwardRef(({ className, ...props }, ref) => {
  return (
    <input
      type="time"
      className={cn(
        "flex h-11 w-full rounded-md border border-gray-700 bg-gray-800/80 px-3 py-2 text-sm text-white shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-gray-400 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-indigo-500 disabled:cursor-not-allowed disabled:opacity-50 [color-scheme:dark] font-mono",
        className
      )}
      ref={ref}
      {...props}
    />
  )
})
TimePicker.displayName = "TimePicker"
