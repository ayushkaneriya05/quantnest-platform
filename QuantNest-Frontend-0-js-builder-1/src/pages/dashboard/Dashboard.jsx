import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { TrendingUp, BarChart3, Target, Zap, ArrowRight } from 'lucide-react'

export default function Dashboard() {
  return (
    <div className="container-padding py-6 lg:py-8 space-y-6 lg:space-y-8">
      {/* Welcome Section */}
      <div className="mb-6 sm:mb-8">
        <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-slate-100 mb-2">Welcome to QuantNest</h1>
        <p className="text-slate-400 text-base sm:text-lg">Your professional algorithmic trading platform</p>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
        <Card className="bg-gray-900/50 border-gray-800/50 shadow-card hover:shadow-card-hover transition-all duration-200 hover-scale">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-300">Portfolio Value</CardTitle>
            <TrendingUp className="h-4 w-4 text-emerald-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-slate-100">$125,420</div>
            <p className="text-xs text-emerald-400">+2.5% from last month</p>
          </CardContent>
        </Card>

        <Card className="bg-gray-900/50 border-gray-800/50 shadow-card hover:shadow-card-hover transition-all duration-200 hover-scale">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-300">Active Strategies</CardTitle>
            <BarChart3 className="h-4 w-4 text-indigo-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-slate-100">12</div>
            <p className="text-xs text-slate-400">3 live, 9 paper trading</p>
          </CardContent>
        </Card>

        <Card className="bg-gray-900/50 border-gray-800/50 shadow-card hover:shadow-card-hover transition-all duration-200 hover-scale">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-300">Win Rate</CardTitle>
            <Target className="h-4 w-4 text-purple-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-slate-100">68.5%</div>
            <p className="text-xs text-purple-400">+1.2% this week</p>
          </CardContent>
        </Card>

        <Card className="bg-gray-900/50 border-gray-800/50 shadow-card hover:shadow-card-hover transition-all duration-200 hover-scale">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-300">Daily P&L</CardTitle>
            <Zap className="h-4 w-4 text-cyan-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-slate-100">+$1,247</div>
            <p className="text-xs text-cyan-400">+0.99% today</p>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
        <Card className="bg-gradient-to-br from-indigo-500/10 to-purple-600/10 border-indigo-500/30">
          <CardHeader>
            <CardTitle className="text-slate-100">Strategy Builder</CardTitle>
            <CardDescription className="text-slate-300">
              Create and backtest new trading strategies with our AI-powered builder.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button className="w-full bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700">
              Build Strategy
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-emerald-500/10 to-teal-600/10 border-emerald-500/30">
          <CardHeader>
            <CardTitle className="text-slate-100">Paper Trading</CardTitle>
            <CardDescription className="text-slate-300">
              Practice your strategies risk-free with real-time market data.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button className="w-full bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700">
              Start Trading
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-orange-500/10 to-red-600/10 border-orange-500/30">
          <CardHeader>
            <CardTitle className="text-slate-100">AI Research</CardTitle>
            <CardDescription className="text-slate-300">
              Get personalized market insights and stock recommendations.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button className="w-full bg-gradient-to-r from-orange-500 to-red-600 hover:from-orange-600 hover:to-red-700">
              Ask AI
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Market Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
        <Card className="bg-gray-900/50 border-gray-800/50 shadow-card hover:shadow-card-hover transition-all duration-200">
          <CardHeader>
            <CardTitle className="text-slate-100 flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-emerald-400" />
              Market Overview
            </CardTitle>
            <CardDescription className="text-slate-400">
              Current market indices and trending stocks
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex justify-between items-center p-3 rounded-lg bg-gray-800/30 hover:bg-gray-800/50 transition-all">
                <div>
                  <p className="text-slate-300 font-medium">S&P 500</p>
                  <p className="text-xs text-slate-400">SPX</p>
                </div>
                <div className="text-right">
                  <p className="text-slate-300">4,156.83</p>
                  <p className="text-xs text-emerald-400">+1.24%</p>
                </div>
              </div>
              <div className="flex justify-between items-center p-3 rounded-lg bg-gray-800/30 hover:bg-gray-800/50 transition-all">
                <div>
                  <p className="text-slate-300 font-medium">NASDAQ</p>
                  <p className="text-xs text-slate-400">IXIC</p>
                </div>
                <div className="text-right">
                  <p className="text-slate-300">12,900.88</p>
                  <p className="text-xs text-emerald-400">+0.89%</p>
                </div>
              </div>
              <div className="flex justify-between items-center p-3 rounded-lg bg-gray-800/30 hover:bg-gray-800/50 transition-all">
                <div>
                  <p className="text-slate-300 font-medium">DOW JONES</p>
                  <p className="text-xs text-slate-400">DJI</p>
                </div>
                <div className="text-right">
                  <p className="text-slate-300">33,274.15</p>
                  <p className="text-xs text-red-400">-0.56%</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gray-900/50 border-gray-800/50 shadow-card hover:shadow-card-hover transition-all duration-200">
          <CardHeader>
            <CardTitle className="text-slate-100 flex items-center gap-2">
              <Target className="h-5 w-5 text-indigo-400" />
              Top Performers
            </CardTitle>
            <CardDescription className="text-slate-400">
              Best performing stocks in your watchlist
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex justify-between items-center p-3 rounded-lg bg-gray-800/30 hover:bg-gray-800/50 transition-all">
                <div>
                  <p className="text-slate-300 font-medium">NVDA</p>
                  <p className="text-xs text-slate-400">NVIDIA Corp</p>
                </div>
                <div className="text-right">
                  <p className="text-slate-300">$118.22</p>
                  <p className="text-xs text-emerald-400">+5.67%</p>
                </div>
              </div>
              <div className="flex justify-between items-center p-3 rounded-lg bg-gray-800/30 hover:bg-gray-800/50 transition-all">
                <div>
                  <p className="text-slate-300 font-medium">TSLA</p>
                  <p className="text-xs text-slate-400">Tesla Inc</p>
                </div>
                <div className="text-right">
                  <p className="text-slate-300">$185.42</p>
                  <p className="text-xs text-emerald-400">+3.21%</p>
                </div>
              </div>
              <div className="flex justify-between items-center p-3 rounded-lg bg-gray-800/30 hover:bg-gray-800/50 transition-all">
                <div>
                  <p className="text-slate-300 font-medium">AAPL</p>
                  <p className="text-xs text-slate-400">Apple Inc</p>
                </div>
                <div className="text-right">
                  <p className="text-slate-300">$192.53</p>
                  <p className="text-xs text-emerald-400">+2.15%</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Activity */}
      <Card className="bg-gray-900/50 border-gray-800/50 shadow-card hover:shadow-card-hover transition-all duration-200">
        <CardHeader>
          <CardTitle className="text-slate-100">Recent Activity</CardTitle>
          <CardDescription className="text-slate-400">
            Your latest trading activity and strategy performance
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center space-x-4 p-4 rounded-lg bg-gray-800/30">
              <div className="w-2 h-2 bg-emerald-400 rounded-full"></div>
              <div className="flex-1">
                <p className="text-slate-300 font-medium">TSLA Strategy executed</p>
                <p className="text-sm text-slate-400">Bought 10 shares at $185.42</p>
              </div>
              <div className="text-right">
                <p className="text-slate-300">+$124.50</p>
                <p className="text-xs text-slate-400">2 hours ago</p>
              </div>
            </div>
            
            <div className="flex items-center space-x-4 p-4 rounded-lg bg-gray-800/30">
              <div className="w-2 h-2 bg-purple-400 rounded-full"></div>
              <div className="flex-1">
                <p className="text-slate-300 font-medium">New strategy created</p>
                <p className="text-sm text-slate-400">Mean Reversion Strategy v2.1</p>
              </div>
              <div className="text-right">
                <p className="text-slate-400">Backtesting</p>
                <p className="text-xs text-slate-400">4 hours ago</p>
              </div>
            </div>
            
            <div className="flex items-center space-x-4 p-4 rounded-lg bg-gray-800/30">
              <div className="w-2 h-2 bg-cyan-400 rounded-full"></div>
              <div className="flex-1">
                <p className="text-slate-300 font-medium">Portfolio rebalanced</p>
                <p className="text-sm text-slate-400">Risk management rules applied</p>
              </div>
              <div className="text-right">
                <p className="text-slate-300">-$45.20</p>
                <p className="text-xs text-slate-400">6 hours ago</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Active Strategies Performance */}
      <Card className="bg-gray-900/50 border-gray-800/50 shadow-card hover:shadow-card-hover transition-all duration-200">
        <CardHeader>
          <CardTitle className="text-slate-100 flex items-center gap-2">
            <Zap className="h-5 w-5 text-yellow-400" />
            Active Strategies
          </CardTitle>
          <CardDescription className="text-slate-400">
            Performance overview of your live trading strategies
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div className="p-4 rounded-lg bg-gray-800/30 hover:bg-gray-800/50 transition-all">
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-slate-300 font-medium">Mean Reversion Pro</h4>
                <span className="text-xs bg-emerald-500/20 text-emerald-300 px-2 py-1 rounded-full">LIVE</span>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">P&L Today:</span>
                  <span className="text-emerald-400">+$247.50</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">Win Rate:</span>
                  <span className="text-slate-300">72%</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">Active Since:</span>
                  <span className="text-slate-300">3 days</span>
                </div>
              </div>
            </div>

            <div className="p-4 rounded-lg bg-gray-800/30 hover:bg-gray-800/50 transition-all">
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-slate-300 font-medium">Momentum Scanner</h4>
                <span className="text-xs bg-blue-500/20 text-blue-300 px-2 py-1 rounded-full">PAPER</span>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">P&L Today:</span>
                  <span className="text-emerald-400">+$89.30</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">Win Rate:</span>
                  <span className="text-slate-300">68%</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">Active Since:</span>
                  <span className="text-slate-300">1 week</span>
                </div>
              </div>
            </div>

            <div className="p-4 rounded-lg bg-gray-800/30 hover:bg-gray-800/50 transition-all">
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-slate-300 font-medium">Volatility Breakout</h4>
                <span className="text-xs bg-orange-500/20 text-orange-300 px-2 py-1 rounded-full">TESTING</span>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">P&L Today:</span>
                  <span className="text-red-400">-$12.80</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">Win Rate:</span>
                  <span className="text-slate-300">64%</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">Active Since:</span>
                  <span className="text-slate-300">2 days</span>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
