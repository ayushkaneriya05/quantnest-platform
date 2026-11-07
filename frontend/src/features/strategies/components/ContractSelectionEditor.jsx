import { useRef, useState } from "react";
import PropTypes from "prop-types";
import { useStrategySpecification } from "@/shared/context/EnumsContext";
import { instrumentsApi } from "@/shared/services/instrumentsApi";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import {
  formatCurrency,
  formatDate,
  formatDateInput,
  formatDateTime,
  formatNumber,
} from "@/shared/utils/formatters";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Switch } from "@/shared/components/ui/switch";
import { DatePicker } from "@/shared/components/ui/date-picker";
import { StudioSelect } from "./ExpressionEditor";

export default function ContractSelectionEditor({
  underlyingId,
  value,
  onChange,
}) {
  const { spec, values, choicesFor, changePolicy } = useStrategySpecification();
  const automatic = spec.markets.automatic;
  const fields = automatic.fields;
  const [result, setResult] = useState(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const request = useRef(0);
  const change = (values) => {
    request.current += 1;
    setBusy(false);
    setResult(null);
    setError("");
    onChange({ ...value, ...values });
  };
  const changeField = (key, next) => change(changePolicy(value, key, next));
  const preview = async () => {
    const sequence = ++request.current;
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const response = await instrumentsApi.selectionPreview(
        underlyingId,
        value,
      );
      if (sequence === request.current) setResult(response);
    } catch (failure) {
      if (sequence === request.current)
        setError(getApiErrorMessage(failure, "Could not resolve the policy."));
    } finally {
      if (sequence === request.current) setBusy(false);
    }
  };
  return (
    <div className="mt-2 space-y-3">
      <p className="text-xs text-muted-foreground">
        {automatic.description}
      </p>
      <div className="grid gap-2 sm:grid-cols-2">
        <label className="space-y-1 text-xs">
          {fields.instrument_type.label}
          <StudioSelect
            label="Selected contract family"
            value={value.instrument_type}
            options={choicesFor(fields.instrument_type)}
            onChange={(kind) => changeField("instrument_type", kind)}
          />
        </label>
        {value.instrument_type === values.InstrumentType.OPTION && (
          <label className="space-y-1 text-xs">
            {fields.option_type.label}
            <StudioSelect
              label="Option right"
              value={value.option_type}
              options={choicesFor(fields.option_type)}
              onChange={(option_type) => change({ option_type })}
            />
          </label>
        )}
        <label className="space-y-1 text-xs">
          {fields.expiry.label}
          <StudioSelect
            label="Expiry selection"
            value={value.expiry}
            options={choicesFor(fields.expiry)}
            onChange={(expiry) => changeField("expiry", expiry)}
          />
        </label>
        {value.expiry === values.ExpirySelection.FIXED && (
          <label className="space-y-1 text-xs">
            {fields.expiry_date.label}
            <DatePicker
              placeholder="Choose listed expiry"
              className=""
              date={
                value.expiry_date
                  ? new Date(`${value.expiry_date}T12:00:00`)
                  : undefined
              }
              setDate={(date) =>
                change({ expiry_date: date ? formatDateInput(date) : null })
              }
            />
          </label>
        )}
        {value.instrument_type === values.InstrumentType.OPTION && (
          <>
            <label className="space-y-1 text-xs">
              {fields.strike.label}
              <StudioSelect
                label="Strike selection"
                value={value.strike}
                options={choicesFor(fields.strike)}
                onChange={(strike) => changeField("strike", strike)}
              />
            </label>
            {automatic.relative_strikes.includes(value.strike) && (
              <label className="space-y-1 text-xs">
                {fields.distance.label}
                <Input
                  aria-label="Strike distance"
                  type="number"
                  min="1"
                  max={fields.distance.max}
                  step={fields.distance.step}
                  className=""
                  value={value.distance}
                  onChange={(event) =>
                    change({ distance: Number(event.target.value) })
                  }
                />
              </label>
            )}
            {value.strike === values.StrikeSelection.FIXED && (
              <label className="space-y-1 text-xs">
                {fields.strike_price.label}
                <Input
                  aria-label="Specific strike"
                  type="number"
                  min={fields.strike_price.min}
                  step={fields.strike_price.step}
                  className=""
                  value={value.strike_price ?? ""}
                  onChange={(event) =>
                    change({ strike_price: event.target.value })
                  }
                />
              </label>
            )}
          </>
        )}
      </div>
      <label className="flex items-center gap-2 text-xs">
        <Switch
          checked={value.allow_expiry_day}
          onCheckedChange={(allow_expiry_day) => change({ allow_expiry_day })}
        />
        Include contracts expiring today
      </label>
      <details className="studio-disclosure">
        <summary>How contract selection works</summary>
        <p className="mt-2 text-xs text-muted-foreground">
          {automatic.selection_help}
        </p>
        <p className="mt-2 text-xs text-muted-foreground">
          Use Lots for fixed sizing. Backtests require dated contract records
          and freeze the eligible catalog at the test start.
        </p>
      </details>
      <Button size="sm" variant="outline" disabled={busy} onClick={preview}>
        {busy ? "Resolving…" : "Preview selected contract"}
      </Button>
      {error && (
        <p role="alert" className="text-xs text-destructive">
          {error}
        </p>
      )}
      {result && (
        <div
          className="rounded-md border px-3 py-2 text-xs leading-relaxed"
          aria-live="polite"
        >
          <p className="font-medium">{result.instrument.name}</p>
          <p>
            Expiry {formatDate(result.instrument.expiry_date)} · Lot{" "}
            {formatNumber(result.instrument.lot_size, {
              maximumFractionDigits: 0,
            })}
          </p>
          <p className="text-muted-foreground">
            Underlying{" "}
            {result.underlying_quote.available
              ? formatCurrency(result.underlying_quote.price)
              : "unavailable"}
            {result.underlying_quote.timestamp &&
              ` · ${formatDateTime(result.underlying_quote.timestamp)}`}{" "}
            · {result.underlying_quote.source}
          </p>
          <p className="text-muted-foreground">
            Preview does not pin this contract or submit an order.
          </p>
        </div>
      )}
    </div>
  );
}
ContractSelectionEditor.propTypes = {
  underlyingId: PropTypes.number.isRequired,
  value: PropTypes.object.isRequired,
  onChange: PropTypes.func.isRequired,
};
