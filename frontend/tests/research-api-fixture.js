const rule = { operand_a_type: "CLOSE", operand_a_params: { shift: 0 }, comparison: "GT", operand_b_type: "CONSTANT", operand_b_params: { value: 100 }, is_active: true };
const choices = (values) => values.map((value) => ({ value, label: value }));
window.fixtureSchema = {
  service_configured: true, defaults: { timeframe: "1D" }, backtest_defaults: { name: "Research experiment", start_date: "2026-01-01", end_date: "2026-10-04", initial_capital: "100000", slippage_pct: "0.05", include_charges: false }, charge_profiles: [],
  enums: { CandleTimeframe: choices(["1D", "5m"]), LogicalOperator: choices(["AND", "OR"]), OperandType: choices(["CLOSE", "CONSTANT"]), ComparisonOperator: choices(["GT"]), OperandParameterConfig: { CLOSE: [{ key: "shift", type: "number", default: 0, label: "Shift" }], CONSTANT: [{ key: "value", type: "number", default: 0, label: "Value" }] }, OperandGroups: { Price: ["CLOSE", "CONSTANT"] } },
  presets: [{ id: "trend", name: "Trend setup", description: "A readable backend preset.", timeframe: "1D", logical_operator: "AND", conditions: [rule] }],
  strategies: [{ id: 7, name: "Crossover idea", timeframe: "5m" }],
};
const instrument = { id: 1, symbol: "RELIANCE", name: "Reliance", sym_ticker: "NSE:RELIANCE-EQ" };
const row = { instrument_id: 1, symbol: "RELIANCE", close: 100.25, volume: 1000, return_20_bars_pct: 2.5, volatility_20_bars_pct: 1.5, matched: true, observed_at: "2026-10-02T10:00:00Z", operand_values: [{ a: 100.25, b: 100, passed: true, comparison: "GT" }], chart: [] };
const evidence = { evidence_id: "E1", tool: "screen_instruments", source_run_id: 1, source_as_of: "2026-10-04T10:00:00Z", data: { as_of: "2026-10-04T10:00:00Z", timeframe: "1D", total: 1, evaluated: 1, matched: 1, excluded: [], rows: [row], conditions: { rules: [rule] } } };
const mode = new URLSearchParams(location.search).get("case");
const freshConversation = ["welcome", "message-race"].includes(mode);
const request = { instrument_ids: [1], instruments: [instrument], strategy_id: null, use_watchlist: false, timeframe: "1D", backtest_ids: [], backtests: [], screen: { timeframe: "1D", conditions: [rule], logical_operator: "AND" } };
window.fixtureRuns = freshConversation ? [] : [{ id: 1, session: 1, mode: mode === "screener" ? "SCREEN" : "RESEARCH", revision: 2, as_of: "2026-10-04T10:00:00Z", prompt: "Analyze my stocks", request,
  status: mode === "progress" ? "RUNNING" : "COMPLETED", progress_message: "Loading candles", evidence: mode === "progress" ? [] : [evidence],
  result: { answer: "## Market observations\n\nPrices met the condition [E1].", evidence_ids: ["E1"], artifact_refs: ["E1"], next_steps: ["Compare volatility"], limitations: [], clarification_questions: [] }, actions: [], error_message: "" }];
window.researchRequests = [];
window.fixtureSessions = [{ id: 1, title: "Momentum study", kind: mode === "screener" ? "SCREEN" : "CHAT", context: { ...request }, updated_at: "2026-10-04T10:00:00Z" }];
window.fixtureSockets = [];
window.WebSocket = class {
  constructor() { window.fixtureSockets.push(this); setTimeout(() => this.onopen?.(), 0); }
  close() {}
};
export const ensureFreshAccessToken = async () => "fixture";
export const getWebSocketUrl = () => "ws://fixture/research";
const page = (results) => ({ data: { results, count: results.length, next: null, previous: null } });
export default {
  get: async (url, options = {}) => {
    if (url === "/common/choices/") {
      const params = options.params;
      const rows = params.resource === "strategies" ? window.fixtureSchema.strategies :
        params.resource === "screens" ? [
          ...window.fixtureSessions.filter((item) => item.kind === "SCREEN"),
          ...Array.from({ length: 30 }, (_, index) => ({ id: index + 2, title: `Recent screen ${index + 2}` })),
        ] : [];
      const results = rows.map((item) => ({ ...item, value: String(item.id), label: item.name || item.title }))
        .filter((item) => (!params.id || String(item.id) === String(params.id)) &&
          (!params.search || item.label.toLowerCase().includes(params.search.toLowerCase())));
      results.sort((a, b) => b.id - a.id);
      const offset = ((params.page || 1) - 1) * 20;
      return { data: { results: results.slice(offset, offset + 20), has_more: results.length > offset + 20, page: params.page || 1 } };
    }
    if (url.includes("/schema/")) return { data: window.fixtureSchema };
    if (url === "/research/sessions/") return page(window.fixtureSessions.filter((item) => !options.params?.search || item.title.toLowerCase().includes(options.params.search.toLowerCase())));
    if (url.includes("/sessions/")) return { data: window.fixtureSessions[0] };
    if (url === "/research/runs/") return page(window.fixtureRuns.filter((item) => !options.params?.active || ["PENDING", "RUNNING"].includes(item.status)));
    if (url.startsWith("/research/runs/")) {
      if (mode === "message-race") await new Promise((resolve) => setTimeout(resolve, 500));
      const run = window.fixtureRuns.find((item) => url.includes(`/${item.id}/`));
      return { data: mode === "message-race" ? { ...run, revision: 2, status: "RUNNING", progress_message: "Loading candles" } : run };
    }
    if (url.includes("/strategies/")) return { data: [] };
    if (url.includes("/backtest/")) return page([10, 11, 12, 13].map((id) => ({ id, name: `Experiment ${id}`, status: "COMPLETED" })));
    return { data: [] };
  },
  post: async (url, payload) => {
    window.researchRequests.push({ url, payload });
    if (url === "/research/runs/") {
      const run = { ...window.fixtureRuns[0], id: 2, revision: 1, session: 1, prompt: payload.prompt, request: { ...request, ...payload, instruments: payload.strategy_id || payload.use_watchlist || payload.instrument_ids?.includes(1) ? [instrument] : [] }, status: "PENDING", progress_message: "Preparing research context", evidence: [], result: {}, actions: [], as_of: "2026-10-04T11:00:00Z" };
      window.fixtureRuns.push(run);
      if (mode === "message-race") {
        window.fixtureSockets[0].onmessage({ data: JSON.stringify({ type: "research.update", run: {
          id: run.id, session: run.session, revision: 2, status: "RUNNING", progress_message: "Loading candles",
        } }) });
        await new Promise((resolve) => setTimeout(resolve, 100));
      }
      return { data: run };
    }
    if (url.includes("/propose-action/")) return { data: { id: 1, run: 1, action_type: payload.action_type, payload: { instruments: [instrument], instrument_ids: [1] }, status: "PROPOSED", resource_ids: {} } };
    if (url.includes("/confirm/")) return { data: { id: 1, action_type: "ADD_TO_WATCHLIST", payload: {}, status: "COMPLETED", resource_ids: { watchlist_id: 1 }, error_message: "" } };
    if (url.includes("/cancel/")) { window.fixtureRuns[0] = { ...window.fixtureRuns[0], status: "CANCELLED", revision: 5 }; return { data: window.fixtureRuns[0] }; }
    return { data: {} };
  },
  patch: async (_, payload) => { window.fixtureSessions[0] = { ...window.fixtureSessions[0], ...payload }; return { data: window.fixtureSessions[0] }; },
  delete: async () => ({ data: {} }),
};
