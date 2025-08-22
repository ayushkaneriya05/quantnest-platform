import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { TrendingUp, Code2, TestTube2, Rocket, Plug, Shield, BarChart3, Zap, Users, CheckCircle, Star, ArrowRight, Play, Target, Brain, Activity, Globe, Lock, Clock, EyeOff, Lightbulb, Handshake, Award } from 'lucide-react'

// Import the new MainHeader component
import MainHeader from '@/components/layout/main-header'

export default function QuantNestLanding() {
  return (
    <div className="flex flex-col min-h-screen bg-black font-sans">
      {/* Header */}
      <MainHeader /> {/* Use the new MainHeader component */}

      <main className="flex-1">
        {/* Hero Section */}
        <section className="relative overflow-hidden py-12 sm:py-16 md:py-20 lg:py-24 xl:py-32">
          <div className="absolute inset-0 bg-gradient-to-br from-black via-gray-900/20 to-black" />
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(239,68,68,0.1),transparent_50%)]" />
          <div className="relative">
            <div className="container px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
              <div className="mx-auto max-w-4xl text-center">
                <div className="mb-4 sm:mb-6 inline-flex items-center rounded-full bg-slate-800/50 px-3 py-1.5 sm:px-4 sm:py-2 md:px-6 md:py-3 shadow-[inset_0_2px_4px_rgba(255,255,255,0.05),inset_0_-2px_4px_rgba(0,0,0,0.3)] border border-gray-700/50">
                  <Zap className="mr-1.5 sm:mr-2 h-3 w-3 sm:h-4 sm:w-4 text-red-400" />
                  <span className="text-xs sm:text-sm font-medium text-slate-300">Trusted by 50,000+ Professional Traders</span>
                </div>

                <h1 className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl xl:text-7xl font-bold tracking-tight text-slate-100 mb-4 sm:mb-6 md:mb-8 font-heading leading-[1.1] sm:leading-tight">
                  Professional
                  <span className="block text-transparent bg-clip-text bg-gradient-to-r from-red-400 via-blue-400 to-red-500 text-gradient-depth py-1 sm:py-2">
                    Algorithmic Trading
                  </span>
                  <span className="block text-slate-200">Platform</span>
                </h1>

                <p className="mt-4 sm:mt-6 text-base sm:text-lg lg:text-xl leading-6 sm:leading-7 lg:leading-8 text-slate-400 max-w-2xl lg:max-w-3xl mx-auto">
                  Build, backtest, and deploy sophisticated trading strategies with institutional-grade tools. From
                  paper trading to live execution across multiple asset classes.
                </p>

                <div className="mt-6 sm:mt-8 md:mt-10 flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-4 md:gap-6">
                  <Button
                    size="lg"
                    className="w-full sm:w-auto bg-gradient-to-r from-red-500 to-blue-600 hover:from-red-600 hover:to-blue-700 text-white shadow-[0_12px_40px_rgba(239,68,68,0.4)] px-6 py-2.5 sm:px-8 sm:py-3 md:px-10 md:py-4 text-sm sm:text-base md:text-lg font-semibold rounded-2xl border-0"
                  >
                    Start Free Trial
                    <ArrowRight className="ml-2 h-4 w-4 sm:h-5 sm:w-5" />
                  </Button>
                  <Button
                    variant="outline"
                    size="lg"
                    className="w-full sm:w-auto text-slate-300 border-slate-600/50 hover:bg-slate-800/50 hover:text-slate-100 bg-slate-800/30 px-6 py-2.5 sm:px-8 sm:py-3 md:px-10 md:py-4 text-sm sm:text-base md:text-lg font-semibold rounded-2xl shadow-[inset_0_2px_4px_rgba(255,255,255,0.05),inset_0_-2px_4px_rgba(0,0,0,0.3)]"
                  >
                    <Play className="mr-2 h-4 w-4 sm:h-5 sm:w-5" />
                    Watch Demo
                  </Button>
                </div>

                <div className="mt-8 sm:mt-10 md:mt-12 flex flex-wrap items-center justify-center gap-4 sm:gap-6 md:gap-8 text-xs sm:text-sm text-slate-500">
                  <div className="flex items-center">
                    <Shield className="h-3 w-3 sm:h-4 sm:w-4 mr-1 sm:mr-2" />
                    <span>Enterprise Security</span>
                  </div>
                  <div className="flex items-center">
                    <CheckCircle className="h-3 w-3 sm:h-4 sm:w-4 mr-1 sm:mr-2" />
                    <span>No Credit Card Required</span>
                  </div>
                  <div className="flex items-center">
                    <Clock className="h-3 w-3 sm:h-4 sm:w-4 mr-1 sm:mr-2" />
                    <span>Setup in Minutes</span>
                  </div>
                </div>
              </div>

              <div className="mt-12 sm:mt-16 md:mt-20 lg:mt-24">
                <div className="relative rounded-2xl sm:rounded-3xl bg-slate-800/30 p-2 sm:p-3 md:p-4 shadow-[inset_0_4px_8px_rgba(255,255,255,0.05),inset_0_-4px_8px_rgba(0,0,0,0.3)] border border-gray-800 backdrop-blur-sm max-w-6xl mx-auto">
                  <img
                    src="https://images.pexels.com/photos/4960630/pexels-photo-4960630.jpeg"
                    alt="QuantNest Professional Trading Platform"
                    width={1200}
                    height={600}
                    className="rounded-xl sm:rounded-2xl shadow-2xl w-full h-auto"
                  />
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Stats Section */}
        <section className="py-12 sm:py-16 md:py-20 bg-gray-900/30">
          <div className="container px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
            <div className="grid grid-cols-2 gap-4 sm:gap-6 lg:grid-cols-4 md:gap-8">
              <div className="text-center p-4 sm:p-5 md:p-6 rounded-xl sm:rounded-2xl bg-gray-900/50 shadow-[inset_0_2px_4px_rgba(255,255,255,0.05),inset_0_-2px_4px_rgba(0,0,0,0.3)] border border-gray-800/50">
                <div className="text-2xl sm:text-3xl lg:text-4xl font-bold text-red-300 font-heading">$2.5B+</div>
                <div className="text-xs sm:text-sm font-medium text-slate-400 mt-1 sm:mt-2">Assets Under Management</div>
              </div>
              <div className="text-center p-4 sm:p-5 md:p-6 rounded-xl sm:rounded-2xl bg-gray-900/50 shadow-[inset_0_2px_4px_rgba(255,255,255,0.05),inset_0_-2px_4px_rgba(0,0,0,0.3)] border border-gray-800/50">
                <div className="text-2xl sm:text-3xl lg:text-4xl font-bold text-blue-300 font-heading">50K+</div>
                <div className="text-xs sm:text-sm font-medium text-slate-400 mt-1 sm:mt-2">Active Traders</div>
              </div>
              <div className="text-center p-4 sm:p-5 md:p-6 rounded-xl sm:rounded-2xl bg-gray-900/50 shadow-[inset_0_2px_4px_rgba(255,255,255,0.05),inset_0_-2px_4px_rgba(0,0,0,0.3)] border border-gray-800/50">
                <div className="text-2xl sm:text-3xl lg:text-4xl font-bold text-red-300 font-heading">99.99%</div>
                <div className="text-xs sm:text-sm font-medium text-slate-400 mt-1 sm:mt-2">System Uptime</div>
              </div>
              <div className="text-center p-4 sm:p-5 md:p-6 rounded-xl sm:rounded-2xl bg-gray-900/50 shadow-[inset_0_2px_4px_rgba(255,255,255,0.05),inset_0_-2px_4px_rgba(0,0,0,0.3)] border border-gray-800/50">
                <div className="text-2xl sm:text-3xl lg:text-4xl font-bold text-blue-300 font-heading">15+</div>
                <div className="text-xs sm:text-sm font-medium text-slate-400 mt-1 sm:mt-2">Broker Integrations</div>
              </div>
            </div>
          </div>
        </section>

        {/* Features Overview */}
        <section id="features" className="section-padding-lg bg-black">
          <div className="container container-padding max-w-7xl mx-auto">
            <div className="mx-auto max-w-3xl text-center mb-12 sm:mb-16 md:mb-20">
              <h2 className="text-sm font-semibold leading-7 text-red-400 uppercase tracking-wide mb-3 sm:mb-4 section-subtitle">
                Complete Trading Suite
              </h2>
              <p className="text-2xl sm:text-3xl md:text-4xl lg:text-5xl font-bold tracking-tight text-slate-100 mb-4 sm:mb-6 font-heading">
                Everything you need for algorithmic trading
              </p>
              <p className="text-base leading-7 text-slate-400 sm:text-lg sm:leading-8">
                Professional-grade tools designed for traders, by traders. From strategy development to live execution
                with institutional-level infrastructure.
              </p>
            </div>
            
            <div className="mx-auto max-w-7xl">
              <div className="grid grid-cols-1 gap-6 sm:gap-8 md:max-w-2xl md:mx-auto lg:max-w-none lg:grid-cols-3 xl:gap-10">
                <div className="relative overflow-hidden rounded-2xl sm:rounded-3xl bg-gray-900/50 shadow-[inset_0_4px_8px_rgba(255,255,255,0.05),inset_0_-4px_8px_rgba(0,0,0,0.3)] border border-gray-800/50 p-6 sm:p-8">
                  <div className="flex items-center justify-between mb-4 sm:mb-6">
                    <div className="flex h-12 w-12 sm:h-14 sm:w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-500/20 to-teal-600/20 shadow-[inset_0_2px_4px_rgba(255,255,255,0.1),inset_0_-2px_4px_rgba(0,0,0,0.2)]">
                      <Target className="h-6 w-6 sm:h-7 sm:w-7 text-emerald-400" />
                    </div>
                    <div className="rounded-full bg-emerald-500/20 px-2 py-1 text-xs font-medium text-emerald-300 border border-emerald-500/30">
                      Risk-Free
                    </div>
                  </div>
                  <h3 className="text-lg font-semibold text-slate-100 mb-2 sm:text-xl sm:mb-3 font-heading">Paper Trading</h3>
                  <p className="text-sm text-slate-400 sm:text-base">
                    Master your strategies with unlimited paper trading using real-time market data and realistic
                    execution modeling.
                  </p>
                </div>

                <div className="relative overflow-hidden rounded-2xl sm:rounded-3xl bg-gray-900/50 shadow-[inset_0_4px_8px_rgba(255,255,255,0.05),inset_0_-4px_8px_rgba(0,0,0,0.3)] border border-gray-800/50 p-6 sm:p-8">
                  <div className="flex items-center justify-between mb-4 sm:mb-6">
                    <div className="flex h-12 w-12 sm:h-14 sm:w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-red-500/20 to-blue-600/20 shadow-[inset_0_2px_4px_rgba(255,255,255,0.1),inset_0_-2px_4px_rgba(0,0,0,0.2)]">
                      <Code2 className="h-6 w-6 sm:h-7 sm:w-7 text-blue-400" />
                    </div>
                    <div className="rounded-full bg-blue-500/20 px-2 py-1 text-xs font-medium text-blue-300 border border-blue-500/30">
                      AI-Powered
                    </div>
                  </div>
                  <h3 className="text-lg font-semibold text-slate-100 mb-2 sm:text-xl sm:mb-3 font-heading">Strategy Builder</h3>
                  <p className="text-sm text-slate-400 sm:text-base">
                    Build sophisticated algorithms with visual tools or code in Python, JavaScript, and Pine Script
                    with AI assistance.
                  </p>
                </div>

                <div className="relative overflow-hidden rounded-2xl sm:rounded-3xl bg-gray-900/50 shadow-[inset_0_4px_8px_rgba(255,255,255,0.05),inset_0_-4px_8px_rgba(0,0,0,0.3)] border border-gray-800/50 p-6 sm:p-8">
                  <div className="flex items-center justify-between mb-4 sm:mb-6">
                    <div className="flex h-12 w-12 sm:h-14 sm:w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-orange-500/20 to-red-600/20 shadow-[inset_0_2px_4px_rgba(255,255,255,0.1),inset_0_-2px_4px_rgba(0,0,0,0.2)]">
                      <TestTube2 className="h-6 w-6 sm:h-7 sm:w-7 text-orange-400" />
                    </div>
                    <div className="rounded-full bg-orange-500/20 px-2 py-1 text-xs font-medium text-orange-300 border border-orange-500/30">
                      Institutional
                    </div>
                  </div>
                  <h3 className="text-lg font-semibold text-slate-100 mb-2 sm:text-xl sm:mb-3 font-heading">Advanced Backtesting</h3>
                  <p className="text-sm text-slate-400 sm:text-base">
                    Validate strategies with tick-level precision, realistic costs, and comprehensive risk analytics
                    across years of data.
                  </p>
                </div>

                <div className="relative overflow-hidden rounded-2xl sm:rounded-3xl bg-gray-900/50 shadow-[inset_0_4px_8px_rgba(255,255,255,0.05),inset_0_-4px_8px_rgba(0,0,0,0.3)] border border-gray-800/50 p-6 sm:p-8">
                  <div className="flex items-center justify-between mb-4 sm:mb-6">
                    <div className="flex h-12 w-12 sm:h-14 sm:w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-green-500/20 to-emerald-600/20 shadow-[inset_0_2px_4px_rgba(255,255,255,0.1),inset_0_-2px_4px_rgba(0,0,0,0.2)]">
                      <Rocket className="h-6 w-6 sm:h-7 sm:w-7 text-green-400" />
                    </div>
                    <div className="rounded-full bg-green-500/20 px-2 py-1 text-xs font-medium text-green-300 border border-green-500/30">
                      Live
                    </div>
                  </div>
                  <h3 className="text-lg font-semibold text-slate-100 mb-2 sm:text-xl sm:mb-3 font-heading">Live Deployment</h3>
                  <p className="text-sm text-slate-400 sm:text-base">
                    Deploy proven strategies to live markets with one-click execution, real-time monitoring, and
                    automatic risk management.
                  </p>
                </div>

                <div className="relative overflow-hidden rounded-2xl sm:rounded-3xl bg-gray-900/50 shadow-[inset_0_4px_8px_rgba(255,255,255,0.05),inset_0_-4px_8px_rgba(0,0,0,0.3)] border border-gray-800/50 p-6 sm:p-8">
                  <div className="flex items-center justify-between mb-4 sm:mb-6">
                    <div className="flex h-12 w-12 sm:h-14 sm:w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500/20 to-cyan-600/20 shadow-[inset_0_2px_4px_rgba(255,255,255,0.1),inset_0_-2px_4px_rgba(0,0,0,0.2)]">
                      <Plug className="h-6 w-6 sm:h-7 sm:w-7 text-blue-400" />
                    </div>
                    <div className="rounded-full bg-blue-500/20 px-2 py-1 text-xs font-medium text-blue-300 border border-blue-500/30">
                      Multi-Broker
                    </div>
                  </div>
                  <h3 className="text-lg font-semibold text-slate-100 mb-2 sm:text-xl sm:mb-3 font-heading">Broker Integration</h3>
                  <p className="text-sm text-slate-400 sm:text-base">
                    Connect to 15+ major brokers including Interactive Brokers, TD Ameritrade, and Alpaca with secure
                    API connections.
                  </p>
                </div>

                <div className="relative overflow-hidden rounded-2xl sm:rounded-3xl bg-gray-900/50 shadow-[inset_0_4px_8px_rgba(255,255,255,0.05),inset_0_-4px_8px_rgba(0,0,0,0.3)] border border-gray-800/50 p-6 sm:p-8">
                  <div className="flex items-center justify-between mb-4 sm:mb-6">
                    <div className="flex h-12 w-12 sm:h-14 sm:w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-red-500/20 to-blue-600/20 shadow-[inset_0_2px_4px_rgba(255,255,255,0.1),inset_0_-2px_4px_rgba(0,0,0,0.2)]">
                      <BarChart3 className="h-6 w-6 sm:h-7 sm:w-7 text-red-400" />
                    </div>
                    <div className="rounded-full bg-red-500/20 px-2 py-1 text-xs font-medium text-red-300 border border-red-500/30">
                      Analytics
                    </div>
                  </div>
                  <h3 className="text-lg font-semibold text-slate-100 mb-2 sm:text-xl sm:mb-3 font-heading">Performance Analytics</h3>
                  <p className="text-sm text-slate-400 sm:text-base">
                    Comprehensive performance tracking with Sharpe ratio, drawdown analysis, alpha, beta, and custom
                    risk metrics.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* How It Works Section */}
        <section className="py-20 sm:py-24 lg:py-32 bg-gray-900/30">
          <div className="container px-4 sm:px-6 lg:px-8">
            <div className="mx-auto max-w-3xl text-center mb-16 sm:mb-20">
              <h2 className="text-sm font-semibold leading-7 text-red-400 uppercase tracking-wide mb-3 sm:mb-4 section-subtitle">
                Simple Process
              </h2>
              <p className="text-3xl font-bold tracking-tight text-slate-100 sm:text-4xl lg:text-5xl mb-4 sm:mb-6 font-heading">
                How It Works
              </p>
              <p className="text-base leading-7 text-slate-400 sm:text-lg sm:leading-8">
                Get started with algorithmic trading in three simple steps. No complex setup required.
              </p>
            </div>

            <div className="mx-auto max-w-5xl flex flex-col">
              <div className="grid max-w-xl grid-cols-1 gap-8 lg:max-w-none lg:grid-cols-3 sm:gap-12 mx-auto">
                {/* Step 1 */}
                <div className="relative text-center p-4">
                  <div className="flex h-16 w-16 sm:h-20 sm:w-20 items-center justify-center rounded-3xl bg-gradient-to-br from-red-500/20 to-blue-600/20 shadow-[inset_0_4px_8px_rgba(255,255,255,0.1),inset_0_-2px_4px_rgba(0,0,0,0.2)] border border-red-500/30 mx-auto mb-6 sm:mb-8">
                    <Brain className="h-8 w-8 sm:h-10 sm:w-10 text-red-400" />
                  </div>
                  <div className="absolute -top-2 -right-2 bg-gradient-to-r from-red-500 to-blue-600 text-white text-sm font-bold rounded-full w-7 h-7 sm:w-8 sm:h-8 flex items-center justify-center">
                    1
                  </div>
                  <h3 className="text-xl font-bold text-slate-100 mb-3 sm:text-2xl sm:mb-4 font-heading">Discover with AI</h3>
                  <p className="text-sm text-slate-400 leading-relaxed sm:text-lg">
                    Get personalized stock picks, news summaries, and market analysis from your personal AI research assistant.
                  </p>
                </div>

                {/* Step 2 */}
                <div className="relative text-center p-4">
                  <div className="flex h-16 w-16 sm:h-20 sm:w-20 items-center justify-center rounded-3xl bg-gradient-to-br from-emerald-500/20 to-teal-600/20 shadow-[inset_0_4px_8px_rgba(255,255,255,0.1),inset_0_-2px_4px_rgba(0,0,0,0.2)] border border-emerald-500/30 mx-auto mb-6 sm:mb-8">
                    <Code2 className="h-8 w-8 sm:h-10 sm:w-10 text-emerald-400" />
                  </div>
                  <div className="absolute -top-2 -right-2 bg-gradient-to-r from-emerald-500 to-teal-600 text-white text-sm font-bold rounded-full w-7 h-7 sm:w-8 sm:h-8 flex items-center justify-center">
                    2
                  </div>
                  <h3 className="text-xl font-bold text-slate-100 mb-3 sm:text-2xl sm:mb-4 font-heading">Build & Backtest</h3>
                  <p className="text-sm text-slate-400 leading-relaxed sm:text-lg">
                    Use our simple drag-and-drop interface to build a trading strategy based on indicators and logic. No coding required. Backtest it instantly on historical data.
                  </p>
                </div>

                {/* Step 3 */}
                <div className="relative text-center p-4">
                  <div className="flex h-16 w-16 sm:h-20 sm:w-20 items-center justify-center rounded-3xl bg-gradient-to-br from-orange-500/20 to-red-600/20 shadow-[inset_0_4px_8px_rgba(255,255,255,0.1),inset_0_-2px_4px_rgba(0,0,0,0.2)] border border-orange-500/30 mx-auto mb-6 sm:mb-8">
                    <Rocket className="h-8 w-8 sm:h-10 sm:w-10 text-orange-400" />
                  </div>
                  <div className="absolute -top-2 -right-2 bg-gradient-to-r from-orange-500 to-red-600 text-white text-sm font-bold rounded-full w-7 h-7 sm:w-8 sm:h-8 flex items-center justify-center">
                    3
                  </div>
                  <h3 className="text-xl font-bold text-slate-100 mb-3 sm:text-2xl sm:mb-4 font-heading">Deploy with Confidence</h3>
                  <p className="text-sm text-slate-400 leading-relaxed sm:text-lg">
                    Practice your strategy in our risk-free paper trading environment with real-time market data. When you're ready, connect your broker and deploy it live.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Detailed Feature: Algo Trading */}
        <section className="py-20 sm:py-24 lg:py-32 bg-black">
          <div className="container px-4 sm:px-6 lg:px-8">
            <div className="mx-auto grid max-w-2xl grid-cols-1 gap-y-12 sm:gap-y-16 lg:mx-0 lg:max-w-none lg:grid-cols-2 lg:items-center lg:gap-x-8">
              <div className="lg:pr-8 lg:pt-4">
                <div className="lg:max-w-lg">
                  <h2 className="text-sm font-semibold leading-7 text-blue-400 uppercase tracking-wide mb-3 sm:mb-4 section-subtitle">
                    Automated Excellence
                  </h2>
                  <p className="text-3xl font-bold tracking-tight text-slate-100 sm:text-4xl mb-4 sm:mb-6 font-heading">
                    Automate Your Trading with Algo Trading
                  </p>
                  <p className="text-base leading-7 text-slate-400 mb-8 sm:mb-10 sm:text-lg">
                    With QuantNest's Algo Trading feature, you can create and deploy automated trading strategies that execute trades on your behalf, ensuring you never miss an opportunity.
                  </p>
                  
                  <dl className="space-y-6 text-sm leading-6 sm:space-y-8 sm:text-base sm:leading-7">
                    <div className="relative pl-8 sm:pl-9">
                      <dt className="inline font-semibold text-slate-200">
                        <Code2 className="absolute left-0 top-0 h-4 w-4 sm:h-5 sm:w-5 text-blue-400" />
                        Customizable Algorithms
                      </dt>
                      <dd className="inline text-slate-400">
                        {" "}
                        Tailor your trading algorithms to fit your unique strategy and risk tolerance with our intuitive builder.
                      </dd>
                    </div>
                    <div className="relative pl-8 sm:pl-9">
                      <dt className="inline font-semibold text-slate-200">
                        <Zap className="absolute left-0 top-0 h-4 w-4 sm:h-5 sm:w-5 text-blue-400" />
                        Real-Time Execution
                      </dt>
                      <dd className="inline text-slate-400">
                        {" "}
                        Ensure your trades are executed instantly based on market conditions, maximizing your potential gains.
                      </dd>
                    </div>
                    <div className="relative pl-8 sm:pl-9">
                      <dt className="inline font-semibold text-slate-200">
                        <TestTube2 className="absolute left-0 top-0 h-4 w-4 sm:h-5 sm:w-5 text-blue-400" />
                        Backtesting Capabilities
                      </dt>
                      <dd className="inline text-slate-400">
                        {" "}
                        Test your algorithms against historical data to refine your strategies before going live.
                      </dd>
                    </div>
                    <div className="relative pl-8 sm:pl-9">
                      <dt className="inline font-semibold text-slate-200">
                        <BarChart3 className="absolute left-0 top-0 h-4 w-4 sm:h-5 sm:w-5 text-blue-400" />
                        Performance Analytics
                      </dt>
                      <dd className="inline text-slate-400">
                        {" "}
                        Monitor the performance of your algorithms with detailed analytics to make informed adjustments.
                      </dd>
                    </div>
                  </dl>
                  
                  <div className="mt-8 sm:mt-10">
                    <Button className="bg-gradient-to-r from-blue-500 to-red-600 hover:from-blue-600 hover:to-red-700 text-white shadow-[0_8px_32px_rgba(59,130,246,0.3)] rounded-2xl px-8 py-3 text-base">
                      Build Your First Algorithm
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </div>
              <div className="relative">
                <div className="absolute inset-0 bg-gradient-to-r from-blue-500/10 to-red-500/10 rounded-3xl transform -rotate-1 shadow-[inset_0_4px_8px_rgba(255,255,255,0.05),inset_0_-4px_8px_rgba(0,0,0,0.3)]"></div>
                <img
                  src="https://images.pexels.com/photos/3183170/pexels-photo-3183170.jpeg"
                  alt="Algo Trading Flowchart Interface"
                  width={600}
                  height={400}
                  className="relative w-full max-w-none rounded-2xl shadow-2xl border border-gray-800 h-auto"
                />
              </div>
            </div>
          </div>
        </section>

        {/* Detailed Feature: AI Research Assistant */}
        <section className="py-20 sm:py-24 lg:py-32 bg-gray-900/30">
          <div className="container px-4 sm:px-6 lg:px-8">
            <div className="mx-auto grid max-w-2xl grid-cols-1 gap-y-12 sm:gap-y-16 lg:mx-0 lg:max-w-none lg:grid-cols-2 lg:items-center lg:gap-x-8">
              <div className="relative lg:order-first">
                <div className="absolute inset-0 bg-gradient-to-r from-red-500/10 to-blue-500/10 rounded-3xl transform rotate-1 shadow-[inset_0_4px_8px_rgba(255,255,255,0.05),inset_0_-4px_8px_rgba(0,0,0,0.3)]"></div>
                <img
                  src="/placeholder.svg?height=400&width=600&text=AI+Research+Assistant"
                  alt="AI Research Assistant Interface"
                  width={600}
                  height={400}
                  className="relative w-full max-w-none rounded-2xl shadow-2xl border border-gray-800 h-auto"
                />
              </div>
              <div className="lg:pl-8 lg:pt-4">
                <div className="lg:max-w-lg">
                  <h2 className="text-sm font-semibold leading-7 text-red-400 uppercase tracking-wide mb-3 sm:mb-4 section-subtitle">
                    AI-Powered Intelligence
                  </h2>
                  <p className="text-3xl font-bold tracking-tight text-slate-100 sm:text-4xl mb-4 sm:mb-6 font-heading">
                    Your Personal AI Research Assistant
                  </p>
                  <p className="text-base leading-7 text-slate-400 mb-8 sm:mb-10 sm:text-lg">
                    Leverage the power of AI to enhance your trading decisions with intelligent insights and data-driven recommendations tailored to your trading style.
                  </p>
                  
                  <dl className="space-y-6 text-sm leading-6 sm:space-y-8 sm:text-base sm:leading-7">
                    <div className="relative pl-8 sm:pl-9">
                      <dt className="inline font-semibold text-slate-200">
                        <Target className="absolute left-0 top-0 h-4 w-4 sm:h-5 sm:w-5 text-red-400" />
                        Personalized Insights
                      </dt>
                      <dd className="inline text-slate-400">
                        {" "}
                        Receive tailored stock picks and market analysis based on your trading preferences and history.
                      </dd>
                    </div>
                    <div className="relative pl-8 sm:pl-9">
                      <dt className="inline font-semibold text-slate-200">
                        <Globe className="absolute left-0 top-0 h-4 w-4 sm:h-5 sm:w-5 text-red-400" />
                        News Summaries
                      </dt>
                      <dd className="inline text-slate-400">
                        {" "}
                        Stay updated with concise summaries of market news that impact your trading strategies.
                      </dd>
                    </div>
                    <div className="relative pl-8 sm:pl-9">
                      <dt className="inline font-semibold text-slate-200">
                        <Activity className="absolute left-0 top-0 h-4 w-4 sm:h-5 sm:w-5 text-red-400" />
                        Data-Driven Recommendations
                      </dt>
                      <dd className="inline text-slate-400">
                        {" "}
                        Get actionable insights derived from millions of data points, helping you make informed trading decisions.
                      </dd>
                    </div>
                    <div className="relative pl-8 sm:pl-9">
                      <dt className="inline font-semibold text-slate-200">
                        <Brain className="absolute left-0 top-0 h-4 w-4 sm:h-5 sm:w-5 text-red-400" />
                        Continuous Learning
                      </dt>
                      <dd className="inline text-slate-400">
                        {" "}
                        The AI adapts and improves its recommendations based on your trading behavior and market changes.
                      </dd>
                    </div>
                  </dl>
                  
                  <div className="mt-8 sm:mt-10">
                    <Button className="bg-gradient-to-r from-red-500 to-blue-600 hover:from-red-600 hover:to-blue-700 text-white shadow-[0_8px_32px_rgba(239,68,68,0.3)] rounded-2xl px-8 py-3 text-base">
                      Try AI Assistant
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Detailed Feature: Paper Trading */}
        <section className="py-20 sm:py-24 lg:py-32 bg-gray-900/30">
          <div className="container px-4 sm:px-6 lg:px-8">
            <div className="mx-auto grid max-w-2xl grid-cols-1 gap-y-12 sm:gap-y-16 lg:mx-0 lg:max-w-none lg:grid-cols-2 lg:items-center lg:gap-x-8">
              <div className="lg:pr-8 lg:pt-4">
                <div className="lg:max-w-lg">
                  <h2 className="text-sm font-semibold leading-7 text-emerald-400 uppercase tracking-wide mb-3 sm:mb-4 section-subtitle">
                    Risk-Free Learning
                  </h2>
                  <p className="text-3xl font-bold tracking-tight text-slate-100 sm:text-4xl mb-4 sm:mb-6 font-heading">
                    Master Paper Trading
                  </p>
                  <p className="text-base leading-7 text-slate-400 mb-8 sm:mb-10 sm:text-lg">
                    Perfect your trading strategies without risking real capital. Our paper trading environment provides
                    real-time market data with institutional-grade execution simulation.
                  </p>
                  
                  <dl className="space-y-6 text-sm leading-6 sm:space-y-8 sm:text-base sm:leading-7">
                    <div className="relative pl-8 sm:pl-9">
                      <dt className="inline font-semibold text-slate-200">
                        <Globe className="absolute left-0 top-0 h-4 w-4 sm:h-5 sm:w-5 text-emerald-400" />
                        Real-time global data
                      </dt>
                      <dd className="inline text-slate-400">
                        {" "}
                        from 50+ exchanges worldwide with microsecond precision.
                      </dd>
                    </div>
                    <div className="relative pl-8 sm:pl-9">
                      <dt className="inline font-semibold text-slate-200">
                        <Activity className="absolute left-0 top-0 h-4 w-4 sm:h-5 sm:w-5 text-emerald-400" />
                        Realistic execution
                      </dt>
                      <dd className="inline text-slate-400">
                        {" "}
                        with advanced slippage modeling and latency simulation.
                      </dd>
                    </div>
                    <li className="flex items-start">
                      <BarChart3 className="h-5 w-5 text-emerald-400 mr-3 flex-shrink-0 mt-1" />
                      <span className="text-slate-300 text-base">Portfolio analytics with detailed P&L tracking and risk attribution analysis.</span>
                    </li>
                  </dl>
                  
                  <div className="mt-8 sm:mt-10">
                    <Button className="bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 text-white shadow-[0_8px_32px_rgba(16,185,129,0.3)] rounded-2xl px-8 py-3 text-base">
                      Start Paper Trading
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </div>
              <div className="relative">
                <div className="absolute inset-0 bg-gradient-to-r from-emerald-500/10 to-teal-500/10 rounded-3xl transform rotate-1 shadow-[inset_0_4px_8px_rgba(255,255,255,0.05),inset_0_-4px_8px_rgba(0,0,0,0.3)]"></div>
                <img
                  src="/placeholder.svg"
                  alt="Paper Trading Interface"
                  width={600}
                  height={400}
                  className="relative w-full max-w-none rounded-2xl shadow-2xl border border-gray-800 h-auto"
                />
              </div>
            </div>
          </div>
        </section>

        {/* Pricing Section */}
        <section id="pricing" className="py-20 sm:py-24 lg:py-32 bg-black">
          <div className="container px-4 sm:px-6 lg:px-8">
            <div className="mx-auto max-w-3xl text-center mb-16 sm:mb-20">
              <h2 className="text-3xl font-bold tracking-tight text-slate-100 sm:text-4xl lg:text-5xl mb-4 sm:mb-6 font-heading">
                Professional Pricing Plans
              </h2>
              <p className="text-base leading-7 text-slate-400 sm:text-lg sm:leading-8">
                Choose the plan that fits your trading needs. All plans include our core features with different limits
                and capabilities.
              </p>
            </div>
            
            <div className="mx-auto grid max-w-lg grid-cols-1 gap-6 lg:max-w-6xl lg:grid-cols-3 sm:gap-8">
              <div className="flex flex-col justify-between rounded-3xl bg-gray-900/50 shadow-[inset_0_4px_8px_rgba(255,255,255,0.05),inset_0_-4px_8px_rgba(0,0,0,0.3)] border border-gray-800/50 p-6 sm:p-8">
                <div className="pb-6 sm:pb-8">
                  <h3 className="text-xl font-bold text-slate-100 mb-2 sm:text-2xl font-heading">Starter</h3>
                  <p className="text-sm text-slate-400 mb-6 sm:mb-8">Perfect for learning and experimentation</p>
                  <div className="mb-6 sm:mb-8">
                    <span className="text-4xl font-bold text-slate-100 sm:text-5xl font-heading">$0</span>
                    <span className="text-base font-semibold text-slate-400 sm:text-lg">/month</span>
                  </div>
                </div>
                <div className="flex-1">
                  <ul className="space-y-3 text-sm mb-6 sm:mb-8">
                    <li className="flex items-center">
                      <CheckCircle className="h-4 w-4 text-emerald-400 mr-2 sm:h-5 sm:w-5 sm:mr-3" />
                      <span className="text-slate-300">Unlimited paper trading</span>
                    </li>
                    <li className="flex items-center">
                      <CheckCircle className="h-4 w-4 text-emerald-400 mr-2 sm:h-5 sm:w-5 sm:mr-3" />
                      <span className="text-slate-300">Basic backtesting (1 year data)</span>
                    </li>
                    <li className="flex items-center">
                      <CheckCircle className="h-4 w-4 text-emerald-400 mr-2 sm:h-5 sm:w-5 sm:mr-3" />
                      <span className="text-slate-300">5 strategies maximum</span>
                    </li>
                    <li className="flex items-center">
                      <CheckCircle className="h-4 w-4 text-emerald-400 mr-2 sm:h-5 sm:w-5 sm:mr-3" />
                      <span className="text-slate-300">Community support</span>
                    </li>
                  </ul>
                  <Button className="w-full bg-slate-700/50 text-slate-200 hover:bg-slate-700 border border-slate-600/50 rounded-2xl shadow-[inset_0_2px_4px_rgba(255,255,255,0.05),inset_0_-2px_4px_rgba(0,0,0,0.3)] text-base">
                    Get Started Free
                  </Button>
                </div>
              </div>

              <div className="flex flex-col justify-between rounded-3xl bg-gradient-to-br from-red-500/10 to-blue-600/10 shadow-[inset_0_4px_8px_rgba(255,255,255,0.05),inset_0_-4px_8px_rgba(0,0,0,0.3)] border border-red-500/30 p-6 sm:p-8 relative">
                <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                  <div className="bg-gradient-to-r from-red-500 to-blue-600 text-white px-3 py-1 rounded-full text-xs font-medium sm:px-4 sm:py-1 sm:text-sm">
                    Most Popular
                  </div>
                </div>
                <div className="pb-6 sm:pb-8">
                  <h3 className="text-xl font-bold text-slate-100 mb-2 sm:text-2xl font-heading">Professional</h3>
                  <p className="text-sm text-slate-400 mb-6 sm:mb-8">For serious traders and small teams</p>
                  <div className="mb-6 sm:mb-8">
                    <span className="text-4xl font-bold text-slate-100 sm:text-5xl font-heading">$99</span>
                    <span className="text-base font-semibold text-slate-400 sm:text-lg">/month</span>
                  </div>
                </div>
                <div className="flex-1">
                  <ul className="space-y-3 text-sm mb-6 sm:mb-8">
                    <li className="flex items-center">
                      <CheckCircle className="h-4 w-4 text-emerald-400 mr-2 sm:h-5 sm:w-5 sm:mr-3" />
                      <span className="text-slate-300">Everything in Starter</span>
                    </li>
                    <li className="flex items-center">
                      <CheckCircle className="h-4 w-4 text-emerald-400 mr-2 sm:h-5 sm:w-5 sm:mr-3" />
                      <span className="text-slate-300">Live trading (1 broker)</span>
                    </li>
                    <li className="flex items-center">
                      <CheckCircle className="h-4 w-4 text-emerald-400 mr-2 sm:h-5 sm:w-5 sm:mr-3" />
                      <span className="text-slate-300">Advanced backtesting (10 years)</span>
                    </li>
                    <li className="flex items-center">
                      <CheckCircle className="h-4 w-4 text-emerald-400 mr-2 sm:h-5 sm:w-5 sm:mr-3" />
                      <span className="text-slate-300">50 strategies maximum</span>
                    </li>
                    <li className="flex items-center">
                      <CheckCircle className="h-4 w-4 text-emerald-400 mr-2 sm:h-5 sm:w-5 sm:mr-3" />
                      <span className="text-slate-300">Priority support</span>
                    </li>
                  </ul>
                  <Button className="w-full bg-gradient-to-r from-red-500 to-blue-600 hover:from-red-600 hover:to-blue-700 text-white shadow-[0_8px_32px_rgba(239,68,68,0.3)] rounded-2xl text-base">
                    Start Free Trial
                  </Button>
                </div>
              </div>

              <div className="flex flex-col justify-between rounded-3xl bg-gray-900/50 shadow-[inset_0_4px_8px_rgba(255,255,255,0.05),inset_0_-4px_8px_rgba(0,0,0,0.3)] border border-gray-800/50 p-6 sm:p-8">
                <div className="pb-6 sm:pb-8">
                  <h3 className="text-xl font-bold text-slate-100 mb-2 sm:text-2xl font-heading">Enterprise</h3>
                  <p className="text-sm text-slate-400 mb-6 sm:mb-8">For institutions and large teams</p>
                  <div className="mb-6 sm:mb-8">
                    <span className="text-4xl font-bold text-slate-100 sm:text-5xl font-heading">$499</span>
                    <span className="text-base font-semibold text-slate-400 sm:text-lg">/month</span>
                  </div>
                </div>
                <div className="flex-1">
                  <ul className="space-y-3 text-sm mb-6 sm:mb-8">
                    <li className="flex items-center">
                      <CheckCircle className="h-4 w-4 text-emerald-400 mr-2 sm:h-5 sm:w-5 sm:mr-3" />
                      <span className="text-slate-300">Everything in Professional</span>
                    </li>
                    <li className="flex items-center">
                      <CheckCircle className="h-4 w-4 text-emerald-400 mr-2 sm:h-5 sm:w-5 sm:mr-3" />
                      <span className="text-slate-300">Multiple broker connections</span>
                    </li>
                    <li className="flex items-center">
                      <CheckCircle className="h-4 w-4 text-emerald-400 mr-2 sm:h-5 sm:w-5 sm:mr-3" />
                      <span className="text-slate-300">Unlimited strategies</span>
                    </li>
                    <li className="flex items-center">
                      <CheckCircle className="h-4 w-4 text-emerald-400 mr-2 sm:h-5 sm:w-5 sm:mr-3" />
                      <span className="text-slate-300">Custom integrations</span>
                    </li>
                    <li className="flex items-center">
                      <CheckCircle className="h-4 w-4 text-emerald-400 mr-2 sm:h-5 sm:w-5 sm:mr-3" />
                      <span className="text-slate-300">Dedicated support</span>
                    </li>
                  </ul>
                  <Button className="w-full bg-slate-700/50 text-slate-200 hover:bg-slate-700 border border-slate-600/50 rounded-2xl shadow-[inset_0_2px_4px_rgba(255,255,255,0.05),inset_0_-2px_4px_rgba(0,0,0,0.3)] text-base">
                    Contact Sales
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Testimonials */}
        <section className="py-20 sm:py-24 lg:py-32 bg-gray-900/30">
          <div className="container px-4 sm:px-6 lg:px-8">
            <div className="mx-auto max-w-3xl text-center mb-16 sm:mb-20">
              <h2 className="text-3xl font-bold tracking-tight text-slate-100 sm:text-4xl lg:text-5xl mb-4 sm:mb-6 font-heading">
                Trusted by professionals worldwide
              </h2>
              <p className="text-base leading-7 text-slate-400 sm:text-lg sm:leading-8">
                See what traders and institutions are saying about QuantNest
              </p>
            </div>
            
            <div className="mx-auto grid max-w-2xl grid-cols-1 gap-6 lg:mx-0 lg:max-w-none lg:grid-cols-3 sm:gap-8">
              <div className="rounded-3xl bg-gray-900/50 shadow-[inset_0_4px_8px_rgba(255,255,255,0.05),inset_0_-4px_8px_rgba(0,0,0,0.3)] border border-gray-800/50 p-6 sm:p-8">
                <div className="flex items-center mb-4 sm:mb-6">
                  {[...Array(5)].map((_, i) => (
                    <Star key={i} className="h-4 w-4 sm:h-5 sm:w-5 fill-yellow-400 text-yellow-400" />
                  ))}
                </div>
                <p className="text-base text-slate-300 mb-4 sm:mb-6 sm:text-lg leading-relaxed testimonial-quote">
                  "QuantNest's backtesting engine is incredibly sophisticated. The tick-level precision and realistic
                  cost modeling helped me optimize my strategies before going live."
                </p>
                <div className="flex items-center">
                  <div className="h-10 w-10 sm:h-12 sm:w-12 rounded-2xl bg-gradient-to-br from-blue-500/20 to-cyan-600/20 flex items-center justify-center text-white font-semibold shadow-[inset_0_2px_4px_rgba(255,255,255,0.1),inset_0_-2px_4px_rgba(0,0,0,0.2)] text-sm sm:text-base">
                    SC
                  </div>
                  <div className="ml-3 sm:ml-4">
                    <p className="text-sm font-semibold text-slate-200">Sarah Chen</p>
                    <p className="text-xs text-slate-400">Senior Quantitative Trader, Citadel</p>
                  </div>
                </div>
              </div>

              <div className="rounded-3xl bg-gray-900/50 shadow-[inset_0_4px_8px_rgba(255,255,255,0.05),inset_0_-4px_8px_rgba(0,0,0,0.3)] border border-gray-800/50 p-6 sm:p-8">
                <div className="flex items-center mb-4 sm:mb-6">
                  {[...Array(5)].map((_, i) => (
                    <Star key={i} className="h-4 w-4 sm:h-5 sm:w-5 fill-yellow-400 text-yellow-400" />
                  ))}
                </div>
                <p className="text-base text-slate-300 mb-4 sm:mb-6 sm:text-lg leading-relaxed testimonial-quote">
                  "The broker integrations are seamless and the execution is lightning fast. We've deployed multiple
                  strategies across different asset classes without any issues."
                </p>
                <div className="flex items-center">
                  <div className="h-10 w-10 sm:h-12 sm:w-12 rounded-2xl bg-gradient-to-br from-emerald-500/20 to-teal-600/20 flex items-center justify-center text-white font-semibold shadow-[inset_0_2px_4px_rgba(255,255,255,0.1),inset_0_-2px_4px_rgba(0,0,0,0.2)] text-sm sm:text-base">
                    MR
                  </div>
                  <div className="ml-3 sm:ml-4">
                    <p className="text-sm font-semibold text-slate-200">Michael Rodriguez</p>
                    <p className="text-xs text-slate-400">Portfolio Manager, Two Sigma</p>
                  </div>
                </div>
              </div>

              <div className="rounded-3xl bg-gray-900/50 shadow-[inset_0_4px_8px_rgba(255,255,255,0.05),inset_0_-4px_8px_rgba(0,0,0,0.3)] border border-gray-800/50 p-6 sm:p-8">
                <div className="flex items-center mb-4 sm:mb-6">
                  {[...Array(5)].map((_, i) => (
                    <Star key={i} className="h-4 w-4 sm:h-5 sm:w-5 fill-yellow-400 text-yellow-400" />
                  ))}
                </div>
                <p className="text-base text-slate-300 mb-4 sm:mb-6 sm:text-lg leading-relaxed testimonial-quote">
                  "Started with paper trading and now managing a profitable portfolio. The learning curve was smooth
                  thanks to the intuitive interface and excellent documentation."
                </p>
                <div className="flex items-center">
                  <div className="h-10 w-10 sm:h-12 sm:w-12 rounded-2xl bg-gradient-to-br from-red-500/20 to-blue-600/20 flex items-center justify-center text-white font-semibold shadow-[inset_0_2px_4px_rgba(255,255,255,0.1),inset_0_-2px_4px_rgba(0,0,0,0.2)] text-sm sm:text-base">
                    DK
                  </div>
                  <div className="ml-3 sm:ml-4">
                    <p className="text-sm font-semibold text-slate-200">David Kim</p>
                    <p className="text-xs text-slate-400">Independent Trader</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Security & Trust Section */}
        <section className="py-20 sm:py-24 lg:py-32 bg-black">
          <div className="container px-4 sm:px-6 lg:px-8">
            <div className="mx-auto max-w-3xl text-center mb-16 sm:mb-20">
              <h2 className="text-3xl font-bold tracking-tight text-slate-100 sm:text-4xl lg:text-5xl mb-4 sm:mb-6 font-heading">
                Security Isn't a Feature. It's Our Foundation.
              </h2>
              <p className="text-base leading-7 text-slate-400 sm:text-lg sm:leading-8">
                We use bank-grade security and industry best practices to protect your data and your privacy.
              </p>
            </div>

            <div className="mx-auto max-w-6xl flex flex-col">
              <div className="grid max-w-xl grid-cols-1 gap-6 lg:max-w-none lg:grid-cols-3 sm:gap-8 mx-auto">
                {/* Broker-Level Security */}
                <div className="text-center p-6 sm:p-8 rounded-3xl bg-gray-900/50 shadow-[inset_0_4px_8px_rgba(255,255,255,0.05),inset_0_-4px_8px_rgba(0,0,0,0.3)] border border-gray-800/50">
                  <div className="flex h-14 w-14 sm:h-16 sm:w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500/20 to-cyan-600/20 shadow-[inset_0_2px_4px_rgba(255,255,255,0.1),inset_0_-2px_4px_rgba(0,0,0,0.2)] mx-auto mb-4 sm:mb-6">
                    <Shield className="h-7 w-7 sm:h-8 sm:w-8 text-blue-400" />
                  </div>
                  <h3 className="text-lg font-semibold text-slate-100 mb-3 sm:text-xl sm:mb-4 font-heading">Broker-Level Security</h3>
                  <p className="text-sm text-slate-400 leading-relaxed sm:text-base">
                    We never store your broker credentials. Your account is connected via a secure, encrypted API token using the official broker-provided login process.
                  </p>
                </div>

                {/* Data Encryption */}
                <div className="text-center p-6 sm:p-8 rounded-3xl bg-gray-900/50 shadow-[inset_0_4px_8px_rgba(255,255,255,0.05),inset_0_-4px_8px_rgba(0,0,0,0.3)] border border-gray-800/50">
                  <div className="flex h-14 w-14 sm:h-16 sm:w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-green-500/20 to-emerald-600/20 shadow-[inset_0_2px_4px_rgba(255,255,255,0.1),inset_0_-2px_4px_rgba(0,0,0,0.2)] mx-auto mb-4 sm:mb-6">
                    <Lock className="h-7 w-7 sm:h-8 sm:w-8 text-green-400" />
                  </div>
                  <h3 className="text-lg font-semibold text-slate-100 mb-3 sm:text-xl sm:mb-4 font-heading">Data Encryption</h3>
                  <p className="text-sm text-slate-400 leading-relaxed sm:text-base">
                    All your personal data and trading strategies are protected with AES-256 encryption, both in transit and at rest.
                  </p>
                </div>

                {/* Strict Privacy */}
                <div className="text-center p-6 sm:p-8 rounded-3xl bg-gray-900/50 shadow-[inset_0_4px_8px_rgba(255,255,255,0.05),inset_0_-4px_8px_rgba(0,0,0,0.3)] border border-gray-800/50">
                  <div className="flex h-14 w-14 sm:h-16 sm:w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-red-500/20 to-blue-600/20 shadow-[inset_0_2px_4px_rgba(255,255,255,0.1),inset_0_-2px_4px_rgba(0,0,0,0.2)] mx-auto mb-4 sm:mb-6">
                    <EyeOff className="h-7 w-7 sm:h-8 sm:w-8 text-red-400" />
                  </div>
                  <h3 className="text-lg font-semibold text-slate-100 mb-3 sm:text-xl sm:mb-4 font-heading">Strict Privacy</h3>
                  <p className="text-sm text-slate-400 leading-relaxed sm:text-base">
                    We will never sell your personal data or your trading data to third parties. Your strategies are your intellectual property, period.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Behind the Nest Section */}
        <section className="py-20 sm:py-24 lg:py-32 bg-gray-900/30">
          <div className="container px-4 sm:px-6 lg:px-8">
            <div className="mx-auto max-w-4xl">
              <div className="text-center mb-10 sm:mb-12">
                <h2 className="text-3xl font-bold tracking-tight text-slate-100 sm:text-4xl lg:text-5xl mb-4 sm:mb-6 font-heading">
                  Built in Ahmedabad, for the Indian Trader
                </h2>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 sm:gap-12 items-center">
                <div className="lg:col-span-1">
                  <div className="w-40 h-40 sm:w-48 sm:h-48 mx-auto rounded-2xl bg-gradient-to-br from-red-500/20 to-blue-600/20 shadow-[inset_0_4px_8px_rgba(255,255,255,0.05),inset_0_-2px_4px_rgba(0,0,0,0.3)] border border-gray-800/50 flex items-center justify-center">
                    <Users className="h-20 w-20 sm:h-24 sm:w-24 text-red-400" />
                  </div>
                </div>
                
                <div className="lg:col-span-2">
                  <div className="text-base text-slate-300 leading-relaxed space-y-4 sm:space-y-6 sm:text-lg">
                    <p>
                      QuantNest wasn't born in a boardroom. It was born from our own trading experiences right here in India. As a solo founder and an active trader, I grew frustrated with the lack of institutional-grade tools available to retail investors.
                    </p>
                    <p>
                      I wanted a platform that was intelligent, data-driven, and built specifically for the nuances of our market. Our mission is simple: to empower every Indian trader with the technology and insights they need to compete and succeed.
                    </p>
                    <p>
                      We're building QuantNest to be the platform we always wanted for ourselves, and we're excited to have you on this journey with us.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* About Us Section */}
        <section id="about" className="py-20 sm:py-24 lg:py-32 bg-black">
          <div className="container px-4 sm:px-6 lg:px-8">
            <div className="mx-auto max-w-3xl text-center mb-16 sm:mb-20">
              <h2 className="text-sm font-semibold leading-7 text-emerald-400 uppercase tracking-wide mb-3 sm:mb-4 section-subtitle">
                Our Story
              </h2>
              <p className="text-3xl font-bold tracking-tight text-slate-100 sm:text-4xl lg:text-5xl mb-4 sm:mb-6 font-heading">
                About QuantNest
              </p>
              <p className="text-base leading-7 text-slate-400 sm:text-lg sm:leading-8">
                At QuantNest, we are driven by a passion for empowering traders with <span className="text-red-300 font-medium">cutting-edge technology</span> and unparalleled insights. Our journey began with a simple idea: to democratize <span className="text-blue-300 font-medium">sophisticated algorithmic trading tools</span>, making them accessible to everyone from individual traders to large institutions.
              </p>
            </div>

            <div className="mx-auto max-w-6xl flex flex-col">
              <div className="grid max-w-xl grid-cols-1 gap-6 lg:max-w-none lg:grid-cols-3 sm:gap-8 mx-auto">
                <div className="text-center p-6 sm:p-8 rounded-3xl bg-gray-900/50 shadow-[inset_0_4px_8px_rgba(255,255,255,0.05),inset_0_-4px_8px_rgba(0,0,0,0.3)] border border-gray-800/50">
                  <div className="flex h-14 w-14 sm:h-16 sm:w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500/20 to-cyan-600/20 shadow-[inset_0_2px_4px_rgba(255,255,255,0.1),inset_0_-2px_4px_rgba(0,0,0,0.2)] mx-auto mb-4 sm:mb-6">
                    <Lightbulb className="h-7 w-7 sm:h-8 sm:w-8 text-blue-400" />
                  </div>
                  <h3 className="text-lg font-semibold text-slate-100 mb-3 sm:text-xl sm:mb-4 font-heading">Our Vision</h3>
                  <p className="text-sm text-slate-400 leading-relaxed sm:text-base">
                    To be the leading platform for algorithmic trading, fostering innovation and success for traders worldwide.
                  </p>
                </div>

                <div className="text-center p-6 sm:p-8 rounded-3xl bg-gray-900/50 shadow-[inset_0_4px_8px_rgba(255,255,255,0.05),inset_0_-4px_8px_rgba(0,0,0,0.3)] border border-gray-800/50">
                  <div className="flex h-14 w-14 sm:h-16 sm:w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-green-500/20 to-emerald-600/20 shadow-[inset_0_2px_4px_rgba(255,255,255,0.1),inset_0_-2px_4px_rgba(0,0,0,0.2)] mx-auto mb-4 sm:mb-6">
                    <Handshake className="h-7 w-7 sm:h-8 sm:w-8 text-green-400" />
                  </div>
                  <h3 className="text-lg font-semibold text-slate-100 mb-3 sm:text-xl sm:mb-4 font-heading">Our Mission</h3>
                  <p className="text-sm text-slate-400 leading-relaxed sm:text-base">
                    To empower traders with intuitive, powerful, and secure tools that simplify complex strategies and maximize potential returns.
                  </p>
                </div>

                <div className="text-center p-6 sm:p-8 rounded-3xl bg-gray-900/50 shadow-[inset_0_4px_8px_rgba(255,255,255,0.05),inset_0_-4px_8px_rgba(0,0,0,0.3)] border border-gray-800/50">
                  <div className="flex h-14 w-14 sm:h-16 sm:w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-red-500/20 to-blue-600/20 shadow-[inset_0_2px_4px_rgba(255,255,255,0.1),inset_0_-2px_4px_rgba(0,0,0,0.2)] mx-auto mb-4 sm:mb-6">
                    <Award className="h-7 w-7 sm:h-8 sm:w-8 text-red-400" />
                  </div>
                  <h3 className="text-lg font-semibold text-slate-100 mb-3 sm:text-xl sm:mb-4 font-heading">Our Values</h3>
                  <p className="text-sm text-slate-400 leading-relaxed sm:text-base">
                    Innovation, Security, Transparency, and User Empowerment are at the core of everything we do.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section id="contact" className="py-20 sm:py-24 lg:py-32 bg-gradient-to-br from-red-900/50 to-blue-900/50">
          <div className="container px-4 sm:px-6 lg:px-8">
            <div className="mx-auto max-w-3xl text-center">
              <h2 className="text-3xl font-bold tracking-tight text-slate-100 sm:text-4xl lg:text-5xl mb-4 sm:mb-6 font-heading">
                Ready to transform your trading?
              </h2>
              <p className="text-base leading-7 text-slate-300 mb-8 sm:mb-12 sm:text-lg">
                Join thousands of professional traders who trust QuantNest for their algorithmic trading needs. Start
                your free trial today and experience the difference.
              </p>
              
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4 sm:gap-6 mb-8 sm:mb-12">
                <Button
                  size="lg"
                  className="bg-gradient-to-r from-red-500 to-blue-600 hover:from-red-600 hover:to-blue-700 text-white shadow-[0_12px_40px_rgba(239,68,68,0.4)] px-8 py-3 text-base font-semibold rounded-2xl sm:px-10 sm:py-4 sm:text-lg"
                >
                  Start Free Trial
                  <ArrowRight className="ml-2 h-4 w-4 sm:h-5 sm:w-5" />
                </Button>
                <Button
                  variant="outline"
                  size="lg"
                  className="text-slate-200 border-slate-500/50 hover:bg-slate-800/50 hover:text-slate-100 bg-slate-800/30 px-8 py-3 text-base font-semibold rounded-2xl shadow-[inset_0_2px_4px_rgba(255,255,255,0.05),inset_0_-2px_4px_rgba(0,0,0,0.3)] sm:px-10 sm:py-4 sm:text-lg"
                >
                  Schedule Demo
                </Button>
              </div>
              
              <div className="flex flex-wrap items-center justify-center space-x-4 text-xs text-slate-400 sm:space-x-8 sm:text-sm">
                <div className="flex items-center">
                  <Lock className="h-3 w-3 mr-1 sm:h-4 sm:w-4 sm:mr-2" />
                  Enterprise Security
                </div>
                <div className="flex items-center">
                  <CheckCircle className="h-3 w-3 mr-1 sm:h-4 w-4 sm:mr-2" />
                  No Credit Card Required
                </div>
                <div className="flex items-center">
                  <Users className="h-3 w-3 mr-1 sm:h-4 w-4 sm:mr-2" />
                  24/7 Expert Support
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-800 bg-black">
        <div className="container px-4 py-12 sm:px-6 lg:px-8 sm:py-16">
          <div className="grid grid-cols-2 gap-8 lg:grid-cols-6 justify-center items-start">
            <div className="col-span-2">
              <div className="flex items-center space-x-2 mb-3 sm:mb-4">
                <div className="flex h-8 w-8 sm:h-9 sm:w-9 items-center justify-center rounded-2xl bg-gradient-to-br from-red-500/20 to-blue-600/20 shadow-[inset_0_2px_4px_rgba(255,255,255,0.1),inset_0_-2px_4px_rgba(0,0,0,0.2)]">
                  <TrendingUp className="h-4 w-4 sm:h-5 sm:w-5 text-red-400" />
                </div>
                <span className="font-bold text-lg sm:text-xl text-slate-100 font-heading">QuantNest</span>
              </div>
              <p className="text-xs text-slate-400 max-w-xs mb-4 sm:mb-6 sm:text-sm">
                The most advanced algorithmic trading platform for professional traders and institutions.
              </p>
              <div className="flex space-x-3 sm:space-x-4">
                <Link to="#" className="text-slate-500 hover:text-slate-300 transition-colors">
                  <span className="sr-only">Twitter</span>
                  <svg className="h-5 w-5 sm:h-6 sm:w-6" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M8.29 20.251c7.547 0 11.675-6.253 11.675-11.675 0-.178 0-.355-.012-.53A8.348 8.348 0 0022 5.92a8.19 8.19 0 01-2.357.646 4.118 4.118 0 001.804-2.27 8.224 8.224 0 01-2.605.996 4.107 4.107 0 00-6.993 3.743 11.65 11.65 0 01-8.457-4.287 4.106 4.106 0 002.8 9.713v.052a4.105 4.105 0 003.292 4.022 4.095 4.095 0 01-1.853.07 4.108 4.108 0 003.834 2.85A8.233 8.233 0 012 18.407a11.616 11.616 0 006.29 1.84" />
                  </svg>
                </Link>
                <Link to="#" className="text-slate-500 hover:text-slate-300 transition-colors">
                  <span className="sr-only">LinkedIn</span>
                  <svg className="h-5 w-5 sm:h-6 sm:w-6" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
                  </svg>
                </Link>
              </div>
            </div>
            
            <div>
              <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wide mb-3 sm:mb-4 font-heading">Product</h3>
              <ul className="space-y-2 text-xs text-slate-400 sm:text-sm">
                <li>
                  <Link to="#" className="hover:text-slate-200 transition-colors">
                    Features
                  </Link>
                </li>
                <li>
                  <Link to="#" className="hover:text-slate-200 transition-colors">
                    Pricing
                  </Link>
                </li>
                <li>
                  <Link to="#" className="hover:text-slate-200 transition-colors">
                    API Documentation
                  </Link>
                </li>
                <li>
                  <Link to="#" className="hover:text-slate-200 transition-colors">
                    Integrations
                  </Link>
                </li>
              </ul>
            </div>
            
            <div>
              <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wide mb-3 sm:mb-4 font-heading">Company</h3>
              <ul className="space-y-2 text-xs text-slate-400 sm:text-sm">
                <li>
                  <Link to="#" className="hover:text-slate-200 transition-colors">
                    About Us
                  </Link>
                </li>
                <li>
                  <Link to="#" className="hover:text-slate-200 transition-colors">
                    Blog
                  </Link>
                </li>
                <li>
                  <Link to="#" className="hover:text-slate-200 transition-colors">
                    Careers
                  </Link>
                </li>
                <li>
                  <Link to="#" className="hover:text-slate-200 transition-colors">
                    Contact
                  </Link>
                </li>
              </ul>
            </div>
            
            <div>
              <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wide mb-3 sm:mb-4 font-heading">Resources</h3>
              <ul className="space-y-2 text-xs text-slate-400 sm:text-sm">
                <li>
                  <Link to="#" className="hover:text-slate-200 transition-colors">
                    Documentation
                  </Link>
                </li>
                <li>
                  <Link to="#" className="hover:text-slate-200 transition-colors">
                    Help Center
                  </Link>
                </li>
                <li>
                  <Link to="#" className="hover:text-slate-200 transition-colors">
                    Community
                  </Link>
                </li>
                <li>
                  <Link to="#" className="hover:text-slate-200 transition-colors">
                    System Status
                  </Link>
                </li>
              </ul>
            </div>
            
            <div>
              <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wide mb-3 sm:mb-4 font-heading">Legal</h3>
              <ul className="space-y-2 text-xs text-slate-400 sm:text-sm">
                <li>
                  <Link to="#" className="hover:text-slate-200 transition-colors">
                    Privacy Policy
                  </Link>
                </li>
                <li>
                  <Link to="#" className="hover:text-slate-200 transition-colors">
                    Terms of Service
                  </Link>
                </li>
                <li>
                  <Link to="#" className="hover:text-slate-200 transition-colors">
                    Security
                  </Link>
                </li>
                <li>
                  <Link to="#" className="hover:text-slate-200 transition-colors">
                    Compliance
                  </Link>
                </li>
              </ul>
            </div>
          </div>
          
          <div className="mt-10 border-t border-gray-800 pt-6 flex flex-col sm:flex-row justify-between items-center sm:pt-8">
            <p className="text-xs text-slate-400 sm:text-sm">
              © {new Date().getFullYear()} QuantNest Technologies Inc. All rights reserved.
            </p>
            <p className="mt-3 sm:mt-0 text-xs text-slate-500">
              Trading involves risk. Past performance does not guarantee future results.
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}
