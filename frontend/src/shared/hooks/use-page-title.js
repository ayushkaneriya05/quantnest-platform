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
  
  // Portfolio routes
  '/dashboard/portfolio/advanced-risk-hub': { title: 'Advanced Risk Hub', subtitle: 'Comprehensive risk management tools' },
  '/dashboard/portfolio/tax-center': { title: 'Tax Center', subtitle: 'Tax reporting and optimization' },
  '/dashboard/portfolio/trade-journal': { title: 'Trade Journal', subtitle: 'Track and analyze your trades' },
  
  // Strategy routes
  '/dashboard/strategy/backtesting-hub': { title: 'Backtesting Hub', subtitle: 'Test strategies against historical data' },
  '/dashboard/strategy/my-live-algos': { title: 'My Live Algos', subtitle: 'Manage your active trading algorithms' },
  '/dashboard/strategy/strategy-builder': { title: 'Strategy Builder', subtitle: 'Create and customize trading strategies' },
  '/dashboard/strategy/strategy-marketplace': { title: 'Strategy Marketplace', subtitle: 'Discover and share trading strategies' },
  
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
