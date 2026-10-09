import { useLocation, matchPath } from "react-router-dom";

const pages = [
  ["/overview", "Overview", "Your trading overview and quick actions"],
  ["/settings/profile", "Profile & Settings", "Manage your account, security, and preferences"],
  ["/notifications", "Notification Center", "Manage alerts and notification history"],
  ["/research", "AI Research Assistant", "Research ideas, review evidence, and develop strategy rules"],
  ["/screener", "Market Screener", "Screen stocks using your conditions"],
  ["/strategies", "My Strategies", "Create and manage your trading strategies"],
  ["/strategies/create", "Create Strategy", "Build a new trading strategy"],
  ["/strategies/:id/edit", "Strategy Details", "Configure your strategy"],
  ["/strategies/:id/entry", "Entry Rules", "Define when your strategy enters a position"],
  ["/strategies/:id/exit", "Exit Rules", "Define when your strategy exits a position"],
  ["/strategies/:id/time", "Trading Schedule", "Configure trading hours and restrictions"],
  ["/strategies/:id/assets", "Strategy Instruments", "Configure instruments and selection rules"],
  ["/strategies/:id/risk", "Position & Risk Settings", "Configure sizing and position limits"],
  ["/strategies/:id/auto-disable", "Auto-disable Rules", "Configure conditions for stopping your strategy"],
  ["/strategies/:id/versions", "Strategy Versions", "Review saved configurations and changes"],
  ["/strategies/:id/permissions", "Strategy Sharing", "Manage your strategy's share link"],
  ["/backtests", "Backtesting Lab", "Launch, monitor, and analyze historical simulations"],
  ["/backtests/setup", "New Backtest", "Configure a historical strategy simulation"],
  ["/backtests/results/:id", "Backtest Results", "Review performance and trade distribution"],
  ["/backtests/trades/:id", "Backtest Trades", "Review entries, exits, and P&L"],
  ["/backtests/charts/:id", "Backtest Charts", "Explore equity and drawdown"],
  ["/backtests/montecarlo", "Monte Carlo Simulation", "Analyze strategy performance distributions"],
  ["/terminal", "Trading Terminal", "Manual simulated execution"],
  ["/paper", "Paper Trading", "Manage automated paper deployments"],
  ["/paper/portfolio", "Paper Portfolio", "Review paper positions, orders, and trades"],
  ["/paper/capital", "Paper Capital", "Manage capital and strategy allocations"],
  ["/paper/analytics", "Paper Analytics", "Review simulated performance"],
  ["/brokers", "Broker Connections", "Connect and manage broker accounts"],
  ["/brokers/charge-profiles", "Broker Charge Profiles", "Configure execution costs"],
  ["/brokers/logs", "Broker API Logs", "Review broker requests and responses"],
  ["/live/portfolio", "Live Portfolio", "Review live positions, orders, and trades"],
  ["/live/strategies", "Live Strategies", "Manage live deployments"],
  ["/live/logs", "Execution Logs", "Review order events and broker acknowledgements"],
  ["/journal", "Trade Journal", "Review execution and record lessons learned"],
  ["/reports", "Performance Reports", "Review Terminal, Paper, and Live separately"],
  ["/activity", "Activity History", "Review configuration and operational changes"],
];

export function usePageTitle() {
  const { pathname } = useLocation();
  const [, title = "QuantNest", subtitle = ""] = pages.find(([path]) => matchPath({ path, end: true }, pathname)) || [];
  return { title, subtitle };
}
