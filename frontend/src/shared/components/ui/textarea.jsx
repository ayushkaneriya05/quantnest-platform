import * as React from "react"
import PropTypes from "prop-types"

import { cn } from "@/shared/lib/utils"
import { TooltipHint } from "./tooltip"

const Textarea = React.forwardRef(({ className, title, ...props }, ref) => {
  const textarea = (
    <textarea
      className={cn(
        "scrollbar-thin-theme flex min-h-[80px] min-w-0 w-full max-w-full rounded-md border border-input bg-background px-3 py-2 text-base text-foreground ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset disabled:cursor-not-allowed disabled:opacity-50 md:text-sm",
        className
      )}
      ref={ref}
      {...props}
    />
  )
  return title ? <TooltipHint content={title}>{textarea}</TooltipHint> : textarea
})
Textarea.displayName = "Textarea"
Textarea.propTypes = { className: PropTypes.string, title: PropTypes.string }

export { Textarea }
