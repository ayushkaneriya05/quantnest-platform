export const brand = {
  site: import.meta.env.VITE_SITE_URL || "https://quantnest.site",
  turnstile: import.meta.env.VITE_TURNSTILE_SITE_KEY || "",
};
export const faq = [
  ["Does QuantNest give me trading strategies or investment advice?", "You choose your trading rules. QuantNest provides tools to define, test, simulate and review them. It does not provide a profitable-strategy catalogue, trading signals or discretionary account management."],
  ["Can I start without paying?", "Explore is free and includes small allowances for the supported public workflow. You can build rules, test ideas, research and practise within the limits of your plan. Some data-dependent and AI features may have restricted availability; check your workspace before upgrading for a specific task."],
  ["Does a public plan include Live trading?", "No. Public subscriptions support simulation through Paper. Customer Live trading and QuantNest Private are not currently offered."],
  ["Do unused credits roll over?", "No. Explore resets by calendar month in Asia/Kolkata. Paid allowances reset at the verified billing-period boundary. There are no automatic paid overages."],
  ["What happens if I cancel or don't renew?", "Cancellation disables future renewal while preserving the current paid period. Existing work remains available. New over-limit activity is restricted. Paper requires explicit resumption within your current limits; reductions and protective controls remain available."],
  ["Are backtests and Paper results actual broker results?", "No. Historical candles and observed-price simulation cannot reproduce exchange queues, all partial fills, market impact or broker latency. Costs, slippage, coverage and assumptions should be reviewed."],
  ["What is the refund policy?", "The first paid Workspace purchase has a seven-day refund window, alongside applicable remedies. Custom Development has separately agreed terms. Submit a request from Billing and Usage."],
  ["Which markets can I work with?", "Explore, Build and Pro currently support NSE stocks. NSE futures and options are coming soon in Build and Pro, with no announced release date; they are not available for use today. Pro adds greater usage capacity. Public plans cover simulation; customer Live trading is not currently available."],
  ["Can you build a tool to my specifications?", "Yes. Request an application, dashboard, automation, data tool or integration. Custom Development is separate from the QuantNest product; no subscription is required. Specifications, acceptance criteria, ownership, costs and maintenance are agreed before development."],
];
