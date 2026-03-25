import { useLocation } from 'react-router-dom'

// Route to title mapping
const routeTitles = {
  '/dashboard': { title: 'Dashboard', subtitle: 'Your trading overview and quick actions' },
  '/dashboard/search': { title: 'Search', subtitle: 'Find stocks, strategies, and market data' },
  '/dashboard/profile-settings': { title: 'Profile & Settings', subtitle: 'Manage your account, security, and personal information' },
  
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
  '/dashboard/backtest/setup': { title: 'Backtest Setup', subtitle: 'Configure and run a historical strategy backtest' },
  '/dashboard/backtest/optimize': { title: 'Parameter Optimization', subtitle: 'Find optimal strategy parameters' },
  '/dashboard/backtest/montecarlo': { title: 'Monte Carlo Simulation', subtitle: 'Analyze strategy performance distributions' },
  
  // Paper Trading routes (Phase 4)
  '/dashboard/paper': { title: 'Paper Trading', subtitle: 'Practice trading with virtual money' },
  '/dashboard/paper/orders': { title: 'Order Book', subtitle: 'Place and manage paper trading orders' },
  '/dashboard/paper/positions': { title: 'Open Positions', subtitle: 'View and close paper trading positions' },
  '/dashboard/paper/trades': { title: 'Trade History', subtitle: 'Review completed paper trades' },
  '/dashboard/paper/accounts': { title: 'Paper Accounts', subtitle: 'Manage virtual trading accounts' },
  
  // Trading routes
  '/dashboard/trading/broker-connections': { title: 'Broker Connections', subtitle: 'Connect and manage your broker accounts' },
  '/dashboard/trading/paper-trading': { title: 'Paper Trading', subtitle: 'Practice trading with virtual money' },
  '/dashboard/trading/trade-terminal': { title: 'Trade Terminal', subtitle: 'Execute trades and monitor positions' },
}

export function usePageTitle() {
  const location = useLocation()
  
  // Get the title and subtitle for the current route
  const pageInfo = routeTitles[location.pathname] || { 
    title: 'Dashboard', 
    subtitle: 'Your trading overview and quick actions' 
  }
  
  return pageInfo
}
