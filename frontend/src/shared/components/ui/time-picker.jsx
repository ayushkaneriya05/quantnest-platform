import * as React from "react"
import { cn } from "@/shared/lib/utils"

export const TimePicker = React.forwardRef(({ className, ...props }, ref) => {
  return (
    <input
      type="time"
      className={cn(
        "flex h-11 w-full rounded-md border border-border bg-secondary/80 px-3 py-2 text-sm text-foreground shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 [color-scheme:light] dark:[color-scheme:dark] font-mono",
        className
      )}
      ref={ref}
      {...props}
    />
  )
})
TimePicker.displayName = "TimePicker"
