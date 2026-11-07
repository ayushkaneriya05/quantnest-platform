import PropTypes from "prop-types";
import { Plus, Trash2 } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { TimePicker } from "@/shared/components/ui/time-picker";
import { Radio } from "@/shared/components/ui/radio";
import { useStrategySpecification } from "@/shared/context/EnumsContext";
import { StudioSelect } from "./ExpressionEditor";

export default function StudioSchedule({
  value,
  onChange,
  customDays,
  onCustomDaysChange,
  issues,
}) {
  const { enums, spec, choicesFor } = useStrategySpecification();
  const fields = spec.schedule.fields;
  const update = (key, next) => onChange({ ...value, [key]: next });
  const windows = value.no_trade_windows || [];
  const timeInput = (key, label, id) => (
    <label className="studio-field" htmlFor={id}>
      <span>{label}</span>
      <TimePicker
        id={id}
        value={value[key] || ""}
        step={1}
        onChange={(event) => update(key, event.target.value || null)}
        aria-invalid={
          issues.some((issue) => issue.selector === `#${id}`) || undefined
        }
        aria-describedby={
          issues.some((issue) => issue.selector === `#${id}`)
            ? `${id}-error`
            : undefined
        }
      />
      {issues
        .filter((issue) => issue.selector === `#${id}`)
        .map((issue) => (
          <span
            key={issue.selector}
            id={`${id}-error`}
            className="text-sm text-destructive"
          >
            {issue.message}
          </span>
        ))}
      <span className="studio-hint">
        {value[key] ? "Schedule timezone" : "No additional restriction"}
      </span>
    </label>
  );
  const dayLabels = (value.trading_days || []).map(
    (day) => enums.TradingDay?.find((item) => item.value === day)?.label || day,
  );
  return (
    <div className="studio-schedule studio-surface">
      <fieldset className="studio-section">
        <legend>Rule timing</legend>
        <div className="studio-field-grid">
          <label className="studio-field">
            <span>{fields.candle_timeframe.label}</span>
            <StudioSelect
              label="Default timeframe"
              value={value.candle_timeframe}
              options={choicesFor(fields.candle_timeframe)}
              onChange={(next) => update("candle_timeframe", next)}
            />
          </label>
          <label className="studio-field">
            <span>{fields.timezone.label}</span>
            <StudioSelect
              label="Schedule timezone"
              value={value.timezone}
              options={choicesFor(fields.timezone)}
              onChange={(next) => update("timezone", next)}
            />
          </label>
        </div>
        <p className="studio-hint">
          Inputs set to Default inherit this timeframe. LTP uses live prices.
          Changing timezone keeps your entered times and changes how they are
          interpreted.
        </p>
      </fieldset>
      <fieldset className="studio-section" data-schedule-days tabIndex={-1}>
        <legend>Entry availability</legend>
        <div className="flex flex-wrap gap-x-5 gap-y-2 text-sm">
          <label className="flex min-h-9 items-center gap-2">
            <Radio
              name="studio-weekdays"
              checked={!customDays}
              onChange={() => {
                onCustomDaysChange(false);
                update("trading_days", []);
              }}
            />
            All exchange trading days
          </label>
          <label className="flex min-h-9 items-center gap-2">
            <Radio
              name="studio-weekdays"
              checked={customDays}
              onChange={() => onCustomDaysChange(true)}
            />
            Selected weekdays
          </label>
        </div>
        {customDays && (
          <div
            className="flex flex-wrap gap-1.5"
            role="group"
            aria-label="Entry weekdays"
          >
            {(enums.TradingDay || []).map((day) => {
              const selected = value.trading_days.includes(day.value);
              return (
                <Button
                  key={day.value}
                  size="sm"
                  aria-pressed={selected}
                  variant={selected ? "selected" : "outline"}
                  onClick={() =>
                    update(
                      "trading_days",
                      selected
                        ? value.trading_days.filter(
                            (item) => item !== day.value,
                          )
                        : [...value.trading_days, day.value],
                    )
                  }
                >
                  {day.label}
                </Button>
              );
            })}
          </div>
        )}
        {customDays && !value.trading_days.length && (
          <p className="text-sm text-destructive">
            Choose at least one weekday, or select All exchange trading days.
          </p>
        )}
        <div className="studio-field-grid">
          {timeInput("start_time", "Entry start", "studio-entry-start")}
          {timeInput("end_time", "Entry end", "studio-entry-end")}
        </div>
        <p className="studio-hint">
          Entry end stops new entries; it does not close positions or cancel
          pending orders. Existing positions follow their exit rules. Time
          bounds include their exact boundary instant.
        </p>
      </fieldset>
      <fieldset className="studio-section">
        <legend>Excluded entry windows</legend>
        <div className="space-y-2">
          {!windows.length && (
            <p className="studio-hint">No excluded entry windows.</p>
          )}
          {windows.map((window, index) => (
            <div
              key={index}
              data-window-index={index}
              className="studio-window-row"
            >
              {["start", "end"].map((key) => (
                <label key={key} className="studio-field">
                  <span>{key === "start" ? "From" : "To"}</span>
                  <TimePicker
                    aria-label={`Excluded window ${index + 1} ${key}`}
                    value={window[key]}
                    step={1}
                    onChange={(event) =>
                      update(
                        "no_trade_windows",
                        windows.map((item, i) =>
                          i === index
                            ? { ...item, [key]: event.target.value }
                            : item,
                        ),
                      )
                    }
                  />
                </label>
              ))}
              <Button
                variant="ghost"
                size="icon"
                aria-label={`Remove excluded window ${index + 1}`}
                onClick={() =>
                  update(
                    "no_trade_windows",
                    windows.filter((_, i) => i !== index),
                  )
                }
              >
                <Trash2 className="h-4 w-4" />
              </Button>
              {issues
                .filter(
                  (issue) =>
                    issue.selector === `[data-window-index="${index}"] input`,
                )
                .map((issue) => (
                  <p
                    key={issue.selector}
                    className="col-span-full text-sm text-destructive"
                  >
                    {issue.message}
                  </p>
                ))}
            </div>
          ))}
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() =>
            update("no_trade_windows", [...windows, { start: "", end: "" }])
          }
        >
          <Plus className="mr-1 h-4 w-4" />
          Add window
        </Button>
        <p className="studio-hint">
          Windows use the schedule timezone and cannot span midnight. Exchange
          sessions and holidays still apply to each traded contract.
        </p>
      </fieldset>
      <div className="studio-schedule-summary" aria-live="polite">
        <strong className="block text-sm">Entry schedule</strong>
        <p className="mt-1 text-sm text-muted-foreground">
          {customDays
            ? dayLabels.join(", ") || "Choose weekdays"
            : "All exchange trading days"}
          {` · ${value.start_time || "No start restriction"} → ${value.end_time || "No end restriction"} · ${value.timezone}`}
        </p>
        {windows.length > 0 && (
          <p className="mt-1 text-sm text-muted-foreground">
            Excluding{" "}
            {windows
              .map(
                (window) =>
                  `${window.start || "incomplete"}–${window.end || "incomplete"}`,
              )
              .join(", ")}
            .
          </p>
        )}
        <p className="studio-hint mt-1">
          Configured entry restrictions, subject to each contract’s exchange
          calendar.
        </p>
      </div>
    </div>
  );
}
StudioSchedule.propTypes = {
  value: PropTypes.object.isRequired,
  onChange: PropTypes.func.isRequired,
  customDays: PropTypes.bool.isRequired,
  onCustomDaysChange: PropTypes.func.isRequired,
  issues: PropTypes.array.isRequired,
};
