import * as React from "react"
import { format, setMonth, setYear, setDate as setDayOfMonth } from "date-fns"
import { Calendar as CalendarIcon, ChevronLeft, ChevronRight } from "lucide-react"

import { cn } from "@/shared/lib/utils"
import { Button } from "@/shared/components/ui/button"
import { Calendar } from "@/shared/components/ui/calendar"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/shared/components/ui/popover"

export function DatePicker({ date, setDate, className, placeholder = "Pick a date" }) {
  const [open, setOpen] = React.useState(false)
  const [displayMonth, setDisplayMonth] = React.useState(date || new Date())
  const [view, setView] = React.useState("days")

  const currentYear = new Date().getFullYear()
  const years = Array.from({ length: 40 }).map((_, i) => currentYear - 20 + i)

  const monthNames = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
  ]

  React.useEffect(() => {
    if (date) setDisplayMonth(date)
  }, [date?.getTime()])

  React.useEffect(() => {
    if (open) setView("days")
  }, [open])

  const goToPrevMonth = () => {
    setDisplayMonth(prev => {
      const d = new Date(prev)
      d.setMonth(d.getMonth() - 1)
      return d
    })
  }

  const goToNextMonth = () => {
    setDisplayMonth(prev => {
      const d = new Date(prev)
      d.setMonth(d.getMonth() + 1)
      return d
    })
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          className={cn(
            "w-full justify-start text-left font-normal bg-secondary/80 border-border h-11 text-foreground hover:bg-muted/80 hover:text-foreground",
            !date && "text-muted-foreground",
            className
          )}
        >
          <CalendarIcon className="mr-2 h-4 w-4 text-muted-foreground" />
          <span className="min-w-0 truncate">{date ? format(date, "PPP") : placeholder}</span>
        </Button>
      </PopoverTrigger>
      <PopoverContent
        className="w-auto p-0 bg-card border border-border/50 text-foreground shadow-2xl shadow-black/40 rounded-xl overflow-y-auto"
        align="start"
      >
        {/* Custom Header */}
        <div className="px-3 pt-3 pb-2 border-b border-border/80 flex items-center justify-between">
          <div className="flex items-center gap-0.5">
            {view === "days" && (
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 text-muted-foreground hover:text-foreground hover:bg-secondary"
                aria-label="Previous month" onClick={goToPrevMonth}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
            )}
            <Button
              variant="ghost"
              className="h-8 px-2 hover:bg-secondary hover:text-foreground font-semibold text-sm text-foreground"
              onClick={() => setView(view === "months" ? "days" : "months")}
            >
              {format(displayMonth, "MMMM")}
            </Button>
            <Button
              variant="ghost"
              className="h-8 px-2 hover:bg-secondary hover:text-foreground font-semibold text-sm text-foreground"
              onClick={() => setView(view === "years" ? "days" : "years")}
            >
              {displayMonth.getFullYear()}
            </Button>
            {view === "days" && (
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 text-muted-foreground hover:text-foreground hover:bg-secondary"
                aria-label="Next month" onClick={goToNextMonth}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            )}
          </div>
          <Button
            variant="ghost"
            className="h-7 px-2.5 hover:bg-secondary text-xs text-indigo-700 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300 font-semibold"
            onClick={() => {
              const today = new Date()
              setDisplayMonth(today)
              setView("days")
              setDate(today)
              setOpen(false)
            }}
          >
            Today
          </Button>
        </div>

        {/* Day View */}
        {view === "days" && (
          <Calendar
            mode="single"
            selected={date}
            onSelect={(newDate) => {
              setDate(newDate)
              if (newDate) {
                setDisplayMonth(newDate)
                setOpen(false)
              }
            }}
            month={displayMonth}
            onMonthChange={setDisplayMonth}
            hideHeader
            className="p-3"
          />
        )}

        {/* Month View */}
        {view === "months" && (
          <div className="grid grid-cols-3 gap-1.5 p-4">
            {monthNames.map((monthStr, index) => (
              <Button
                key={monthStr}
                variant="ghost"
                className={cn(
                  "h-10 rounded-lg text-sm font-medium transition-all hover:bg-secondary hover:text-foreground",
                  displayMonth.getMonth() === index
                    ? "bg-indigo-600 text-white hover:bg-indigo-700"
                    : "text-foreground"
                )}
                onClick={() => {
                  setDisplayMonth(setMonth(setDayOfMonth(displayMonth, 1), index))
                  setView("days")
                }}
              >
                {monthStr.slice(0, 3)}
              </Button>
            ))}
          </div>
        )}

        {/* Year View */}
        {view === "years" && (
          <div className="grid grid-cols-4 gap-1.5 p-4 max-h-[280px] overflow-y-auto scrollbar-thin-theme">
            {years.map((year) => (
              <Button
                key={year}
                variant="ghost"
                className={cn(
                  "h-10 rounded-lg text-sm font-medium transition-all hover:bg-secondary hover:text-foreground",
                  displayMonth.getFullYear() === year
                    ? "bg-indigo-600 text-white hover:bg-indigo-700"
                    : "text-foreground"
                )}
                onClick={() => {
                  setDisplayMonth(setYear(setDayOfMonth(displayMonth, 1), year))
                  setView("days")
                }}
              >
                {year}
              </Button>
            ))}
          </div>
        )}
      </PopoverContent>
    </Popover>
  )
}
