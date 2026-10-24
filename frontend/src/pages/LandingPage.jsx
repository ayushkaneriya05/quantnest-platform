import { useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ArrowRight, Check, Code2, Sparkles } from 'lucide-react';
import { useTheme } from '@/shared/context/theme';
import MainHeader from '@/shared/components/layout/main-header';
import { Button } from '@/shared/components/ui/button';
import SiteFooter from '@/features/site/SiteFooter';
import SiteEffects from '@/features/site/SiteEffects';
import PricingCards from '@/features/site/PricingCards';
import SiteIllustration from '@/features/site/SiteIllustration';
import { FeatureGrid, PointList, SectionTitle } from '@/features/site/SiteSections';
import { faq } from '@/features/site/config';
import '@/features/site/site.css';

const journey = [
  ['Research', 'Ask questions and screen selected stocks.', '/features/research/'],
  ['Define', 'Turn your own idea into readable rules.', '/features/builder/'],
  ['Test', 'Inspect historical trades, costs and assumptions.', '/features/backtesting/'],
  ['Practise', 'Run a saved version with simulated capital.', '/features/paper/'],
  ['Review', 'Record lessons and investigate the results.', '/features/journal/'],
];

export default function QuantNestLanding() {
  const { resolvedTheme } = useTheme();
  const { hash } = useLocation();
  useEffect(() => {
    document.title = 'QuantNest · Your rules, clearly tested';
    const description = document.querySelector('meta[name="description"]');
    if (description) description.content = 'Research your own trading ideas, build rules, backtest and practise in Paper. Explore QuantNest subscriptions and separate custom software development.';
    if (hash) document.getElementById(hash.slice(1))?.scrollIntoView();
    else window.scrollTo({ top: 0 });
  }, [hash]);

  return <div data-landing-theme={resolvedTheme} className="qn-landing site-root min-h-dvh overflow-x-clip bg-background text-foreground selection:bg-brand/25">
    <a href="#site-main" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-card focus:p-3">Skip to content</a>
    <MainHeader />
    <main id="site-main">
      <section className="site-home-hero relative isolate overflow-hidden border-b">
        <div aria-hidden="true" className="landing-market-animation pointer-events-none absolute inset-0" /><div aria-hidden="true" className="landing-grid pointer-events-none absolute inset-0 opacity-40" /><div aria-hidden="true" className="landing-orb pointer-events-none absolute -right-20 top-12 h-80 w-80 rounded-full bg-brand/10 blur-3xl" />
        <div className="site-container relative grid items-center gap-8 py-10 sm:py-14 lg:grid-cols-[1.1fr_1fr] lg:gap-12 lg:py-16">
          <div className="site-appear"><p className="site-eyebrow flex items-center gap-2"><Sparkles className="h-4 w-4" />Your idea. A more considered process.</p>
            <h1 className="mt-6 text-4xl font-semibold leading-[1.12] tracking-[-.045em] sm:text-5xl lg:text-6xl">Give your trading ideas<br className="hidden sm:block" /> <span className="text-brand">a clearer path.</span></h1>
            <p className="mt-6 max-w-xl text-base leading-8 text-muted-foreground sm:text-lg">Research your questions. Build your own rules. Test them on history and practise with simulated capital—all in one connected workspace.</p>
            <div className="mt-8 flex flex-wrap gap-3"><Button asChild size="lg" className="rounded-full"><Link to="/register">Start free with Explore<ArrowRight className="h-4 w-4" /></Link></Button><Button asChild variant="outline" size="lg" className="rounded-full"><Link to="/product/">See how QuantNest works</Link></Button></div>
            <div className="mt-7 flex flex-wrap gap-x-5 gap-y-3 text-xs text-muted-foreground">{['Your own strategy logic', 'Historical testing', 'Automated Paper practice'].map(text => <span className="flex items-center gap-2" key={text}><Check className="h-3.5 w-3.5 text-brand" />{text}</span>)}</div>
            <p className="mt-6 max-w-lg text-xs leading-6 text-muted-foreground">For supported NSE cash-stock workflows. Public plans cover simulation through Paper; customer Live trading is not currently available.</p>
          </div>
          <div className="site-hero-visual relative min-w-0"><SiteIllustration name="home" /><div className="site-visual-caption mt-4 flex justify-between gap-3 px-2 text-xs text-muted-foreground"><span>From the first question to the next iteration</span><span className="shrink-0 text-brand">Built around your logic</span></div></div>
        </div>
      </section>

      <section className="site-home-section" id="workflow"><div className="site-container"><SectionTitle eyebrow="The connected workflow" title="Less scattered work. More context." description="Each step keeps the question, configuration and recorded outcome connected, so you can understand what you tested and why." />
        <ol className="mt-7 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">{journey.map(([title, detail, to], index) => <li key={title}><Link to={to} className="group block h-full rounded-2xl border bg-card p-5"><div className="flex items-center justify-between text-brand"><span className="text-xs font-semibold">0{index + 1}</span><ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" /></div><h3 className="mt-5 font-semibold">{title}</h3><p className="mt-3 text-sm leading-7 text-muted-foreground">{detail}</p></Link></li>)}</ol>
      </div></section>

      <section className="site-home-section border-y bg-muted/30" id="features"><div className="site-container"><div className="mb-7 flex flex-col justify-between gap-5 md:flex-row md:items-end"><SectionTitle eyebrow="Inside your workspace" title="Choose your next task." description="Explore every part of QuantNest, from your first research question to a detailed review of recorded results." /><Link to="/features/" className="flex shrink-0 items-center gap-2 text-sm font-medium text-brand">All features<ArrowRight className="h-4 w-4" /></Link></div><FeatureGrid /></div></section>

      <section className="site-home-section" id="research"><div className="site-container grid items-center gap-8 lg:grid-cols-2 lg:gap-12"><SiteIllustration name="research-intro" /><div><SectionTitle eyebrow="Research with context" title="Keep asking better questions." description="Use the assistant to investigate your own ideas, inspect supporting calculations and understand the results you already have." /><div className="my-7"><PointList points={['Attach selected stocks, a watchlist, your strategy or completed backtests.', 'Open sources and observation times instead of taking a written answer at face value.', 'Refine a draft in conversation and confirm it before anything is created or started.']} /></div><Link to="/features/research/" className="inline-flex items-center gap-2 font-medium text-brand">Explore AI research<ArrowRight className="h-4 w-4" /></Link></div></div></section>

      <section className="site-home-section border-y bg-muted/30" id="services"><div className="site-container"><SectionTitle eyebrow="Beyond the public workspace" title="Software for your own project." description="Commission an application, tool or integration built around your requirements. No QuantNest subscription is required." /><div className="mt-7 max-w-3xl">
        <article className="site-service-card site-card"><Code2 className="h-7 w-7 text-brand" /><h3 className="mt-6 text-2xl font-semibold">Custom software development</h3><p className="mt-4 text-sm leading-7 text-muted-foreground">Applications, dashboards, workflow automation, data tools and integrations. Describe your goal; we help turn it into an agreed specification.</p><div className="my-6"><PointList points={['Agree inputs, deliverables, acceptance criteria and ownership.', 'Work through clear milestones, handover and optional maintenance.']} /></div><Button asChild variant="outline" className="rounded-full"><Link to="/custom-development/">Explore development services<ArrowRight className="h-4 w-4" /></Link></Button></article>
      </div></div></section>

      <section className="site-home-section" id="pricing"><div className="site-container"><div className="mb-7"><SectionTitle eyebrow="Simple workspace plans" title="Start small. Add room when you need it." description="Explore the public workflow with limited free usage. Choose Build or Pro when you need more saved strategies, tests, research and Paper capacity." /></div><PricingCards /><Link to="/pricing/" className="mt-6 inline-flex items-center gap-2 text-sm text-brand">Understand credits and compare plans<ArrowRight className="h-4 w-4" /></Link></div></section>

      <section className="site-home-section border-t" id="faq"><div className="site-container grid gap-10 lg:grid-cols-[.8fr_1.2fr]"><div><SectionTitle eyebrow="Before you begin" title="A few useful answers." description="Know what is included and what simulated results can tell you." /><Link to="/faq/" className="mt-6 inline-flex items-center gap-2 text-sm text-brand">Read all FAQs<ArrowRight className="h-4 w-4" /></Link><Link to="/docs/" className="mt-4 block text-sm text-brand">Read the user guides →</Link></div><div>{faq.slice(0, 5).map(([question, answer]) => <details className="site-faq border-b py-5 first:pt-0" key={question}><summary className="cursor-pointer text-base font-medium leading-7">{question}</summary><p className="mt-4 text-sm leading-7 text-muted-foreground">{answer}</p></details>)}</div></div></section>

      <section className="site-container pb-10 sm:pb-16"><div className="site-closing-panel relative overflow-hidden rounded-3xl border border-brand/30 bg-brand/5 px-6 py-8 text-center sm:px-12"><p className="site-eyebrow">A place to start thinking clearly</p><h2 className="mt-5 text-3xl font-semibold tracking-tight sm:text-4xl">Bring your idea. Keep the decisions yours.</h2><p className="mx-auto mt-5 max-w-2xl text-base leading-8 text-muted-foreground">Create a workspace for your own research and rules, or tell us about the software you need.</p><div className="mt-7 flex flex-wrap justify-center gap-3"><Button asChild size="lg" className="rounded-full"><Link to="/register">Create your workspace<ArrowRight className="h-4 w-4" /></Link></Button><Button asChild variant="outline" size="lg" className="rounded-full"><Link to="/contact/">Talk to QuantNest</Link></Button></div></div></section>
    </main><SiteFooter /><SiteEffects />
  </div>;
}
