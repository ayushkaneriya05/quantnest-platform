import PropTypes from "prop-types";
import { useState } from "react";
import { ChevronDown, Layers, Trash2 } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Switch } from "@/shared/components/ui/switch";
import { customConfirm } from "@/shared/components/ui/custom-dialog";
import { useStrategySpecification } from "@/shared/context/EnumsContext";
import InstrumentSearch from "@/features/terminal/components/InstrumentSearch";
import ContractSelectionEditor from "./ContractSelectionEditor";
import { NumberExpression, StudioSelect } from "./ExpressionEditor";
import { policyText, sizingText } from "../studioPresentation";
import { formatDate, formatNumber } from "@/shared/utils/formatters";

function SizingFields({ value, onChange, label = "", lotsOnly = false }) {
  const { enums, spec, choicesFor } = useStrategySpecification();
  const update = (name, next) => onChange({ ...value, [name]: next });
  return (
    <div className="studio-field-grid">
      <label className="studio-field sm:col-span-2">
        <span>Sizing method</span>
        <StudioSelect
          label={`${label}Sizing method`}
          value={value.sizing_method}
          options={choicesFor(spec.sizing.fields.sizing_method)}
          onChange={(next) => update("sizing_method", next)}
        />
      </label>
      {value.sizing_method === "FIXED" ? (
        <>
          <label className="studio-field">
            <span>Measured in</span>
            <StudioSelect
              label={`${label}Quantity unit`}
              value={value.quantity_unit || spec.sizing.fields.quantity_unit.default}
              options={(enums.QuantityUnit || []).filter(
                (item) => !lotsOnly || item.value === spec.markets.automatic.fixed_sizing_unit,
              )}
              onChange={(next) => update("quantity_unit", next)}
            />
          </label>
          <label className="studio-field">
            <span>Fixed quantity</span>
            <Input
              aria-label={`${label}Fixed quantity`}
              type="number"
              min={spec.sizing.fields.fixed_quantity.min}
              step={spec.sizing.fields.fixed_quantity.step}
              value={value.fixed_quantity ?? ""}
              onChange={(event) =>
                update(
                  "fixed_quantity",
                  event.target.value === "" ? null : Number(event.target.value),
                )
              }
            />
          </label>
        </>
      ) : (
        <label className="studio-field sm:col-span-2">
          <span>Available capital (%)</span>
          <Input
            aria-label={`${label}Capital percentage`}
            type="number"
            min={spec.sizing.fields.capital_percentage.min}
            max={spec.sizing.fields.capital_percentage.max}
            step={spec.sizing.fields.capital_percentage.step}
            value={value.capital_percentage ?? ""}
            onChange={(event) =>
              update(
                "capital_percentage",
                event.target.value === "" ? null : Number(event.target.value),
              )
            }
          />
        </label>
      )}
    </div>
  );
}
SizingFields.propTypes = {
  value: PropTypes.object.isRequired,
  onChange: PropTypes.func.isRequired,
  label: PropTypes.string,
  lotsOnly: PropTypes.bool,
};

export default function StudioMarkets({
  document,
  onChange,
  operators,
  instruments = [],
}) {
  const { enums, spec, defaultContractSelection, initialRiskNode } = useStrategySpecification();
  const [expanded, setExpanded] = useState({});
  const [filter, setFilter] = useState("");
  const [addedInstruments, setAddedInstruments] = useState({});
  const metadata = {
    ...Object.fromEntries(instruments.map((item) => [item.id, item])),
    ...addedInstruments,
  };
  const sizing = document.position_sizing_rule;
  const watches = document.watchlist_instruments;
  const updateWatch = (watch, changes) =>
    onChange({
      ...document,
      watchlist_instruments: watches.map((item) =>
        item === watch ? { ...item, ...changes } : item,
      ),
    });
  const disabledReason = (instrument, mode) => {
    if (mode === "automatic")
      return !spec.markets.automatic.underlying_types.includes(instrument.instrument_type) ||
        !spec.markets.automatic.exchanges.includes(instrument.exchange)
        ? "Choose an NSE/BSE underlying"
        : "";
    if (instrument.analysis_only) return "Signal use only";
    return watches.some(
      (item) =>
        !item.contract_selection &&
        item.instrument_symbol === instrument.sym_ticker,
    )
      ? "Already selected"
      : "";
  };
  const add = (instrument, mode) => {
    setAddedInstruments((current) => ({
      ...current,
      [instrument.id]: instrument,
    }));
    const automatic = mode === "automatic";
    const watch = {
      instrument_id: instrument.id,
      instrument_symbol: instrument.sym_ticker,
      instrument_name: instrument.name,
      source_id: `instrument-${instrument.id}`,
      route_id: automatic
        ? `auto-${crypto.randomUUID()}`
        : `direct-${instrument.id}`,
      leg_id: "primary",
      ...(automatic
        ? {
            signal_instrument_id: instrument.id,
            signal_instrument_name: instrument.name,
            contract_selection: defaultContractSelection(),
            execution_routes: [
              {
                ...sizing,
                ...structuredClone(spec.markets.automatic.sizing_override),
              },
            ],
          }
        : {}),
    };
    onChange({ ...document, watchlist_instruments: [...watches, watch] });
    setFilter("");
    setExpanded((current) => ({ ...current, [watch.route_id]: true }));
  };
  const visible = watches.filter((watch) =>
    `${watch.instrument_name} ${watch.instrument_symbol} ${watch.signal_instrument_name || ""}`
      .toLowerCase()
      .includes(filter.toLowerCase()),
  );
  return (
    <div className="studio-markets-grid">
      <section className="studio-surface min-w-0" data-studio-markets>
        <div className="studio-section-heading">
          <h2>
            Selected instruments{" "}
            <span className="studio-count">{watches.length}</span>
          </h2>
          <InstrumentSearch
            label="Add instrument"
            triggerClassName="shrink-0"
            allowHistorical
            modes={[
              { value: "fixed", label: "Fixed instrument / contract" },
              { value: "automatic", label: "Automatic F&O selection" },
            ]}
            getDisabledReason={disabledReason}
            onAddToWatchlist={add}
          />
        </div>
        {watches.length > 5 && (
          <div className="px-3 pb-3">
            <Input
              aria-label="Filter selected instruments"
              placeholder="Filter selected instruments…"
              value={filter}
              onChange={(event) => setFilter(event.target.value)}
            />
            <p className="studio-hint mt-1">
              {visible.length} of {watches.length} selected
            </p>
          </div>
        )}
        {!watches.length && (
          <div className="studio-empty">
            <Layers className="h-5 w-5 text-muted-foreground" />
            <p>Add a stock, fixed contract or automatic contract policy.</p>
          </div>
        )}
        {watches.length > 0 && !visible.length && (
          <p className="p-3 text-sm text-muted-foreground">
            No selected instruments match this filter.
          </p>
        )}
        <div className="divide-y divide-border">
          {visible.map((watch) => {
            const name = watch.instrument_name || watch.instrument_symbol;
            const custom = watch.execution_routes?.[0]?.override_sizing;
            const effective = custom ? watch.execution_routes[0] : sizing;
            const instrument = metadata[watch.instrument_id];
            const instrumentType = enums.InstrumentType?.find(
              (choice) => choice.value === instrument?.instrument_type,
            )?.label;
            const open = Boolean(expanded[watch.route_id]);
            return (
              <article
                key={`${watch.route_id}:${watch.leg_id}`}
                className="studio-route"
              >
                <div className="flex min-w-0 items-start gap-2">
                  <Button variant="plain" size="content"
                    type="button"
                    className="block h-auto justify-start whitespace-normal p-0 min-w-0 flex-1 text-left"
                    aria-expanded={open}
                    aria-label={`Edit settings for ${name}`}
                    onClick={() =>
                      setExpanded((current) => ({
                        ...current,
                        [watch.route_id]: !open,
                      }))
                    }
                  >
                    <span className="flex items-center gap-2">
                      <strong className="min-w-0 break-words text-sm">
                        {name}
                      </strong>
                      <ChevronDown
                        className={`h-4 w-4 shrink-0 text-muted-foreground transition-transform ${open ? "rotate-180" : ""}`}
                      />
                    </span>
                    <span className="mt-1 block text-xs text-muted-foreground">
                      {watch.contract_selection
                        ? `Automatic · ${policyText(watch.contract_selection, enums)}`
                        : [
                            "Fixed",
                            instrument?.exchange,
                            instrumentType,
                            instrument?.expiry_date &&
                              formatDate(instrument.expiry_date),
                            instrument?.is_active === false &&
                              "Archived · backtest only",
                          ]
                            .filter(Boolean)
                            .join(" · ")}
                    </span>
                    <span className="mt-1 block text-xs">
                      Signal: {watch.signal_instrument_name || name}{" "}
                      <span className="text-muted-foreground">
                        → Trade:{" "}
                        {watch.contract_selection ? "selected contract" : name}
                      </span>
                    </span>
                    <span className="mt-1 block text-xs text-muted-foreground">
                      Size: {sizingText(effective, enums)} ·{" "}
                      {custom ? "Custom" : "Strategy default"}
                      {!watch.contract_selection &&
                        instrument?.lot_size > 1 &&
                        ` · Lot ${formatNumber(instrument.lot_size, { maximumFractionDigits: 0 })}${effective.sizing_method === "FIXED" && effective.quantity_unit === "LOTS" ? ` · ${formatNumber(effective.fixed_quantity * instrument.lot_size, { maximumFractionDigits: 0 })} units` : ""}`}
                    </span>
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label={`Remove ${name}`}
                    onClick={async () => {
                      if (
                        await customConfirm(
                          `Remove ${name} from this draft? Running deployments are managed separately.`,
                          "Remove instrument",
                          "Remove",
                        )
                      )
                        onChange({
                          ...document,
                          watchlist_instruments: watches.filter(
                            (item) => item !== watch,
                          ),
                        });
                    }}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
                {!watch.contract_selection &&
                  instrument?.lot_size > 1 &&
                  effective.sizing_method === "FIXED" &&
                  effective.quantity_unit === "UNITS" &&
                  Number(effective.fixed_quantity) % instrument.lot_size !==
                    0 && (
                    <p className="mt-2 text-xs text-destructive" role="status">
                      Fixed quantity{" "}
                      {formatNumber(effective.fixed_quantity, {
                        maximumFractionDigits: 0,
                      })}{" "}
                      does not form a whole lot. This contract needs multiples
                      of{" "}
                      {formatNumber(instrument.lot_size, {
                        maximumFractionDigits: 0,
                      })}{" "}
                      units. Choose Lots or set a valid custom quantity;
                      execution rejects invalid quantities.
                    </p>
                  )}
                {open && (
                  <div className="mt-3 space-y-3 border-t border-border pt-3">
                    {watch.contract_selection ? (
                      <ContractSelectionEditor
                        underlyingId={watch.instrument_id}
                        value={watch.contract_selection}
                        onChange={(contract_selection) =>
                          updateWatch(watch, { contract_selection })
                        }
                      />
                    ) : (
                      <div className="flex flex-wrap items-center gap-2">
                        <InstrumentSearch
                          label="Change signal instrument"
                          triggerClassName=""
                          allowHistorical
                          onAddToWatchlist={(instrument) =>
                            updateWatch(watch, {
                              signal_instrument_id: instrument.id,
                              signal_instrument_name: instrument.name,
                            })
                          }
                        />
                        {watch.signal_instrument_id &&
                          watch.signal_instrument_id !==
                            watch.instrument_id && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() =>
                                updateWatch(watch, {
                                  signal_instrument_id: watch.instrument_id,
                                  signal_instrument_name: watch.instrument_name,
                                })
                              }
                            >
                              Use traded contract for signals
                            </Button>
                          )}
                      </div>
                    )}
                    <div className="space-y-3">
                      <label className="flex items-center gap-2 text-sm">
                        <Switch
                          aria-label={`Custom sizing for ${name}`}
                          checked={Boolean(custom)}
                          disabled={
                            Boolean(watch.contract_selection) &&
                            sizing.sizing_method === "FIXED" &&
                            sizing.quantity_unit !== "LOTS"
                          }
                          onCheckedChange={(enabled) =>
                            updateWatch(watch, {
                              execution_routes: enabled
                                ? [
                                    {
                                      ...sizing,
                                      ...(watch.contract_selection
                                        ? { quantity_unit: spec.markets.automatic.fixed_sizing_unit }
                                        : {}),
                                      override_sizing: true,
                                    },
                                  ]
                                : [],
                            })
                          }
                        />
                        Use custom size
                      </label>
                      {custom && (
                        <SizingFields
                          value={effective}
                          label={`${name} `}
                          lotsOnly={Boolean(watch.contract_selection)}
                          onChange={(value) =>
                            updateWatch(watch, { execution_routes: [value] })
                          }
                        />
                      )}
                      {Boolean(watch.contract_selection) &&
                        sizing.sizing_method === "FIXED" &&
                        sizing.quantity_unit !== "LOTS" && (
                          <p className="studio-hint">
                            This policy needs a Lots override. Change the
                            strategy default to Lots to inherit it.
                          </p>
                        )}
                    </div>
                  </div>
                )}
              </article>
            );
          })}
        </div>
      </section>
      <section className="studio-surface h-fit" data-studio-sizing>
        <div className="studio-section-heading">
          <h2>Direction & default size</h2>
        </div>
        <div className="space-y-3 p-3 sm:p-3">
          <label className="studio-field">
            <span>Entry direction</span>
            <StudioSelect
              label="Entry direction"
              value={document.entry_order_config.entry_side}
              options={enums.Side || []}
              onChange={(entry_side) =>
                onChange({
                  ...document,
                  entry_order_config: {
                    ...document.entry_order_config,
                    entry_side,
                  },
                })
              }
            />
          </label>
          <SizingFields
            value={sizing}
            onChange={(position_sizing_rule) =>
              onChange({ ...document, position_sizing_rule })
            }
          />
          <p className="studio-hint">
            Units are the exact order quantity; Lots multiply by the contract’s
            lot size. A 30-unit lot accepts 30 or 60 units, not 1. Use a custom
            size when instruments need different quantities. Automatic fixed
            sizing requires Lots.
          </p>
          {sizing.sizing_method !== "FIXED" && (
            <p className="studio-hint">
              Long options use premium; futures and short options use estimated
              collateral. The broker determines actual Live margin.
            </p>
          )}
          <details className="studio-disclosure" data-studio-risk>
            <summary>
              Reward/risk basis
              {document.initial_risk ? " · Configured" : " · Optional"}
            </summary>
            <div className="mt-3 space-y-3">
              <label className="flex items-center gap-2 text-sm">
                <Switch
                  aria-label="Define initial risk distance"
                  checked={document.initial_risk != null}
                  onCheckedChange={async (enabled) => {
                    if (
                      enabled ||
                      (await customConfirm(
                        "Remove the initial risk definition? R-multiple rules require a valid initial risk distance.",
                        "Remove risk basis",
                        "Remove",
                      ))
                    )
                      onChange({
                        ...document,
                        initial_risk: enabled ? initialRiskNode() : null,
                      });
                  }}
                />
                Define initial risk distance
              </label>
              <p className="studio-hint">
                Traded-contract price points frozen at entry as 1R. This does
                not place a protective stop.
              </p>
              {document.initial_risk != null && (
                <NumberExpression
                  node={document.initial_risk}
                  operators={{
                    ...operators,
                    captures: [],
                    source_roles: spec.markets.source_roles.filter((item) => item.value === "trade"),
                    default_source: "trade",
                    default_timeframe: document.time_rule.candle_timeframe,
                    expressions: Object.keys(document.expressions || {}),
                  }}
                  ruleType="ENTRY"
                  onChange={(initial_risk) =>
                    onChange({ ...document, initial_risk })
                  }
                />
              )}
            </div>
          </details>
          <p className="studio-hint border-t border-border pt-3">
            Each traded contract owns its position independently. Exit
            conditions close the full owned position.
          </p>
        </div>
      </section>
    </div>
  );
}
StudioMarkets.propTypes = {
  document: PropTypes.object.isRequired,
  onChange: PropTypes.func.isRequired,
  operators: PropTypes.object.isRequired,
  instruments: PropTypes.array,
};
