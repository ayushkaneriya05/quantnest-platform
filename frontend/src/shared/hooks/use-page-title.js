import { useLocation } from 'react-router-dom'

// Route to title mapping
const routeTitles = {
  '/dashboard': { title: 'Dashboard', subtitle: 'Your trading overview and quick actions' },
  '/dashboard/search': { title: 'Search', subtitle: 'Find stocks, strategies, and market data' },
  '/dashboard/profile-settings': { title: 'Profile & Settings', subtitle: 'Manage your account, security, and personal information' },
  '/dashboard/notification-center': { title: 'Notification Center', subtitle: 'Manage alerts, preferences, and notification history' },
  
  // Analysis routes
  '/dashboard/analysis/ai-research-assistant': { title: 'AI Research Assistant', subtitle: 'Get AI-powered market insights and analysis' },
  '/dashboard/analysis/alternative-data-hub': { title: 'Alternative Data Hub', subtitle: 'Access unique market data sources' },
  '/dashboard/analysis/market-screener': { title: 'Market Screener', subtitle: 'Screen and filter stocks by your criteria' },
  
  // Community routes
  '/dashboard/community/leaderboards': { title: 'Leaderboards', subtitle: 'Top performers and community rankings' },
  '/dashboard/community/learning-center': { title: 'Learning Center', subtitle: 'Educational resources and tutorials' },
  '/dashboard/community/social-hub': { title: 'Social Hub', subtitle: 'Connect with other traders' },
  
  // Portfolio routes (Phase 2)
  '/dashboard/portfolio': { title: 'Portfolio Overview', subtitle: 'Capital summary and allocation breakdown' },
  '/dashboard/portfolio/allocations': { title: 'Portfolio Allocations', subtitle: 'Manage capital allocation across strategies' },
  '/dashboard/portfolio/exposure': { title: 'Portfolio Exposure', subtitle: 'View exposure by asset, sector, and strategy' },
  '/dashboard/portfolio/transactions': { title: 'Transactions', subtitle: 'Deposit, withdraw, and track fund movements' },
  '/dashboard/portfolio/risk': { title: 'Risk Settings', subtitle: 'Configure risk limits and breach actions' },
  '/dashboard/portfolio/advanced-risk-hub': { title: 'Advanced Risk Hub', subtitle: 'Comprehensive risk management tools' },
  '/dashboard/portfolio/tax-center': { title: 'Tax Center', subtitle: 'Tax reporting and optimization' },
  '/dashboard/portfolio/trade-journal': { title: 'Trade Journal', subtitle: 'Track and analyze your trades' },
  
  // Strategy routes (Phase 1)
  '/dashboard/strategy/list': { title: 'My Strategies', subtitle: 'Create and manage algorithmic trading strategies' },
  '/dashboard/strategy/create': { title: 'Create Strategy', subtitle: 'Build a new trading strategy step by step' },
  '/dashboard/strategy/backtesting-hub': { title: 'Backtesting Hub', subtitle: 'Test strategies against historical data' },
  '/dashboard/strategy/my-live-algos': { title: 'My Live Algos', subtitle: 'Manage your active trading algorithms' },
  '/dashboard/strategy/strategy-builder': { title: 'Strategy Builder', subtitle: 'Create and customize trading strategies' },
  '/dashboard/strategy/strategy-marketplace': { title: 'Strategy Marketplace', subtitle: 'Discover and share trading strategies' },
  
  // Backtesting routes (Phase 3)
  '/dashboard/backtest': { title: 'Backtesting Lab', subtitle: 'Launch, monitor, and analyze strategy simulations' },
  '/dashboard/backtest/setup': { title: 'New Backtest', subtitle: 'Configure and launch a historical strategy simulation' },
  '/dashboard/backtest/optimize': { title: 'Parameter Optimization', subtitle: 'Find optimal strategy parameters' },
  '/dashboard/backtest/montecarlo': { title: 'Monte Carlo Simulation', subtitle: 'Analyze strategy performance distributions' },
  
  // Paper Trading routes (Phase 4)
  '/dashboard/paper': { title: 'Paper Trading', subtitle: 'Practice trading with virtual money' },
  '/dashboard/paper/orders': { title: 'Order Book', subtitle: 'Place and manage paper trading orders' },
  '/dashboard/paper/positions': { title: 'Open Positions', subtitle: 'View and close paper trading positions' },
  '/dashboard/paper/trades': { title: 'Trade History', subtitle: 'Review completed paper trades' },
  '/dashboard/paper/accounts': { title: 'Paper Accounts', subtitle: 'Manage virtual trading accounts' },
  '/dashboard/paper/analytics': { title: 'Paper Analytics', subtitle: 'Performance metrics and drawdown tracking' },

  // Broker + Live Trading routes
  '/dashboard/brokers': { title: 'Broker Connections', subtitle: 'Connect, verify, and activate broker accounts' },
  '/dashboard/brokers/settings': { title: 'Broker Order Settings', subtitle: 'Configure execution preferences, slippage, retries, and AMO' },
  '/dashboard/brokers/logs': { title: 'Broker API Logs', subtitle: 'Inspect request traces, latency, and broker responses' },
  '/dashboard/live/strategies': { title: 'Live Strategies', subtitle: 'Monitor deployed strategies and broker sessions' },

  '/dashboard/live/logs': { title: 'Execution Logs', subtitle: 'Review order lifecycle events and broker acknowledgements' },
  '/dashboard/live/emergency': { title: 'Emergency Controls', subtitle: 'Pause, resume, or stop running live sessions safely' },

  // Journal, AI, Marketplace, Governance
  '/dashboard/journal': { title: 'Trade Journal', subtitle: 'Document trade context, execution quality, and lessons learned' },
  '/dashboard/journal/reports': { title: 'Performance Reports', subtitle: 'Daily strategy and portfolio reports across paper and live flow' },
  '/dashboard/ai/advisor': { title: 'AI Advisor', subtitle: 'Strategy recommendations, overfit warnings, and tuning ideas' },
  '/dashboard/ai/scores': { title: 'Strategy Health Scores', subtitle: 'Track performance, risk, consistency, and execution quality' },
  '/dashboard/ai/regime': { title: 'Market Regime Detector', subtitle: 'Instrument-level regime and directional confidence snapshots' },
  '/dashboard/marketplace': { title: 'Strategy Marketplace', subtitle: 'Discover and subscribe to listed strategies' },
  '/dashboard/marketplace/creator': { title: 'Creator Dashboard', subtitle: 'Review strategy earnings and listing performance' },
  '/dashboard/marketplace/subscriptions': { title: 'Subscriptions', subtitle: 'Manage active marketplace subscriptions' },
  '/dashboard/settings/audit': { title: 'Audit Logs', subtitle: 'Track critical entity changes and operational actions' },
  '/dashboard/settings/governance': { title: 'Strategy Approvals', subtitle: 'Run compliance checks and approve marketplace submissions' },
  '/dashboard/settings/compliance': { title: 'Compliance Center', subtitle: 'Review strategy compliance scores and check results' },
  '/dashboard/settings/system': { title: 'System Settings', subtitle: 'Configure audit policies, governance rules, and platform settings' },
  
  // Trading routes
  '/dashboard/trading/broker-connections': { title: 'Broker Connections', subtitle: 'Connect and manage your broker accounts' },
  '/dashboard/trading/paper-trading': { title: 'Paper Trading', subtitle: 'Practice trading with virtual money' },
  '/dashboard/trading/trade-terminal': { title: 'Trade Terminal', subtitle: 'Execute trades and monitor positions' },
}

export function usePageTitle() {
  const location = useLocation()
  const path = location.pathname

  // Handle dynamic backtest routes
  if (path.startsWith('/dashboard/backtest/results/')) {
    return { title: 'Backtest Results', subtitle: 'Detailed performance analytics and trade distribution' }
  }
  if (path.startsWith('/dashboard/backtest/trades/')) {
    return { title: 'Trade History', subtitle: 'Individual trade entries, exits, and P&L' }
  }
  if (path.startsWith('/dashboard/backtest/charts/')) {
    return { title: 'Advanced Charts', subtitle: 'Equity curve and drawdown visualization' }
  }
  if (path.startsWith('/dashboard/marketplace/')) {
    if (path === '/dashboard/marketplace/creator') {
      return { title: 'Creator Dashboard', subtitle: 'Review strategy earnings and listing performance' }
    }
    if (path === '/dashboard/marketplace/subscriptions') {
      return { title: 'Subscriptions', subtitle: 'Manage active marketplace subscriptions' }
    }
    const parts = path.split('/')
    if (parts.length === 4 && parts[3]) {
      return { title: 'Marketplace Listing', subtitle: 'Review pricing, performance, and verified user feedback' }
    }
  }
  
  // Get the title and subtitle for the current route from static mapping
  const pageInfo = routeTitles[path] || { 
    title: 'Dashboard', 
    subtitle: 'Your trading overview and quick actions' 
  }
  
  return pageInfo
}
