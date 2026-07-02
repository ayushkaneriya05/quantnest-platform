/* eslint-disable react/prop-types */
import React, { useState } from "react";
import { Link } from "react-router-dom";
import {
  Activity,
  ArrowRight,
  BookOpenCheck,
  BrainCircuit,
  Check,
  ChevronRight,
  ClipboardCheck,
  FlaskConical,
  Gauge,
  GraduationCap,
  Layers3,
  LineChart,
  LockKeyhole,
  Radio,
  Rocket,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Store,
  Terminal,
  Users,
} from "lucide-react";

import MainHeader from "@/shared/components/layout/main-header";
import { Button } from "@/shared/components/ui/button";

const workflow = [
  {
    number: "01",
    icon: BrainCircuit,
    title: "Research with AI",
    description:
      "Ask questions, screen the market, compare symbols, and collect context before you build a strategy.",
    benefit: "Go from scattered market ideas to a clear trading thesis.",
  },
  {
    number: "02",
    icon: SlidersHorizontal,
    title: "Make the strategy",
    description:
      "Define entries, exits, time windows, instruments, position sizing, stop-loss, targets, and risk rules.",
    benefit: "Turn your idea into rules you can inspect and improve.",
  },
  {
    number: "03",
    icon: FlaskConical,
    title: "Backtest before risking capital",
    description:
      "Run the strategy on historical candles, review trades, equity, drawdown, metrics, and Monte Carlo scenarios.",
    benefit: "Understand how the strategy behaves before you deploy it.",
  },
  {
    number: "04",
    icon: Activity,
    title: "Deploy to paper trading",
    description:
      "Run the strategy in a simulated portfolio and track positions, orders, capital, and performance.",
    benefit: "Practice execution with market-like workflow and zero real capital risk.",
  },
  {
    number: "05",
    icon: Rocket,
    title: "Move to live trading",
    description:
      "Connect broker accounts, allocate capital, monitor live sessions, inspect logs, and use emergency controls.",
    benefit: "Operate live strategies with visibility and risk controls.",
  },
];

const platformFeatures = [
  {
    icon: Search,
    eyebrow: "AI research",
    title: "Find better trading ideas",
    description:
      "Use AI-assisted research, market screening, live quotes, and alternative data to decide what is worth testing.",
    accent: "from-violet-500/20 to-indigo-500/5",
    iconColor: "text-violet-300",
  },
  {
    icon: SlidersHorizontal,
    eyebrow: "Strategy builder",
    title: "Build without guessing",
    description:
      "Create structured rules for when to enter, when to exit, how much to trade, and when to stop the strategy.",
    accent: "from-indigo-500/20 to-purple-500/5",
    iconColor: "text-indigo-300",
  },
  {
    icon: LineChart,
    eyebrow: "Backtesting",
    title: "Test the plan first",
    description:
      "See trade-by-trade results, equity curve, drawdown, risk metrics, and Monte Carlo analysis before deployment.",
    accent: "from-sky-500/20 to-cyan-500/5",
    iconColor: "text-sky-300",
  },
  {
    icon: Activity,
    eyebrow: "Paper strategy deployment",
    title: "Run strategies safely",
    description:
      "Deploy strategies to paper accounts, follow orders and positions, manage capital, and review performance.",
    accent: "from-emerald-500/20 to-teal-500/5",
    iconColor: "text-emerald-300",
  },
  {
    icon: Radio,
    eyebrow: "Live trading and brokers",
    title: "Go live with controls",
    description:
      "Connect broker credentials, create live sessions, manage allocations, pause or stop strategies, and inspect execution logs.",
    accent: "from-rose-500/20 to-red-500/5",
    iconColor: "text-rose-300",
  },
  {
    icon: Terminal,
    eyebrow: "Manual paper terminal",
    title: "Practice manual trades too",
    description:
      "Use the trading terminal for watchlists, charts, order tickets, positions, and manual paper trading.",
    accent: "from-amber-500/20 to-orange-500/5",
    iconColor: "text-amber-300",
  },
];

const intelligenceFeatures = [
  {
    icon: BrainCircuit,
    title: "Strategy advisor",
    text: "Get AI recommendations tied to a strategy, then choose what to apply or dismiss.",
  },
  {
    icon: Gauge,
    title: "Health scoring",
    text: "See whether a strategy looks healthy, weak, or needs attention.",
  },
  {
    icon: Layers3,
    title: "Market regime",
    text: "Understand whether the market environment may suit or hurt a strategy.",
  },
  {
    icon: ShieldCheck,
    title: "Overfit checks",
    text: "Spot when a strategy may be too perfect on history and fragile in real markets.",
  },
];

const ecosystemFeatures = [
  {
    icon: Store,
    title: "Marketplace",
    text: "Explore, publish, subscribe to, review, and monetize strategies.",
  },
  {
    icon: BookOpenCheck,
    title: "Journal and reports",
    text: "Track trades, mistakes, insights, daily reports, and performance snapshots.",
  },
  {
    icon: Users,
    title: "Community and proof",
    text: "Share posts, strategy rooms, trade replays, reputation, and verified work.",
  },
  {
    icon: GraduationCap,
    title: "Learning center",
    text: "Follow courses, lessons, quizzes, assignments, certificates, and recommendations.",
  },
  {
    icon: ClipboardCheck,
    title: "Governance",
    text: "Use approvals, audit logs, compliance checks, notifications, and security tools.",
  },
];

const lifecycleLabels = [
  "AI Research",
  "Strategy",
  "Backtest",
  "Paper",
  "Live",
  "Review",
];

const themeMap = {
  dark: {
    page: "bg-[#050505] text-white selection:bg-[#e5c461] selection:text-black",
    hero: "bg-[#050505]",
    section: "bg-[#050505]",
    alt: "bg-[#090909]",
    card: "border-white/10 bg-[#0b0b0b] text-white",
    cardSoft: "border-white/10 bg-[#0f1117]/90",
    panel: "border-white/10 bg-[#0a0a0a]/90",
    text: "text-white",
    muted: "text-zinc-400",
    subtle: "text-zinc-500",
    border: "border-white/10",
    badge: "border-[#e5c461]/20 bg-[#e5c461]/[0.07] text-[#f2da8e]",
    ghost:
      "border-white/15 bg-white/[0.03] text-zinc-200 hover:border-white/30 hover:bg-white/[0.07] hover:text-white",
    ctaGhost: "border-white/15 bg-black/20 text-white hover:bg-white/[0.06]",
  },
  light: {
    page: "bg-[#fffaf0] text-[#19140a] selection:bg-[#d8b557] selection:text-black",
    hero: "bg-[#fffaf0]",
    section: "bg-[#fffaf0]",
    alt: "bg-[#f7f0df]",
    card: "border-amber-900/10 bg-white/75 text-[#19140a]",
    cardSoft: "border-amber-900/10 bg-white/80",
    panel: "border-amber-900/10 bg-white/82",
    text: "text-[#19140a]",
    muted: "text-stone-600",
    subtle: "text-stone-500",
    border: "border-amber-900/10",
    badge: "border-[#b68b34]/25 bg-[#d8b557]/15 text-[#8a6724]",
    ghost:
      "border-amber-900/15 bg-white/60 text-stone-800 hover:border-[#b68b34]/40 hover:bg-[#fff3c8] hover:text-[#8a6724]",
    ctaGhost: "border-amber-900/15 bg-white/60 text-stone-800 hover:bg-[#fff3c8]",
  },
};

function SectionHeading({ eyebrow, title, description, align = "center", theme }) {
  const alignment =
    align === "left" ? "max-w-3xl" : "mx-auto max-w-3xl text-center";

  return (
    <div className={alignment}>
      <div
        className={`mb-4 flex items-center gap-3 ${
          align === "center" ? "justify-center" : ""
        }`}
      >
        <span className="h-px w-8 bg-[#d8b557]" />
        <span className="text-xs font-semibold uppercase tracking-[0.24em] text-[#caa64f]">
          {eyebrow}
        </span>
        {align === "center" && <span className="h-px w-8 bg-[#d8b557]" />}
      </div>
      <h2 className={`text-3xl font-semibold tracking-[-0.04em] sm:text-4xl lg:text-5xl ${theme.text}`}>
        {title}
      </h2>
      <p className={`mt-4 text-base leading-8 sm:text-lg ${theme.muted}`}>
        {description}
      </p>
    </div>
  );
}

export default function QuantNestLanding() {
  const [themeName, setThemeName] = useState("dark");
  const theme = themeMap[themeName];
  const isLight = themeName === "light";

  const toggleTheme = () => {
    setThemeName((current) => (current === "dark" ? "light" : "dark"));
  };

  return (
    <div
      data-landing-theme={themeName}
      className={`qn-landing min-h-screen overflow-x-clip ${theme.page}`}
    >
      <MainHeader theme={themeName} onThemeToggle={toggleTheme} />

      <main>
        <section className={`relative isolate overflow-hidden ${theme.hero}`}>
          <div className="landing-market-animation absolute inset-0 -z-30" />
          <div className="landing-grid absolute inset-0 -z-20 opacity-40" />
          <div className="landing-sparkline absolute inset-x-0 top-20 -z-10 h-80 opacity-60" />
          <div className="absolute inset-x-0 top-0 -z-10 mx-auto h-[620px] max-w-6xl bg-[radial-gradient(circle_at_50%_0%,rgba(220,183,83,0.18),transparent_62%)]" />
          <div className="landing-orb absolute -left-40 top-44 -z-10 h-80 w-80 rounded-full bg-violet-600/10 blur-[100px]" />
          <div className="landing-orb landing-orb-delay absolute -right-36 top-28 -z-10 h-96 w-96 rounded-full bg-amber-500/10 blur-[120px]" />

          <div className="mx-auto max-w-7xl px-4 pb-16 pt-16 sm:px-6 sm:pt-20 lg:px-8 lg:pb-20 lg:pt-24">
            <div className="mx-auto max-w-5xl text-center">
              <div
                className={`mb-6 inline-flex items-center gap-2 rounded-full border px-4 py-2 text-xs font-medium shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] sm:text-sm ${theme.badge}`}
              >
                <Sparkles className="h-4 w-4" />
                AI research to live trading, in one place
              </div>

              <h1 className={`text-balance text-4xl font-semibold leading-[1.05] tracking-[-0.055em] sm:text-6xl lg:text-[78px] ${theme.text}`}>
                Build, test, and run trading strategies with confidence.
              </h1>

              <p className={`mx-auto mt-6 max-w-3xl text-base leading-8 sm:text-lg lg:text-xl ${theme.muted}`}>
                QuantNest helps you research ideas with AI, create rule-based
                strategies, backtest them, try them in paper trading, and move
                selected strategies to live trading with broker connections and
                risk controls.
              </p>

              <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
                <Button
                  asChild
                  size="lg"
                  className="h-11 w-auto rounded-full border border-[#f2da8e]/40 bg-[#e5c461] px-6 text-sm font-semibold text-black shadow-[0_12px_50px_rgba(229,196,97,0.2)] transition-all duration-300 hover:-translate-y-0.5 hover:bg-[#f2da8e]"
                >
                  <Link to="/register">
                    Create your workspace
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                </Button>
                <Button
                  asChild
                  variant="outline"
                  size="lg"
                  className={`h-11 w-auto rounded-full px-6 text-sm transition-all duration-300 hover:-translate-y-0.5 ${theme.ghost}`}
                >
                  <Link to="/login">
                    Sign in to QuantNest
                    <ChevronRight className="h-4 w-4" />
                  </Link>
                </Button>
              </div>

              <div className={`mt-7 flex flex-wrap items-center justify-center gap-x-6 gap-y-3 text-xs sm:text-sm ${theme.subtle}`}>
                <span className="flex items-center gap-2">
                  <Check className="h-4 w-4 text-[#d8b557]" />
                  AI research
                </span>
                <span className="flex items-center gap-2">
                  <Check className="h-4 w-4 text-[#d8b557]" />
                  Strategy backtesting
                </span>
                <span className="flex items-center gap-2">
                  <Check className="h-4 w-4 text-[#d8b557]" />
                  Paper and live deployment
                </span>
              </div>
            </div>

            <div className="relative mx-auto mt-12 max-w-7xl lg:mt-14">
              <div className="absolute -inset-8 -z-10 bg-[radial-gradient(circle_at_50%_30%,rgba(229,196,97,0.12),transparent_60%)] blur-2xl" />
              <div
                className={`relative rounded-[28px] border p-2 shadow-[0_35px_100px_rgba(0,0,0,0.35),0_0_0_1px_rgba(229,196,97,0.04)] sm:p-3 ${theme.panel}`}
              >
                <div className={`flex items-center justify-between border-b px-3 py-2 sm:px-4 ${theme.border}`}>
                  <div className="flex items-center gap-1.5">
                    <span className="h-2.5 w-2.5 rounded-full bg-[#e95c5c]" />
                    <span className="h-2.5 w-2.5 rounded-full bg-[#e5c461]" />
                    <span className="h-2.5 w-2.5 rounded-full bg-[#45c18a]" />
                  </div>
                  <span className={`text-[10px] font-medium uppercase tracking-[0.22em] sm:text-xs ${theme.subtle}`}>
                    QuantNest trading workspace
                  </span>
                  <div className="w-10" />
                </div>
                <div className="overflow-hidden rounded-[20px]">
                  <img
                    src="/dashboard.png"
                    alt="QuantNest trading terminal with watchlist and live chart"
                    width="1912"
                    height="866"
                    className="h-auto w-full"
                    loading="eager"
                  />
                </div>
              </div>

              <div
                className={`landing-float absolute -left-10 top-[20%] hidden rounded-2xl border p-3 shadow-2xl backdrop-blur-xl xl:block 2xl:-left-16 ${theme.cardSoft}`}
              >
                <div className="flex items-center gap-2.5">
                  <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-emerald-500/15">
                    <Activity className="h-4 w-4 text-emerald-300" />
                  </span>
                  <div>
                    <p className={`text-[11px] ${theme.subtle}`}>Live status</p>
                    <p className={`mt-0.5 text-xs font-medium ${theme.text}`}>
                      Monitored in real time
                    </p>
                  </div>
                </div>
              </div>

              <div
                className={`landing-float landing-float-delay absolute -right-10 bottom-[14%] hidden w-48 rounded-2xl border border-[#e5c461]/20 p-3 shadow-2xl backdrop-blur-xl xl:block 2xl:-right-16 ${theme.cardSoft}`}
              >
                <div className="mb-2 flex items-center justify-between">
                  <span className={`text-[11px] ${theme.subtle}`}>Risk controls</span>
                  <ShieldCheck className="h-4 w-4 text-[#d8b557]" />
                </div>
                <div className="space-y-1.5">
                  {["Sizing rules", "Capital limits", "Emergency stop"].map(
                    (label) => (
                      <div
                        key={label}
                        className={`flex items-center gap-2 text-[11px] ${theme.muted}`}
                      >
                        <span className="h-1.5 w-1.5 rounded-full bg-[#e5c461]" />
                        {label}
                      </div>
                    ),
                  )}
                </div>
              </div>
            </div>

            <div className={`mt-10 overflow-hidden border-y py-4 ${theme.border}`}>
              <div className={`flex flex-wrap items-center justify-center gap-x-3 gap-y-2 text-xs font-medium uppercase tracking-[0.18em] sm:gap-x-5 ${theme.subtle}`}>
                {lifecycleLabels.map((label, index) => (
                  <React.Fragment key={label}>
                    <span>{label}</span>
                    {index < lifecycleLabels.length - 1 && (
                      <ArrowRight className="h-3.5 w-3.5 text-[#8d773d]" />
                    )}
                  </React.Fragment>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section
          id="workflow"
          className={`scroll-mt-24 border-t py-16 sm:py-20 lg:py-24 ${theme.alt} ${theme.border}`}
        >
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <SectionHeading
              theme={theme}
              eyebrow="Main workflow"
              title="A clear path from idea to execution."
              description="QuantNest is built around the way a trader actually works: research first, build rules, test them, paper trade, then go live only when the process is ready."
            />

            <div className="mt-10 grid gap-4 md:grid-cols-2 lg:grid-cols-5">
              {workflow.map((step) => {
                const Icon = step.icon;
                return (
                  <article
                    key={step.number}
                    className={`group relative overflow-hidden rounded-3xl border p-5 transition-all duration-500 hover:-translate-y-1 hover:border-[#e5c461]/40 ${theme.card}`}
                  >
                    <div className="absolute right-4 top-4 text-4xl font-semibold tracking-[-0.06em] opacity-[0.05]">
                      {step.number}
                    </div>
                    <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-[#e5c461]/25 bg-[#e5c461]/10">
                      <Icon className="h-5 w-5 text-[#d8b557]" />
                    </div>
                    <h3 className={`mt-5 text-lg font-semibold tracking-tight ${theme.text}`}>
                      {step.title}
                    </h3>
                    <p className={`mt-3 text-sm leading-6 ${theme.muted}`}>
                      {step.description}
                    </p>
                    <p className="mt-4 rounded-2xl border border-[#e5c461]/20 bg-[#e5c461]/10 p-3 text-xs leading-5 text-[#caa64f]">
                      {step.benefit}
                    </p>
                  </article>
                );
              })}
            </div>
          </div>
        </section>

        <section
          id="platform"
          className={`scroll-mt-24 py-16 sm:py-20 lg:py-24 ${theme.section}`}
        >
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <SectionHeading
              theme={theme}
              eyebrow="Platform"
              title="What each part helps you do."
              description="Every feature has a simple job: help you make better decisions, test them properly, and trade with more control."
            />

            <div className="mt-10 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {platformFeatures.map((feature) => {
                const Icon = feature.icon;
                return (
                  <article
                    key={feature.title}
                    className={`group relative min-h-[260px] overflow-hidden rounded-3xl border p-6 transition-all duration-500 hover:border-[#e5c461]/30 ${theme.card}`}
                  >
                    <div
                      className={`absolute inset-0 bg-gradient-to-br ${feature.accent} opacity-0 transition-opacity duration-500 group-hover:opacity-100`}
                    />
                    <div className="relative">
                      <div className="flex items-center justify-between">
                        <span className={`text-xs font-semibold uppercase tracking-[0.2em] ${theme.subtle}`}>
                          {feature.eyebrow}
                        </span>
                        <Icon className={`h-6 w-6 ${feature.iconColor}`} />
                      </div>
                      <h3 className={`mt-12 max-w-xs text-2xl font-semibold tracking-[-0.035em] ${theme.text}`}>
                        {feature.title}
                      </h3>
                      <p className={`mt-4 text-sm leading-7 ${theme.muted}`}>
                        {feature.description}
                      </p>
                    </div>
                  </article>
                );
              })}
            </div>
          </div>
        </section>

        <section className={`border-y py-16 sm:py-20 lg:py-24 ${theme.alt} ${theme.border}`}>
          <div className="mx-auto grid max-w-7xl items-center gap-10 px-4 sm:px-6 lg:grid-cols-[0.85fr_1.15fr] lg:gap-14 lg:px-8">
            <div>
              <SectionHeading
                theme={theme}
                align="left"
                eyebrow="Manual paper trading"
                title="Use the terminal when you want to trade manually."
                description="The trading terminal is for manual paper trading. Watch symbols, read charts, place orders, and learn execution without putting real money at risk."
              />

              <div className="mt-7 space-y-3">
                {[
                  "Build watchlists and search instruments",
                  "Read live candles across timeframes",
                  "Place paper buy and sell orders manually",
                  "Track account, positions, orders, and history",
                ].map((item) => (
                  <div
                    key={item}
                    className={`flex items-start gap-3 text-sm leading-6 ${theme.muted}`}
                  >
                    <span className="mt-1 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-500/15">
                      <Check className="h-3 w-3 text-emerald-300" />
                    </span>
                    {item}
                  </div>
                ))}
              </div>

              <Button
                asChild
                variant="outline"
                className={`mt-8 h-11 rounded-full px-6 ${theme.ghost}`}
              >
                <Link to="/register">
                  Try manual paper trading
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
            </div>

            <div className="relative">
              <div className="absolute -inset-8 bg-[radial-gradient(circle_at_50%_50%,rgba(26,132,255,0.12),transparent_65%)] blur-2xl" />
              <div className={`relative overflow-hidden rounded-[26px] border p-2 shadow-[0_30px_90px_rgba(0,0,0,0.35)] ${theme.panel}`}>
                <img
                  src="/dashboard.png"
                  alt="QuantNest watchlist, candlestick chart, and trading controls"
                  width="1912"
                  height="866"
                  loading="lazy"
                  className="h-full min-h-[320px] w-full rounded-[20px] object-center"
                />
              </div>
            </div>
          </div>
        </section>

        <section
          id="intelligence"
          className={`scroll-mt-24 relative overflow-hidden py-16 sm:py-20 lg:py-24 ${theme.section}`}
        >
          <div className="absolute left-1/2 top-0 h-[420px] w-[760px] -translate-x-1/2 rounded-full bg-violet-600/[0.08] blur-[140px]" />
          <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="grid items-start gap-10 lg:grid-cols-[0.9fr_1.1fr] lg:gap-14">
              <div className="lg:sticky lg:top-28">
                <SectionHeading
                  theme={theme}
                  align="left"
                  eyebrow="Intelligence"
                  title="AI Engine helps you improve strategies."
                  description="This part of QuantNest is strategy-focused. It does not replace your decision, but it helps you review strategy quality, market fit, and risk."
                />
                <div className="mt-7 rounded-2xl border border-[#e5c461]/20 bg-[#e5c461]/[0.08] p-5">
                  <div className="flex items-start gap-3">
                    <LockKeyhole className="mt-0.5 h-5 w-5 shrink-0 text-[#d8b557]" />
                    <p className={`text-sm leading-6 ${theme.muted}`}>
                      AI suggestions are reviewable. Applying a change remains
                      a deliberate user action.
                    </p>
                  </div>
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                {intelligenceFeatures.map((feature, index) => {
                  const Icon = feature.icon;
                  return (
                    <article
                      key={feature.title}
                      className={`rounded-3xl border p-6 ${
                        index % 2 === 1 ? "sm:translate-y-6" : ""
                      } ${theme.card}`}
                    >
                      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-violet-500/10 ring-1 ring-violet-400/20">
                        <Icon className="h-5 w-5 text-violet-300" />
                      </div>
                      <h3 className={`mt-7 text-xl font-semibold ${theme.text}`}>
                        {feature.title}
                      </h3>
                      <p className={`mt-3 text-sm leading-7 ${theme.muted}`}>
                        {feature.text}
                      </p>
                    </article>
                  );
                })}
              </div>
            </div>
          </div>
        </section>

        <section
          id="ecosystem"
          className={`scroll-mt-24 border-y py-16 sm:py-20 lg:py-24 ${theme.alt} ${theme.border}`}
        >
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <SectionHeading
              theme={theme}
              eyebrow="Ecosystem"
              title="A platform for improving the trader, not only the trade."
              description="These features support learning, sharing, reporting, verification, and governance so the platform can grow with the trader."
            />

            <div className={`mt-10 grid gap-px overflow-hidden rounded-3xl border md:grid-cols-2 lg:grid-cols-5 ${theme.border}`}>
              {ecosystemFeatures.map((feature) => {
                const Icon = feature.icon;
                return (
                  <article
                    key={feature.title}
                    className={`p-6 transition-colors duration-300 ${isLight ? "bg-white/70 hover:bg-white" : "bg-[#0b0b0b] hover:bg-[#10100e]"}`}
                  >
                    <Icon className="h-6 w-6 text-[#d8b557]" />
                    <h3 className={`mt-8 text-lg font-semibold ${theme.text}`}>
                      {feature.title}
                    </h3>
                    <p className={`mt-3 text-sm leading-7 ${theme.muted}`}>
                      {feature.text}
                    </p>
                  </article>
                );
              })}
            </div>
          </div>
        </section>

        <section className={`relative overflow-hidden py-16 sm:py-20 lg:py-24 ${theme.section}`}>
          <div className="landing-market-animation absolute inset-0 opacity-70" />
          <div className="landing-grid absolute inset-0 opacity-20" />
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(229,196,97,0.14),transparent_48%)]" />
          <div className="relative mx-auto max-w-5xl px-4 text-center sm:px-6 lg:px-8">
            <img
              src="/logo_1-wordmark.png"
              alt="QuantNest"
              className="mx-auto h-12 w-auto object-contain sm:h-14"
              loading="lazy"
            />
            <h2 className={`mt-8 text-3xl font-semibold tracking-[-0.045em] sm:text-5xl lg:text-6xl ${theme.text}`}>
              Build the process before you risk the capital.
            </h2>
            <p className={`mx-auto mt-5 max-w-2xl text-base leading-8 sm:text-lg ${theme.muted}`}>
              Start with research, test your strategy, run it on paper, and
              move to live trading only when the workflow gives you enough
              confidence.
            </p>
            <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
              <Button
                asChild
                size="lg"
                className="h-[52px] rounded-full bg-[#e5c461] px-8 font-semibold text-black hover:bg-[#f2da8e]"
              >
                <Link to="/register">
                  Start building
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
              <Button
                asChild
                variant="outline"
                size="lg"
                className={`h-[52px] rounded-full px-8 ${theme.ctaGhost}`}
              >
                <Link to="/login">Access your account</Link>
              </Button>
            </div>
          </div>
        </section>
      </main>

      <footer className={`border-t ${theme.border} ${isLight ? "bg-[#fffaf0]" : "bg-black"}`}>
        <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
          <div className="flex flex-col gap-10 lg:flex-row lg:items-start lg:justify-between">
            <div className="max-w-sm">
              <img
                src="/logo_1-wordmark.png"
                alt="QuantNest"
                className="h-9 w-auto object-contain"
                loading="lazy"
              />
              <p className={`mt-5 text-sm leading-7 ${theme.muted}`}>
                AI research, strategy creation, backtesting, paper trading,
                live trading, and review tools in one connected platform.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-x-10 gap-y-5 text-sm sm:grid-cols-4">
              {[
                ["Workflow", "workflow"],
                ["Platform", "platform"],
                ["Intelligence", "intelligence"],
                ["Ecosystem", "ecosystem"],
              ].map(([label, target]) => (
                <button
                  key={target}
                  type="button"
                  onClick={() =>
                    document
                      .getElementById(target)
                      ?.scrollIntoView({ behavior: "smooth" })
                  }
                  className={`text-left transition-colors hover:text-[#b68b34] ${theme.subtle}`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          <div className={`mt-10 flex flex-col gap-4 border-t pt-7 text-xs leading-6 lg:flex-row lg:items-end lg:justify-between ${theme.border} ${theme.subtle}`}>
            <p>
              Copyright {new Date().getFullYear()} QuantNest. All rights
              reserved.
            </p>
            <p className="max-w-3xl lg:text-right">
              QuantNest provides software for trading research and execution
              workflows. It does not provide investment advice. Trading and
              investing involve risk, including possible loss of capital. Past
              or simulated performance does not guarantee future results.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
