import PropTypes from "prop-types";
import * as React from "react";
import { setMonth, setYear, setDate as setDayOfMonth } from "date-fns";
import {
  Calendar as CalendarIcon,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

import { formatDate } from "@/shared/utils/formatters";
import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/components/ui/button";
import { Calendar } from "@/shared/components/ui/calendar";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/shared/components/ui/popover";

export function DatePicker({
  date,
  setDate,
  className,
  placeholder = "Pick a date",
}) {
  const [open, setOpen] = React.useState(false);
  const [displayMonth, setDisplayMonth] = React.useState(date || new Date());
  const [view, setView] = React.useState("days");

  const currentYear = new Date().getFullYear();
  const years = Array.from({ length: 40 }).map((_, i) => currentYear - 20 + i);

  const monthNames = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
  ];

  const dateTime = date?.getTime();
  React.useEffect(() => {
    if (dateTime != null) setDisplayMonth(new Date(dateTime));
  }, [dateTime]);

  React.useEffect(() => {
    if (open) setView("days");
  }, [open]);

  const goToPrevMonth = () => {
    setDisplayMonth((prev) => {
      const d = new Date(prev);
      d.setMonth(d.getMonth() - 1);
      return d;
    });
  };

  const goToNextMonth = () => {
    setDisplayMonth((prev) => {
      const d = new Date(prev);
      d.setMonth(d.getMonth() + 1);
      return d;
    });
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          className={cn(
            "w-full justify-start text-left font-normal",
            !date && "text-muted-foreground",
            className,
          )}
        >
          <CalendarIcon className="h-4 w-4 text-muted-foreground" />
          <span className="min-w-0 truncate">
            {date ? formatDate(date) : placeholder}
          </span>
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
                className="w-7"
                aria-label="Previous month"
                onClick={goToPrevMonth}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
            )}
            <Button
              variant="ghost"
              className="px-2 font-semibold text-sm"
              onClick={() => setView(view === "months" ? "days" : "months")}
            >
              {formatDate(displayMonth, { month: "long" })}
            </Button>
            <Button
              variant="ghost"
              className="px-2 font-semibold text-sm"
              onClick={() => setView(view === "years" ? "days" : "years")}
            >
              {displayMonth.getFullYear()}
            </Button>
            {view === "days" && (
              <Button
                variant="ghost"
                size="icon"
                className="w-7"
                aria-label="Next month"
                onClick={goToNextMonth}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            )}
          </div>
          <Button
            variant="ghost"
            className="px-2.5 text-xs font-semibold"
            onClick={() => {
              const today = new Date();
              setDisplayMonth(today);
              setView("days");
              setDate(today);
              setOpen(false);
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
              setDate(newDate);
              if (newDate) {
                setDisplayMonth(newDate);
                setOpen(false);
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
                variant={displayMonth.getMonth() === index ? "default" : "ghost"}
                aria-pressed={displayMonth.getMonth() === index}
                className=""
                onClick={() => {
                  setDisplayMonth(
                    setMonth(setDayOfMonth(displayMonth, 1), index),
                  );
                  setView("days");
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
                variant={displayMonth.getFullYear() === year ? "default" : "ghost"}
                aria-pressed={displayMonth.getFullYear() === year}
                className=""
                onClick={() => {
                  setDisplayMonth(
                    setYear(setDayOfMonth(displayMonth, 1), year),
                  );
                  setView("days");
                }}
              >
                {year}
              </Button>
            ))}
          </div>
        )}
      </PopoverContent>
    </Popover>
  );
}

DatePicker.propTypes = {
  ...DatePicker.propTypes,
  className: PropTypes.string,
  date: PropTypes.instanceOf(Date),
  placeholder: PropTypes.string,
  setDate: PropTypes.func,
};
