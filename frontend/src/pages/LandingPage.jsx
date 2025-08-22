import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { TrendingUp, Code2, TestTube2, Rocket, Plug, Shield, BarChart3, Zap, Users, CheckCircle, Star, ArrowRight, Play, Target, Brain, Activity, Globe, Lock, Clock, EyeOff, Lightbulb, Handshake, Award } from 'lucide-react'

// Import animation components
import { StaggeredGrid, StaggeredContainer } from '@/components/ui/staggered-grid'
import { 
  ParallaxLayer, 
  FloatingElement, 
  Transform3D, 
  MouseParallax, 
  HeroBackgroundEffects,
  TiltCard,
  GlowingOrb
} from '@/components/ui/hero-animations'
import { 
  InteractiveButton, 
  HoverCard, 
  AnimatedIcon, 
  GlitchText, 
  ScrollReveal, 
  CounterAnimation
} from '@/components/ui/micro-interactions'
import { 
  SectionTransition, 
  TypewriterEffect, 
  SlideInSection
} from '@/components/ui/loading-transitions'
import { useScrollAnimation } from '@/hooks/use-scroll-animation'

// Import the new MainHeader component
import MainHeader from '@/components/layout/main-header'

export default function QuantNestLanding() {
  const [heroRef] = useScrollAnimation({ animationClass: 'animate-fadeInUp', delay: 300 })
  const [statsRef] = useScrollAnimation({ animationClass: 'animate-fadeInUp', delay: 200 })

  return (
    <div className="flex flex-col min-h-screen bg-black font-sans overflow-x-hidden">
      {/* Header */}
      <MainHeader />

      <main className="flex-1">
        {/* Hero Section with Advanced Animations */}
        <section className="relative overflow-hidden py-12 sm:py-16 md:py-20 lg:py-24 xl:py-32">
          {/* Background Effects */}
          <HeroBackgroundEffects />
          
          {/* Parallax Background Gradients */}
          <ParallaxLayer speed={0.3} className="absolute inset-0">
            <div className="absolute inset-0 bg-gradient-to-br from-black via-gray-900/20 to-black" />
          </ParallaxLayer>
          
          <ParallaxLayer speed={0.5} className="absolute inset-0">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(99,102,241,0.1),transparent_50%)]" />
          </ParallaxLayer>

          <div className="relative z-10">
            <div className="container px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
              <ScrollReveal direction="up" delay={300}>
                <div className="mx-auto max-w-4xl text-center">
                  <FloatingElement animation="breathe" duration={4} delay={0.5}>
                    <div className="mb-4 sm:mb-6 inline-flex items-center rounded-full bg-slate-800/50 px-3 py-1.5 sm:px-4 sm:py-2 md:px-6 md:py-3 shadow-[inset_0_2px_4px_rgba(255,255,255,0.05),inset_0_-2px_4px_rgba(0,0,0,0.3)] border border-gray-700/50 hover-glow">
                      <AnimatedIcon 
                        icon={<Zap className="mr-1.5 sm:mr-2 h-3 w-3 sm:h-4 sm:w-4 text-indigo-400" />}
                        animation="pulse"
                        trigger="hover"
                      />
                      <span className="text-xs sm:text-sm font-medium text-slate-300">Trusted by 50,000+ Professional Traders</span>
                    </div>
                  </FloatingElement>

                  <ScrollReveal direction="up" delay={500}>
                    <h1 className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl xl:text-7xl font-bold tracking-tight text-slate-100 mb-4 sm:mb-6 md:mb-8 font-heading leading-[1.1] sm:leading-tight">
                      Professional
                      <GlitchText 
                        text="Algorithmic Trading"
                        hover={true}
                        className="block text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400 text-gradient-depth py-1 sm:py-2 animate-gradient-shift"
                      />
                      <span className="block text-slate-200">Platform</span>
                    </h1>
                  </ScrollReveal>

                  <ScrollReveal direction="up" delay={700}>
                    <p className="mt-4 sm:mt-6 text-base sm:text-lg lg:text-xl leading-6 sm:leading-7 lg:leading-8 text-slate-400 max-w-2xl lg:max-w-3xl mx-auto">
                      Build, backtest, and deploy sophisticated trading strategies with institutional-grade tools. From
                      paper trading to live execution across multiple asset classes.
                    </p>
                  </ScrollReveal>

                  <ScrollReveal direction="up" delay={900}>
                    <div className="mt-6 sm:mt-8 md:mt-10 flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-4 md:gap-6">
                      <InteractiveButton
                        variant="glow"
                        className="w-full sm:w-auto bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white shadow-[0_12px_40px_rgba(99,102,241,0.4)] px-6 py-2.5 sm:px-8 sm:py-3 md:px-10 md:py-4 text-sm sm:text-base md:text-lg font-semibold rounded-2xl border-0"
                      >
                        Start Free Trial
                        <AnimatedIcon 
                          icon={<ArrowRight className="ml-2 h-4 w-4 sm:h-5 sm:w-5" />}
                          animation="bounce"
                          trigger="hover"
                        />
                      </InteractiveButton>
                      
                      <InteractiveButton
                        variant="magnetic"
                        className="w-full sm:w-auto text-slate-300 border-slate-600/50 hover:bg-slate-800/50 hover:text-slate-100 bg-slate-800/30 px-6 py-2.5 sm:px-8 sm:py-3 md:px-10 md:py-4 text-sm sm:text-base md:text-lg font-semibold rounded-2xl shadow-[inset_0_2px_4px_rgba(255,255,255,0.05),inset_0_-2px_4px_rgba(0,0,0,0.3)] border"
                      >
                        <AnimatedIcon 
                          icon={<Play className="mr-2 h-4 w-4 sm:h-5 sm:w-5" />}
                          animation="spin"
                          trigger="hover"
                        />
                        Watch Demo
                      </InteractiveButton>
                    </div>
                  </ScrollReveal>

                  <ScrollReveal direction="up" delay={1100}>
                    <div className="mt-8 sm:mt-10 md:mt-12 flex flex-wrap items-center justify-center gap-4 sm:gap-6 md:gap-8 text-xs sm:text-sm text-slate-500">
                      <FloatingElement animation="float" duration={6} delay={0}>
                        <div className="flex items-center hover-lift">
                          <Shield className="h-3 w-3 sm:h-4 sm:w-4 mr-1 sm:mr-2" />
                          <span>Enterprise Security</span>
                        </div>
                      </FloatingElement>
                      <FloatingElement animation="float" duration={6} delay={1}>
                        <div className="flex items-center hover-lift">
                          <CheckCircle className="h-3 w-3 sm:h-4 sm:w-4 mr-1 sm:mr-2" />
                          <span>No Credit Card Required</span>
                        </div>
                      </FloatingElement>
                      <FloatingElement animation="float" duration={6} delay={2}>
                        <div className="flex items-center hover-lift">
                          <Clock className="h-3 w-3 sm:h-4 sm:w-4 mr-1 sm:mr-2" />
                          <span>Setup in Minutes</span>
                        </div>
                      </FloatingElement>
                    </div>
                  </ScrollReveal>
                </div>

                <ScrollReveal direction="scale" delay={1300}>
                  <div className="mt-12 sm:mt-16 md:mt-20 lg:mt-24">
                    <MouseParallax strength={0.05}>
                      <TiltCard maxTilt={5} className="relative rounded-2xl sm:rounded-3xl bg-slate-800/30 p-2 sm:p-3 md:p-4 shadow-[inset_0_4px_8px_rgba(255,255,255,0.05),inset_0_-4px_8px_rgba(0,0,0,0.3)] border border-gray-800 backdrop-blur-sm max-w-6xl mx-auto hover-glow">
                        <img
                          src="/placeholder.svg"
                          alt="QuantNest Professional Trading Platform"
                          width={1200}
                          height={600}
                          className="rounded-xl sm:rounded-2xl shadow-2xl w-full h-auto"
                        />
                      </TiltCard>
                    </MouseParallax>
                  </div>
                </ScrollReveal>
              </ScrollReveal>
            </div>
          </div>
        </section>

        {/* Stats Section with Counter Animations */}
        <SectionTransition animation="fadeInUp" delay={200}>
          <section className="py-12 sm:py-16 md:py-20 bg-gray-900/30">
            <div className="container px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
              <StaggeredGrid 
                gridCols="grid-cols-2 lg:grid-cols-4" 
                gap="gap-4 sm:gap-6 md:gap-8"
                staggerDelay={200}
                animationType="scaleIn"
              >
                <HoverCard effect="lift" className="text-center p-4 sm:p-5 md:p-6 rounded-xl sm:rounded-2xl bg-gray-900/50 shadow-[inset_0_2px_4px_rgba(255,255,255,0.05),inset_0_-2px_4px_rgba(0,0,0,0.3)] border border-gray-800/50">
                  <div className="text-2xl sm:text-3xl lg:text-4xl font-bold text-indigo-300 font-heading">
                    <CounterAnimation end={2.5} suffix="B+" />
                  </div>
                  <div className="text-xs sm:text-sm font-medium text-slate-400 mt-1 sm:mt-2">Assets Under Management</div>
                </HoverCard>

                <HoverCard effect="lift" className="text-center p-4 sm:p-5 md:p-6 rounded-xl sm:rounded-2xl bg-gray-900/50 shadow-[inset_0_2px_4px_rgba(255,255,255,0.05),inset_0_-2px_4px_rgba(0,0,0,0.3)] border border-gray-800/50">
                  <div className="text-2xl sm:text-3xl lg:text-4xl font-bold text-purple-300 font-heading">
                    <CounterAnimation end={50} suffix="K+" />
                  </div>
                  <div className="text-xs sm:text-sm font-medium text-slate-400 mt-1 sm:mt-2">Active Traders</div>
                </HoverCard>

                <HoverCard effect="lift" className="text-center p-4 sm:p-5 md:p-6 rounded-xl sm:rounded-2xl bg-gray-900/50 shadow-[inset_0_2px_4px_rgba(255,255,255,0.05),inset_0_-2px_4px_rgba(0,0,0,0.3)] border border-gray-800/50">
                  <div className="text-2xl sm:text-3xl lg:text-4xl font-bold text-pink-300 font-heading">
                    <CounterAnimation end={99.99} suffix="%" />
                  </div>
                  <div className="text-xs sm:text-sm font-medium text-slate-400 mt-1 sm:mt-2">System Uptime</div>
                </HoverCard>

                <HoverCard effect="lift" className="text-center p-4 sm:p-5 md:p-6 rounded-xl sm:rounded-2xl bg-gray-900/50 shadow-[inset_0_2px_4px_rgba(255,255,255,0.05),inset_0_-2px_4px_rgba(0,0,0,0.3)] border border-gray-800/50">
                  <div className="text-2xl sm:text-3xl lg:text-4xl font-bold text-cyan-300 font-heading">
                    <CounterAnimation end={15} suffix="+" />
                  </div>
                  <div className="text-xs sm:text-sm font-medium text-slate-400 mt-1 sm:mt-2">Broker Integrations</div>
                </HoverCard>
              </StaggeredGrid>
            </div>
          </section>
        </SectionTransition>

        {/* Features Overview with Staggered Animations */}
        <SectionTransition animation="fadeInUp" delay={300}>
          <section id="features" className="section-padding-lg bg-black relative overflow-hidden">
            {/* Background Elements */}
            <FloatingElement animation="rotate" duration={20} className="absolute top-20 right-20 opacity-10">
              <div className="w-32 h-32 border border-indigo-500/20 rounded-2xl" />
            </FloatingElement>
            
            <div className="container container-padding max-w-7xl mx-auto relative z-10">
              <ScrollReveal direction="up" delay={200}>
                <div className="mx-auto max-w-3xl text-center mb-12 sm:mb-16 md:mb-20">
                  <h2 className="text-sm font-semibold leading-7 text-indigo-400 uppercase tracking-wide mb-3 sm:mb-4 section-subtitle">
                    Complete Trading Suite
                  </h2>
                  <p className="text-2xl sm:text-3xl md:text-4xl lg:text-5xl font-bold tracking-tight text-slate-100 mb-4 sm:mb-6 font-heading">
                    <TypewriterEffect 
                      words={["Everything you need for algorithmic trading", "Professional tools for serious traders", "Built by traders, for traders"]}
                      speed={80}
                      delay={3000}
                      loop={true}
                    />
                  </p>
                  <p className="text-base leading-7 text-slate-400 sm:text-lg sm:leading-8">
                    Professional-grade tools designed for traders, by traders. From strategy development to live execution
                    with institutional-level infrastructure.
                  </p>
                </div>
              </ScrollReveal>
              
              <div className="mx-auto max-w-7xl">
                <StaggeredGrid 
                  gridCols="grid-cols-1 md:grid-cols-2 lg:grid-cols-3" 
                  gap="gap-6 sm:gap-8 xl:gap-10"
                  staggerDelay={150}
                  animationType="fadeInUp"
                >
                  <TiltCard className="relative overflow-hidden rounded-2xl sm:rounded-3xl bg-gray-900/50 shadow-[inset_0_4px_8px_rgba(255,255,255,0.05),inset_0_-4px_8px_rgba(0,0,0,0.3)] border border-gray-800/50 p-6 sm:p-8 hover-glow">
                    <div className="flex items-center justify-between mb-4 sm:mb-6">
                      <FloatingElement animation="breathe" duration={4}>
                        <div className="flex h-12 w-12 sm:h-14 sm:w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-500/20 to-teal-600/20 shadow-[inset_0_2px_4px_rgba(255,255,255,0.1),inset_0_-2px_4px_rgba(0,0,0,0.2)]">
                          <Target className="h-6 w-6 sm:h-7 sm:w-7 text-emerald-400" />
                        </div>
                      </FloatingElement>
                      <div className="rounded-full bg-emerald-500/20 px-2 py-1 text-xs font-medium text-emerald-300 border border-emerald-500/30 animate-pulse">
                        Risk-Free
                      </div>
                    </div>
                    <h3 className="text-lg font-semibold text-slate-100 mb-2 sm:text-xl sm:mb-3 font-heading">Paper Trading</h3>
                    <p className="text-sm text-slate-400 sm:text-base">
                      Master your strategies with unlimited paper trading using real-time market data and realistic
                      execution modeling.
                    </p>
                  </TiltCard>

                  <TiltCard className="relative overflow-hidden rounded-2xl sm:rounded-3xl bg-gray-900/50 shadow-[inset_0_4px_8px_rgba(255,255,255,0.05),inset_0_-4px_8px_rgba(0,0,0,0.3)] border border-gray-800/50 p-6 sm:p-8 hover-glow">
                    <div className="flex items-center justify-between mb-4 sm:mb-6">
                      <FloatingElement animation="breathe" duration={5} delay={1}>
                        <div className="flex h-12 w-12 sm:h-14 sm:w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-purple-500/20 to-indigo-600/20 shadow-[inset_0_2px_4px_rgba(255,255,255,0.1),inset_0_-2px_4px_rgba(0,0,0,0.2)]">
                          <Code2 className="h-6 w-6 sm:h-7 sm:w-7 text-purple-400" />
                        </div>
                      </FloatingElement>
                      <div className="rounded-full bg-purple-500/20 px-2 py-1 text-xs font-medium text-purple-300 border border-purple-500/30 animate-pulse">
                        AI-Powered
                      </div>
                    </div>
                    <h3 className="text-lg font-semibold text-slate-100 mb-2 sm:text-xl sm:mb-3 font-heading">Strategy Builder</h3>
                    <p className="text-sm text-slate-400 sm:text-base">
                      Build sophisticated algorithms with visual tools or code in Python, JavaScript, and Pine Script
                      with AI assistance.
                    </p>
                  </TiltCard>

                  <TiltCard className="relative overflow-hidden rounded-2xl sm:rounded-3xl bg-gray-900/50 shadow-[inset_0_4px_8px_rgba(255,255,255,0.05),inset_0_-4px_8px_rgba(0,0,0,0.3)] border border-gray-800/50 p-6 sm:p-8 hover-glow">
                    <div className="flex items-center justify-between mb-4 sm:mb-6">
                      <FloatingElement animation="breathe" duration={4.5} delay={0.5}>
                        <div className="flex h-12 w-12 sm:h-14 sm:w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-orange-500/20 to-red-600/20 shadow-[inset_0_2px_4px_rgba(255,255,255,0.1),inset_0_-2px_4px_rgba(0,0,0,0.2)]">
                          <TestTube2 className="h-6 w-6 sm:h-7 sm:w-7 text-orange-400" />
                        </div>
                      </FloatingElement>
                      <div className="rounded-full bg-orange-500/20 px-2 py-1 text-xs font-medium text-orange-300 border border-orange-500/30 animate-pulse">
                        Institutional
                      </div>
                    </div>
                    <h3 className="text-lg font-semibold text-slate-100 mb-2 sm:text-xl sm:mb-3 font-heading">Advanced Backtesting</h3>
                    <p className="text-sm text-slate-400 sm:text-base">
                      Validate strategies with tick-level precision, realistic costs, and comprehensive risk analytics
                      across years of data.
                    </p>
                  </TiltCard>

                  <TiltCard className="relative overflow-hidden rounded-2xl sm:rounded-3xl bg-gray-900/50 shadow-[inset_0_4px_8px_rgba(255,255,255,0.05),inset_0_-4px_8px_rgba(0,0,0,0.3)] border border-gray-800/50 p-6 sm:p-8 hover-glow">
                    <div className="flex items-center justify-between mb-4 sm:mb-6">
                      <FloatingElement animation="breathe" duration={3.5} delay={1.5}>
                        <div className="flex h-12 w-12 sm:h-14 sm:w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-green-500/20 to-emerald-600/20 shadow-[inset_0_2px_4px_rgba(255,255,255,0.1),inset_0_-2px_4px_rgba(0,0,0,0.2)]">
                          <Rocket className="h-6 w-6 sm:h-7 sm:w-7 text-green-400" />
                        </div>
                      </FloatingElement>
                      <div className="rounded-full bg-green-500/20 px-2 py-1 text-xs font-medium text-green-300 border border-green-500/30 animate-neon-glow">
                        Live
                      </div>
                    </div>
                    <h3 className="text-lg font-semibold text-slate-100 mb-2 sm:text-xl sm:mb-3 font-heading">Live Deployment</h3>
                    <p className="text-sm text-slate-400 sm:text-base">
                      Deploy proven strategies to live markets with one-click execution, real-time monitoring, and
                      automatic risk management.
                    </p>
                  </TiltCard>

                  <TiltCard className="relative overflow-hidden rounded-2xl sm:rounded-3xl bg-gray-900/50 shadow-[inset_0_4px_8px_rgba(255,255,255,0.05),inset_0_-4px_8px_rgba(0,0,0,0.3)] border border-gray-800/50 p-6 sm:p-8 hover-glow">
                    <div className="flex items-center justify-between mb-4 sm:mb-6">
                      <FloatingElement animation="breathe" duration={5.5} delay={0.8}>
                        <div className="flex h-12 w-12 sm:h-14 sm:w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500/20 to-cyan-600/20 shadow-[inset_0_2px_4px_rgba(255,255,255,0.1),inset_0_-2px_4px_rgba(0,0,0,0.2)]">
                          <Plug className="h-6 w-6 sm:h-7 sm:w-7 text-blue-400" />
                        </div>
                      </FloatingElement>
                      <div className="rounded-full bg-blue-500/20 px-2 py-1 text-xs font-medium text-blue-300 border border-blue-500/30 animate-pulse">
                        Multi-Broker
                      </div>
                    </div>
                    <h3 className="text-lg font-semibold text-slate-100 mb-2 sm:text-xl sm:mb-3 font-heading">Broker Integration</h3>
                    <p className="text-sm text-slate-400 sm:text-base">
                      Connect to 15+ major brokers including Interactive Brokers, TD Ameritrade, and Alpaca with secure
                      API connections.
                    </p>
                  </TiltCard>

                  <TiltCard className="relative overflow-hidden rounded-2xl sm:rounded-3xl bg-gray-900/50 shadow-[inset_0_4px_8px_rgba(255,255,255,0.05),inset_0_-4px_8px_rgba(0,0,0,0.3)] border border-gray-800/50 p-6 sm:p-8 hover-glow">
                    <div className="flex items-center justify-between mb-4 sm:mb-6">
                      <FloatingElement animation="breathe" duration={4.2} delay={1.2}>
                        <div className="flex h-12 w-12 sm:h-14 sm:w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500/20 to-purple-600/20 shadow-[inset_0_2px_4px_rgba(255,255,255,0.1),inset_0_-2px_4px_rgba(0,0,0,0.2)]">
                          <BarChart3 className="h-6 w-6 sm:h-7 sm:w-7 text-indigo-400" />
                        </div>
                      </FloatingElement>
                      <div className="rounded-full bg-indigo-500/20 px-2 py-1 text-xs font-medium text-indigo-300 border border-indigo-500/30 animate-pulse">
                        Analytics
                      </div>
                    </div>
                    <h3 className="text-lg font-semibold text-slate-100 mb-2 sm:text-xl sm:mb-3 font-heading">Performance Analytics</h3>
                    <p className="text-sm text-slate-400 sm:text-base">
                      Comprehensive performance tracking with Sharpe ratio, drawdown analysis, alpha, beta, and custom
                      risk metrics.
                    </p>
                  </TiltCard>
                </StaggeredGrid>
              </div>
            </div>
          </section>
        </SectionTransition>

        {/* How It Works Section with Advanced Animations */}
        <SectionTransition animation="fadeInUp" delay={400}>
          <section className="py-20 sm:py-24 lg:py-32 bg-gray-900/30 relative overflow-hidden">
            <ParallaxLayer speed={0.2} className="absolute inset-0">
              <GlowingOrb
                color="rgba(139, 92, 246, 0.1)"
                size={400}
                className="top-1/2 left-1/4 animate-float"
                animate={true}
              />
            </ParallaxLayer>

            <div className="container px-4 sm:px-6 lg:px-8 relative z-10">
              <ScrollReveal direction="up" delay={200}>
                <div className="mx-auto max-w-3xl text-center mb-16 sm:mb-20">
                  <h2 className="text-sm font-semibold leading-7 text-indigo-400 uppercase tracking-wide mb-3 sm:mb-4 section-subtitle">
                    Simple Process
                  </h2>
                  <p className="text-3xl font-bold tracking-tight text-slate-100 sm:text-4xl lg:text-5xl mb-4 sm:mb-6 font-heading">
                    How It Works
                  </p>
                  <p className="text-base leading-7 text-slate-400 sm:text-lg sm:leading-8">
                    Get started with algorithmic trading in three simple steps. No complex setup required.
                  </p>
                </div>
              </ScrollReveal>

              <div className="mx-auto max-w-5xl flex flex-col">
                <StaggeredGrid 
                  gridCols="grid-cols-1 lg:grid-cols-3" 
                  gap="gap-8 sm:gap-12"
                  staggerDelay={300}
                  animationType="scaleIn"
                >
                  <MouseParallax strength={0.1}>
                    <HoverCard effect="tilt" className="relative text-center p-4">
                      <FloatingElement animation="float" duration={6} delay={0}>
                        <div className="flex h-16 w-16 sm:h-20 sm:w-20 items-center justify-center rounded-3xl bg-gradient-to-br from-indigo-500/20 to-purple-600/20 shadow-[inset_0_4px_8px_rgba(255,255,255,0.1),inset_0_-2px_4px_rgba(0,0,0,0.2)] border border-indigo-500/30 mx-auto mb-6 sm:mb-8 hover-glow">
                          <Brain className="h-8 w-8 sm:h-10 sm:w-10 text-indigo-400" />
                        </div>
                      </FloatingElement>
                      <div className="absolute -top-2 -right-2 bg-gradient-to-r from-indigo-500 to-purple-600 text-white text-sm font-bold rounded-full w-7 h-7 sm:w-8 sm:h-8 flex items-center justify-center animate-bounce">
                        1
                      </div>
                      <h3 className="text-xl font-bold text-slate-100 mb-3 sm:text-2xl sm:mb-4 font-heading">Discover with AI</h3>
                      <p className="text-sm text-slate-400 leading-relaxed sm:text-lg">
                        Get personalized stock picks, news summaries, and market analysis from your personal AI research assistant.
                      </p>
                    </HoverCard>
                  </MouseParallax>

                  <MouseParallax strength={0.1}>
                    <HoverCard effect="tilt" className="relative text-center p-4">
                      <FloatingElement animation="float" duration={7} delay={1}>
                        <div className="flex h-16 w-16 sm:h-20 sm:w-20 items-center justify-center rounded-3xl bg-gradient-to-br from-emerald-500/20 to-teal-600/20 shadow-[inset_0_4px_8px_rgba(255,255,255,0.1),inset_0_-2px_4px_rgba(0,0,0,0.2)] border border-emerald-500/30 mx-auto mb-6 sm:mb-8 hover-glow">
                          <Code2 className="h-8 w-8 sm:h-10 sm:w-10 text-emerald-400" />
                        </div>
                      </FloatingElement>
                      <div className="absolute -top-2 -right-2 bg-gradient-to-r from-emerald-500 to-teal-600 text-white text-sm font-bold rounded-full w-7 h-7 sm:w-8 sm:h-8 flex items-center justify-center animate-bounce" style={{ animationDelay: '0.2s' }}>
                        2
                      </div>
                      <h3 className="text-xl font-bold text-slate-100 mb-3 sm:text-2xl sm:mb-4 font-heading">Build & Backtest</h3>
                      <p className="text-sm text-slate-400 leading-relaxed sm:text-lg">
                        Use our simple drag-and-drop interface to build a trading strategy based on indicators and logic. No coding required. Backtest it instantly on historical data.
                      </p>
                    </HoverCard>
                  </MouseParallax>

                  <MouseParallax strength={0.1}>
                    <HoverCard effect="tilt" className="relative text-center p-4">
                      <FloatingElement animation="float" duration={8} delay={2}>
                        <div className="flex h-16 w-16 sm:h-20 sm:w-20 items-center justify-center rounded-3xl bg-gradient-to-br from-orange-500/20 to-red-600/20 shadow-[inset_0_4px_8px_rgba(255,255,255,0.1),inset_0_-2px_4px_rgba(0,0,0,0.2)] border border-orange-500/30 mx-auto mb-6 sm:mb-8 hover-glow">
                          <Rocket className="h-8 w-8 sm:h-10 sm:w-10 text-orange-400" />
                        </div>
                      </FloatingElement>
                      <div className="absolute -top-2 -right-2 bg-gradient-to-r from-orange-500 to-red-600 text-white text-sm font-bold rounded-full w-7 h-7 sm:w-8 sm:h-8 flex items-center justify-center animate-bounce" style={{ animationDelay: '0.4s' }}>
                        3
                      </div>
                      <h3 className="text-xl font-bold text-slate-100 mb-3 sm:text-2xl sm:mb-4 font-heading">Deploy with Confidence</h3>
                      <p className="text-sm text-slate-400 leading-relaxed sm:text-lg">
                        Practice your strategy in our risk-free paper trading environment with real-time market data. When you're ready, connect your broker and deploy it live.
                      </p>
                    </HoverCard>
                  </MouseParallax>
                </StaggeredGrid>
              </div>
            </div>
          </section>
        </SectionTransition>

        {/* Testimonials with Advanced Effects */}
        <SectionTransition animation="fadeInUp" delay={500}>
          <section className="py-20 sm:py-24 lg:py-32 bg-gray-900/30">
            <div className="container px-4 sm:px-6 lg:px-8">
              <ScrollReveal direction="up" delay={200}>
                <div className="mx-auto max-w-3xl text-center mb-16 sm:mb-20">
                  <h2 className="text-3xl font-bold tracking-tight text-slate-100 sm:text-4xl lg:text-5xl mb-4 sm:mb-6 font-heading">
                    Trusted by professionals worldwide
                  </h2>
                  <p className="text-base leading-7 text-slate-400 sm:text-lg sm:leading-8">
                    See what traders and institutions are saying about QuantNest
                  </p>
                </div>
              </ScrollReveal>
              
              <StaggeredGrid 
                gridCols="grid-cols-1 lg:grid-cols-3" 
                gap="gap-6 sm:gap-8"
                staggerDelay={200}
                animationType="fadeInUp"
              >
                <TiltCard className="rounded-3xl bg-gray-900/50 shadow-[inset_0_4px_8px_rgba(255,255,255,0.05),inset_0_-4px_8px_rgba(0,0,0,0.3)] border border-gray-800/50 p-6 sm:p-8 hover-glow">
                  <div className="flex items-center mb-4 sm:mb-6">
                    {[...Array(5)].map((_, i) => (
                      <AnimatedIcon
                        key={i}
                        icon={<Star className="h-4 w-4 sm:h-5 sm:w-5 fill-yellow-400 text-yellow-400" />}
                        animation="bounce"
                        trigger="hover"
                      />
                    ))}
                  </div>
                  <p className="text-base text-slate-300 mb-4 sm:mb-6 sm:text-lg leading-relaxed testimonial-quote">
                    "QuantNest's backtesting engine is incredibly sophisticated. The tick-level precision and realistic
                    cost modeling helped me optimize my strategies before going live."
                  </p>
                  <div className="flex items-center">
                    <FloatingElement animation="breathe" duration={4}>
                      <div className="h-10 w-10 sm:h-12 sm:w-12 rounded-2xl bg-gradient-to-br from-blue-500/20 to-cyan-600/20 flex items-center justify-center text-white font-semibold shadow-[inset_0_2px_4px_rgba(255,255,255,0.1),inset_0_-2px_4px_rgba(0,0,0,0.2)] text-sm sm:text-base">
                        SC
                      </div>
                    </FloatingElement>
                    <div className="ml-3 sm:ml-4">
                      <p className="text-sm font-semibold text-slate-200">Sarah Chen</p>
                      <p className="text-xs text-slate-400">Senior Quantitative Trader, Citadel</p>
                    </div>
                  </div>
                </TiltCard>

                <TiltCard className="rounded-3xl bg-gray-900/50 shadow-[inset_0_4px_8px_rgba(255,255,255,0.05),inset_0_-4px_8px_rgba(0,0,0,0.3)] border border-gray-800/50 p-6 sm:p-8 hover-glow">
                  <div className="flex items-center mb-4 sm:mb-6">
                    {[...Array(5)].map((_, i) => (
                      <AnimatedIcon
                        key={i}
                        icon={<Star className="h-4 w-4 sm:h-5 sm:w-5 fill-yellow-400 text-yellow-400" />}
                        animation="bounce"
                        trigger="hover"
                      />
                    ))}
                  </div>
                  <p className="text-base text-slate-300 mb-4 sm:mb-6 sm:text-lg leading-relaxed testimonial-quote">
                    "The broker integrations are seamless and the execution is lightning fast. We've deployed multiple
                    strategies across different asset classes without any issues."
                  </p>
                  <div className="flex items-center">
                    <FloatingElement animation="breathe" duration={5} delay={1}>
                      <div className="h-10 w-10 sm:h-12 sm:w-12 rounded-2xl bg-gradient-to-br from-emerald-500/20 to-teal-600/20 flex items-center justify-center text-white font-semibold shadow-[inset_0_2px_4px_rgba(255,255,255,0.1),inset_0_-2px_4px_rgba(0,0,0,0.2)] text-sm sm:text-base">
                        MR
                      </div>
                    </FloatingElement>
                    <div className="ml-3 sm:ml-4">
                      <p className="text-sm font-semibold text-slate-200">Michael Rodriguez</p>
                      <p className="text-xs text-slate-400">Portfolio Manager, Two Sigma</p>
                    </div>
                  </div>
                </TiltCard>

                <TiltCard className="rounded-3xl bg-gray-900/50 shadow-[inset_0_4px_8px_rgba(255,255,255,0.05),inset_0_-4px_8px_rgba(0,0,0,0.3)] border border-gray-800/50 p-6 sm:p-8 hover-glow">
                  <div className="flex items-center mb-4 sm:mb-6">
                    {[...Array(5)].map((_, i) => (
                      <AnimatedIcon
                        key={i}
                        icon={<Star className="h-4 w-4 sm:h-5 sm:w-5 fill-yellow-400 text-yellow-400" />}
                        animation="bounce"
                        trigger="hover"
                      />
                    ))}
                  </div>
                  <p className="text-base text-slate-300 mb-4 sm:mb-6 sm:text-lg leading-relaxed testimonial-quote">
                    "Started with paper trading and now managing a profitable portfolio. The learning curve was smooth
                    thanks to the intuitive interface and excellent documentation."
                  </p>
                  <div className="flex items-center">
                    <FloatingElement animation="breathe" duration={4.5} delay={0.5}>
                      <div className="h-10 w-10 sm:h-12 sm:w-12 rounded-2xl bg-gradient-to-br from-purple-500/20 to-pink-600/20 flex items-center justify-center text-white font-semibold shadow-[inset_0_2px_4px_rgba(255,255,255,0.1),inset_0_-2px_4px_rgba(0,0,0,0.2)] text-sm sm:text-base">
                        DK
                      </div>
                    </FloatingElement>
                    <div className="ml-3 sm:ml-4">
                      <p className="text-sm font-semibold text-slate-200">David Kim</p>
                      <p className="text-xs text-slate-400">Independent Trader</p>
                    </div>
                  </div>
                </TiltCard>
              </StaggeredGrid>
            </div>
          </section>
        </SectionTransition>

        {/* CTA Section with Advanced Animations */}
        <SectionTransition animation="fadeInUp" delay={600}>
          <section id="contact" className="py-20 sm:py-24 lg:py-32 bg-gradient-to-br from-indigo-900/50 to-purple-900/50 relative overflow-hidden">
            <ParallaxLayer speed={0.3}>
              <div className="absolute inset-0 animate-gradient-shift opacity-30" />
            </ParallaxLayer>
            
            <div className="container px-4 sm:px-6 lg:px-8 relative z-10">
              <ScrollReveal direction="up" delay={200}>
                <div className="mx-auto max-w-3xl text-center">
                  <h2 className="text-3xl font-bold tracking-tight text-slate-100 sm:text-4xl lg:text-5xl mb-4 sm:mb-6 font-heading">
                    Ready to transform your trading?
                  </h2>
                  <p className="text-base leading-7 text-slate-300 mb-8 sm:mb-12 sm:text-lg">
                    Join thousands of professional traders who trust QuantNest for their algorithmic trading needs. Start
                    your free trial today and experience the difference.
                  </p>
                  
                  <div className="flex flex-col sm:flex-row items-center justify-center gap-4 sm:gap-6 mb-8 sm:mb-12">
                    <InteractiveButton
                      variant="glow"
                      className="bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white shadow-[0_12px_40px_rgba(99,102,241,0.4)] px-8 py-3 text-base font-semibold rounded-2xl sm:px-10 sm:py-4 sm:text-lg"
                    >
                      Start Free Trial
                      <AnimatedIcon 
                        icon={<ArrowRight className="ml-2 h-4 w-4 sm:h-5 sm:w-5" />}
                        animation="bounce"
                        trigger="hover"
                      />
                    </InteractiveButton>
                    
                    <InteractiveButton
                      variant="magnetic"
                      className="text-slate-200 border-slate-500/50 hover:bg-slate-800/50 hover:text-slate-100 bg-slate-800/30 px-8 py-3 text-base font-semibold rounded-2xl shadow-[inset_0_2px_4px_rgba(255,255,255,0.05),inset_0_-2px_4px_rgba(0,0,0,0.3)] sm:px-10 sm:py-4 sm:text-lg border"
                    >
                      Schedule Demo
                    </InteractiveButton>
                  </div>
                  
                  <StaggeredContainer 
                    staggerDelay={100}
                    animationType="fadeInUp"
                    className="flex flex-wrap items-center justify-center space-x-4 text-xs text-slate-400 sm:space-x-8 sm:text-sm"
                  >
                    <div className="flex items-center hover-lift">
                      <Lock className="h-3 w-3 mr-1 sm:h-4 sm:w-4 sm:mr-2" />
                      Enterprise Security
                    </div>
                    <div className="flex items-center hover-lift">
                      <CheckCircle className="h-3 w-3 mr-1 sm:h-4 w-4 sm:mr-2" />
                      No Credit Card Required
                    </div>
                    <div className="flex items-center hover-lift">
                      <Users className="h-3 w-3 mr-1 sm:h-4 w-4 sm:mr-2" />
                      24/7 Expert Support
                    </div>
                  </StaggeredContainer>
                </div>
              </ScrollReveal>
            </div>
          </section>
        </SectionTransition>
      </main>

      {/* Footer */}
      <SectionTransition animation="fadeInUp" delay={700}>
        <footer className="border-t border-gray-800 bg-black">
          <div className="container px-4 py-12 sm:px-6 lg:px-8 sm:py-16">
            <div className="grid grid-cols-2 gap-8 lg:grid-cols-6 justify-center items-start">
              <ScrollReveal direction="up" delay={100}>
                <div className="col-span-2">
                  <div className="flex items-center space-x-2 mb-3 sm:mb-4">
                    <FloatingElement animation="breathe" duration={4}>
                      <div className="flex h-8 w-8 sm:h-9 sm:w-9 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500/20 to-purple-600/20 shadow-[inset_0_2px_4px_rgba(255,255,255,0.1),inset_0_-2px_4px_rgba(0,0,0,0.2)]">
                        <TrendingUp className="h-4 w-4 sm:h-5 sm:w-5 text-indigo-400" />
                      </div>
                    </FloatingElement>
                    <span className="font-bold text-lg sm:text-xl text-slate-100 font-heading">QuantNest</span>
                  </div>
                  <p className="text-xs text-slate-400 max-w-xs mb-4 sm:mb-6 sm:text-sm">
                    The most advanced algorithmic trading platform for professional traders and institutions.
                  </p>
                  <div className="flex space-x-3 sm:space-x-4">
                    <InteractiveButton variant="magnetic" className="text-slate-500 hover:text-slate-300 transition-colors p-2">
                      <span className="sr-only">Twitter</span>
                      <svg className="h-5 w-5 sm:h-6 sm:w-6" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M8.29 20.251c7.547 0 11.675-6.253 11.675-11.675 0-.178 0-.355-.012-.53A8.348 8.348 0 0022 5.92a8.19 8.19 0 01-2.357.646 4.118 4.118 0 001.804-2.27 8.224 8.224 0 01-2.605.996 4.107 4.107 0 00-6.993 3.743 11.65 11.65 0 01-8.457-4.287 4.106 4.106 0 002.8 9.713v.052a4.105 4.105 0 003.292 4.022 4.095 4.095 0 01-1.853.07 4.108 4.108 0 003.834 2.85A8.233 8.233 0 012 18.407a11.616 11.616 0 006.29 1.84" />
                      </svg>
                    </InteractiveButton>
                    <InteractiveButton variant="magnetic" className="text-slate-500 hover:text-slate-300 transition-colors p-2">
                      <span className="sr-only">LinkedIn</span>
                      <svg className="h-5 w-5 sm:h-6 sm:w-6" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
                      </svg>
                    </InteractiveButton>
                  </div>
                </div>
              </ScrollReveal>
              
              <StaggeredContainer staggerDelay={100} className="space-y-2">
                <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wide mb-3 sm:mb-4 font-heading">Product</h3>
                <ul className="space-y-2 text-xs text-slate-400 sm:text-sm">
                  <li><Link to="#" className="hover:text-slate-200 transition-colors hover-lift">Features</Link></li>
                  <li><Link to="#" className="hover:text-slate-200 transition-colors hover-lift">Pricing</Link></li>
                  <li><Link to="#" className="hover:text-slate-200 transition-colors hover-lift">API Documentation</Link></li>
                  <li><Link to="#" className="hover:text-slate-200 transition-colors hover-lift">Integrations</Link></li>
                </ul>
              </StaggeredContainer>
              
              <StaggeredContainer staggerDelay={150} className="space-y-2">
                <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wide mb-3 sm:mb-4 font-heading">Company</h3>
                <ul className="space-y-2 text-xs text-slate-400 sm:text-sm">
                  <li><Link to="#" className="hover:text-slate-200 transition-colors hover-lift">About Us</Link></li>
                  <li><Link to="#" className="hover:text-slate-200 transition-colors hover-lift">Blog</Link></li>
                  <li><Link to="#" className="hover:text-slate-200 transition-colors hover-lift">Careers</Link></li>
                  <li><Link to="#" className="hover:text-slate-200 transition-colors hover-lift">Contact</Link></li>
                </ul>
              </StaggeredContainer>
              
              <StaggeredContainer staggerDelay={200} className="space-y-2">
                <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wide mb-3 sm:mb-4 font-heading">Resources</h3>
                <ul className="space-y-2 text-xs text-slate-400 sm:text-sm">
                  <li><Link to="#" className="hover:text-slate-200 transition-colors hover-lift">Documentation</Link></li>
                  <li><Link to="#" className="hover:text-slate-200 transition-colors hover-lift">Help Center</Link></li>
                  <li><Link to="#" className="hover:text-slate-200 transition-colors hover-lift">Community</Link></li>
                  <li><Link to="#" className="hover:text-slate-200 transition-colors hover-lift">System Status</Link></li>
                </ul>
              </StaggeredContainer>
              
              <StaggeredContainer staggerDelay={250} className="space-y-2">
                <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wide mb-3 sm:mb-4 font-heading">Legal</h3>
                <ul className="space-y-2 text-xs text-slate-400 sm:text-sm">
                  <li><Link to="#" className="hover:text-slate-200 transition-colors hover-lift">Privacy Policy</Link></li>
                  <li><Link to="#" className="hover:text-slate-200 transition-colors hover-lift">Terms of Service</Link></li>
                  <li><Link to="#" className="hover:text-slate-200 transition-colors hover-lift">Security</Link></li>
                  <li><Link to="#" className="hover:text-slate-200 transition-colors hover-lift">Compliance</Link></li>
                </ul>
              </StaggeredContainer>
            </div>
            
            <ScrollReveal direction="up" delay={400}>
              <div className="mt-10 border-t border-gray-800 pt-6 flex flex-col sm:flex-row justify-between items-center sm:pt-8">
                <p className="text-xs text-slate-400 sm:text-sm">
                  © {new Date().getFullYear()} QuantNest Technologies Inc. All rights reserved.
                </p>
                <p className="mt-3 sm:mt-0 text-xs text-slate-500">
                  Trading involves risk. Past performance does not guarantee future results.
                </p>
              </div>
            </ScrollReveal>
          </div>
        </footer>
      </SectionTransition>
    </div>
  )
}
