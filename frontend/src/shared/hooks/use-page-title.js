import { useLocation } from "react-router-dom";

// Route to title mapping
const routeTitles = {
  "/dashboard": {
    title: "Dashboard",
    subtitle: "Your trading overview and quick actions",
  },
  "/dashboard/search": {
    title: "Search",
    subtitle: "Find stocks, strategies, and market data",
  },
  "/dashboard/profile-settings": {
    title: "Profile & Settings",
    subtitle: "Manage your account, security, and personal information",
  },
  "/dashboard/notification-center": {
    title: "Notification Center",
    subtitle: "Manage alerts, preferences, and notification history",
  },

  // Analysis routes
  "/dashboard/analysis/ai-research-assistant": {
    title: "AI Research Assistant",
    subtitle: "Research hypotheses, review evidence, and build testable strategy drafts",
  },
  "/dashboard/analysis/market-screener": {
    title: "Market Screener",
    subtitle: "Screen and filter stocks by your criteria",
  },

  // Community routes
  "/dashboard/strategy/list": {
    title: "My Strategies",
    subtitle: "Create and manage algorithmic trading strategies",
  },
  "/dashboard/strategy/create": {
    title: "Create Strategy",
    subtitle: "Build a new trading strategy step by step",
  },
  "/dashboard/strategy/backtesting-hub": {
    title: "Backtesting Hub",
    subtitle: "Test strategies against historical data",
  },
  "/dashboard/strategy/my-live-algos": {
    title: "My Live Algos",
    subtitle: "Manage your active trading algorithms",
  },
  "/dashboard/strategy/strategy-builder": {
    title: "Strategy Builder",
    subtitle: "Create and customize trading strategies",
  },

  // Backtesting routes
  "/dashboard/backtest": {
    title: "Backtesting Lab",
    subtitle: "Launch, monitor, and analyze strategy simulations",
  },
  "/dashboard/backtest/setup": {
    title: "New Backtest",
    subtitle: "Configure and launch a historical strategy simulation",
  },
  "/dashboard/backtest/optimize": {
    title: "Parameter Optimization",
    subtitle: "Find optimal strategy parameters",
  },
  "/dashboard/backtest/montecarlo": {
    title: "Monte Carlo Simulation",
    subtitle: "Analyze strategy performance distributions",
  },

  // Paper Trading routes
  "/dashboard/paper": {
    title: "Paper Trading",
    subtitle: "Practice trading with virtual money",
  },
  "/dashboard/paper/orders": {
    title: "Order Book",
    subtitle: "Place and manage paper trading orders",
  },
  "/dashboard/paper/positions": {
    title: "Open Positions",
    subtitle: "View and close paper trading positions",
  },
  "/dashboard/paper/trades": {
    title: "Trade History",
    subtitle: "Review completed paper trades",
  },
  "/dashboard/paper/accounts": {
    title: "Paper Accounts",
    subtitle: "Manage virtual trading accounts",
  },
  "/dashboard/paper/analytics": {
    title: "Paper Analytics",
    subtitle: "Performance metrics and drawdown tracking",
  },

  // Broker + Live Trading routes
  "/dashboard/brokers": {
    title: "Broker Connections",
    subtitle: "Connect, verify, and activate broker accounts",
  },
  "/dashboard/brokers/charge-profiles": {
    title: "Broker Charge Profiles",
    subtitle: "Manage execution cost modeling for backtests and live PnL",
  },
  "/dashboard/brokers/settings": {
    title: "Broker Order Settings",
    subtitle: "Configure execution preferences, slippage, retries, and AMO",
  },
  "/dashboard/brokers/logs": {
    title: "Broker API Logs",
    subtitle: "Inspect request traces, latency, and broker responses",
  },
  "/dashboard/live/strategies": {
    title: "Live Strategies",
    subtitle: "Monitor deployed strategies and broker sessions",
  },

  "/dashboard/live/logs": {
    title: "Execution Logs",
    subtitle: "Review order lifecycle events and broker acknowledgements",
  },
  // Journal, AI, Marketplace, Governance
  "/dashboard/journal": {
    title: "Trade Journal",
    subtitle: "Document trade context, execution quality, and lessons learned",
  },
  "/dashboard/journal/reports": {
    title: "Performance Reports",
    subtitle: "Review Terminal, Paper, and Live execution separately",
  },
  "/dashboard/settings/audit": {
    title: "Activity History",
    subtitle: "Track critical entity changes and operational actions",
  },

  // Manual Trading routes
  "/dashboard/trading/trade-terminal": {
    title: "Trade Terminal",
    subtitle: "Execute trades and monitor positions",
  },
};

export function usePageTitle() {
  const location = useLocation();
  const path = location.pathname;

  // Handle dynamic backtest routes
  if (path.startsWith("/dashboard/backtest/results/")) {
    return {
      title: "Backtest Results",
      subtitle: "Detailed performance analytics and trade distribution",
    };
  }
  if (path.startsWith("/dashboard/backtest/trades/")) {
    return {
      title: "Trade History",
      subtitle: "Individual trade entries, exits, and P&L",
    };
  }
  if (path.startsWith("/dashboard/backtest/charts/")) {
    return {
      title: "Advanced Charts",
      subtitle: "Equity curve and drawdown visualization",
    };
  }

  // Get the title and subtitle for the current route from static mapping
  const pageInfo = routeTitles[path] || {
    title: "Dashboard",
    subtitle: "Your trading overview and quick actions",
  };

  return pageInfo;
}
