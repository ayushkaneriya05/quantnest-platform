# Archived Private marketing source

Inactive reference only. These former customer offers are not available.
Restore selectively only after reviewing the then-current product and requirements.

## frontend/src/features/site/content/general.js

```jsx
export const generalPages = {
  product: { title: 'One workspace. A clearer trading process.', description: 'Move from a question to explicit rules, historical tests and simulated practice. Keep the context behind every result.', sections: [
    ['Research an idea', ['Ask AI about selected stocks or your own strategy question.', 'Screen your watchlist with conditions you choose, then investigate the matching results.']],
    ['Define your rules', ['Build entries, exits, sizing and safeguards in the visual strategy builder.', 'Save versions with notes so you know exactly what changed between experiments.']],
    ['Test and practise', ['Backtest a saved configuration with dates, capital and costs you can inspect.', 'Practise manually in Terminal or automatically in Paper, then review what was recorded.']],
    ['Keep environments clear', ['Public subscriptions include the supported workflow through simulation and Paper trading.', 'Private installations and Live execution are separately assessed. Build and Pro list NSE futures and options as coming soon. They are not available yet; current public workflows support NSE stocks.']],
  ] },
  private: { title: 'Live trading. Your own installation.', description: 'Run your own strategies with supported Live broker execution in a customer-owned QuantNest installation. Keep research, backtesting, Paper and review in your agreed private workspace.', sections: [
    ['What your installation can include', ['Research, screening, strategy building, backtesting, Terminal, Paper, journal, reports and account controls from the maintained product.', 'Agree seats, accounts, workloads and modules before setup. Live is included only when separately accepted and activated.']],
    ['Customer-owned deployment', ['Run the agreed installation on infrastructure you control. Define who manages updates, backups, monitoring and recovery.', 'Keep credentials and trading records in the installation. Discuss any external AI processing before enabling it.']],
    ['Live execution assessment', ['Use your own strategy logic. We assess supported broker connectivity, execution behaviour, controls and requirements applicable to your deployment.', 'Customer-owned hosting is not an automatic exemption from broker or regulatory requirements. Public subscriptions do not activate Live.']],
    ['Setup and ongoing costs', ['Your written quote covers setup, supported releases, support allowance and renewable licensing or maintenance.', 'Infrastructure, broker, data and AI charges are identified separately. Source-code or perpetual-use rights need a separate agreement.']],
    ['Predictable renewal behaviour', ['Renewable licence expiry restricts new deployments and other user-initiated work. Already running strategies continue; monitoring, reconciliation, records and exports remain available.', 'After renewal, an administrator can enable new work. Expiry does not automatically pause running strategies or liquidate positions; purchased continuing-use rights follow your contract.']],
  ], cta: 'Discuss a Private installation', kind: 'private' },
  'custom-development': { title: 'Software built around your way of working.', description: 'Bring your own logic, process or specification. Get a scoped software project with clear deliverables and handover.', sections: [
    ['Who we can help', ['Independent traders needing a tool for their own process, developers refining a research workflow and small teams with testing or reporting needs.', 'Professional-business projects are assessed for access rights, scope and applicable requirements before acceptance.']],
    ['Tools and extensions', ['Custom research utilities, rule implementation, debugging, testing tools, data processing and reports.', 'Authorised code conversion and new integrations can be quoted after a feasibility review. An integration is supported only after delivery and verification.']],
    ['A scope you can review', ['Agree inputs, outputs, acceptance criteria, environments, ownership and third-party costs in writing.', 'Small tools typically start at ₹15,000–₹40,000. Larger testing applications or integrations start at ₹50,000–₹1.5 lakh+. These are scope-dependent quotation starting points, not fixed prices.']],
    ['Clear delivery milestones', ['Enquiry, written requirements, quotation, agreed milestones, acceptance and handover.', 'Payments are normally 40% at commencement, 40% at the acceptance milestone and 20% at handover. Scope changes are agreed before additional work.']],
    ['Support after handover', ['Choose optional maintenance, updates and a defined support allowance.', 'Your agreement distinguishes customer-specific work, licensed QuantNest components and third-party dependencies. Timing and commitments are agreed before you start.']],
  ], cta: 'Tell us what you want to build', kind: 'custom' },
  about: { title: 'Make the reasoning visible.', description: 'QuantNest is an independently developed platform for people who want to understand, test and improve their own trading process.', sections: [
    ['Why QuantNest exists', ['A result is easier to understand when you can inspect its rules and assumptions.', 'Research, configuration, testing, simulation and review belong to one connected investigation.']],
    ['What we believe', ['Your decisions should stay yours. Software should make them easier to inspect without promising a financial outcome.', 'Saved versions, visible costs and clear simulation boundaries help you ask better questions.']],
    ['Our initial focus', ['Supported NSE cash-stock workflows for self-directed users in India.', 'Scoped custom tools and private installations are also available to discuss. Additional markets and instruments need separate development and verification.']],
  ] },
  trust: { title: 'Clear expectations from the beginning.', description: 'Understand what the software does, how your work is handled and which decisions remain yours.', sections: [
    ['Your logic and decisions', ['You choose instruments, rules, sizing and cost assumptions.', 'QuantNest provides software, not investment advice, managed trading, trading signals or assured returns.']],
    ['Results with context', ['Review observation times, costs, coverage and assumptions alongside results.', 'AI answers link to supporting evidence where available. Check the evidence before relying on an explanation.']],
    ['Account and privacy controls', ['Use two-factor authentication and sign-in session controls.', 'Private notes and execution records are not part of public strategy links. Product update emails require a separate subscription.']],
    ['Commercial clarity', ['Review plan limits and checkout totals before paying. Public plans do not activate Live.', 'Private installations and custom projects use written agreements. Contact us to clarify your requirements.']],
  ] },
  'privacy-policy': { title: 'Privacy notice', description: 'Revision 17 October 2026. What information supports your service and how to manage your choices.', sections: [
    ['Information supporting your workspace', ['Account details, sign-in information, saved rules, research questions, execution records, reviews, support messages and billing records support the features you use.', 'Keep passwords, broker secrets and authentication cookies out of support forms and AI questions.']],
    ['Service providers and AI processing', ['Configured providers include Oracle for hosting and protected storage, Cloudflare for delivery/protection, Brevo for email and Razorpay for payments. Google sign-in is used when selected.', 'AI research may send questions and attached context to the configured Gemini service. Content-free application error categories are recorded in service logs.']],
    ['Email and browser storage', ['Email supports account security, billing and replies to your support requests.', 'Browser storage supports sign-in and preferences such as your theme. We do not track product usage or website visits, or record session replays.']],
    ['Access, export and deletion', ['Use account settings or support for export or deletion requests. Execution must be safely settled before deletion.', 'Billing and audit records may need retention for applicable obligations. Contact us about your specific request.']],
    ['Questions and revisions', ['Contact the published support address for privacy questions or grievances.', 'Material changes to this notice are versioned and published here.']],
  ] },
  'terms-of-service': { title: 'Workspace terms', description: 'Public subscription scope, your responsibilities and the limits of simulated results.', sections: [
    ['Service scope', ['Research, configuration, historical testing, simulation and review software for your own logic.', 'Public plans cover the supported workflow through Paper. Private, Live and custom projects need separate agreements.']],
    ['Responsible use', ['The initial public offering is for adult India-resident users and supported NSE cash stocks.', 'Use authorised accounts and content and comply with applicable requirements. This is not discretionary management of customer trading accounts.']],
    ['Plans and billing', ['Explore is free. The pricing page shows the current Build and Pro prices and allowances. Checkout shows the reviewed total including applicable taxes.', 'No rollover or automatic paid overages. Automatic renewal requires consent.']],
    ['Cancellation and expiry', ['Cancel future renewal while keeping the paid period. Plan changes are scheduled at renewal.', 'Saved work remains accessible; further activity must fit current limits. Resuming Paper is an explicit action.']],
    ['Result limitations', ['AI may be incorrect. Backtests and simulation depend on observations, costs and assumptions.', 'Results do not establish future profitability or reproduce every broker/exchange condition.']],
    ['Private and custom contracts', ['Separate agreements define installation scope, execution requirements, ownership, licensing, milestones and maintenance.', 'Owning the server does not automatically exempt a Live deployment from applicable requirements.']],
    ['Refunds and support', ['The first paid Workspace purchase has a seven-day refund window alongside applicable remedies.', 'Use Billing and Usage or the published support channel. Private/custom contracts have separate terms.']],
  ] },
  refunds: { title: 'Change your mind with a clear process.', description: 'Cancellation, the first-purchase refund window and the terms of custom work.', sections: [
    ['First paid Workspace purchase', ['Request a refund within seven days of your first paid Workspace purchase, alongside applicable remedies.', 'Submit a payment reference and reason in Billing and Usage. Track the request in your account.']],
    ['After your request', ['Requests are reviewed; payment-provider processing may take additional time.', 'Confirmed refunds link to the original payment. Status and relevant credit notes remain in your billing records.']],
    ['Cancel future renewal', ['Stop future automatic renewal while preserving the current paid period.', 'Saved work remains accessible. Further activity must fit your current allowances; no automatic paid overages apply.']],
    ['Private and custom work', ['Setup, milestones, handover and maintenance have separately agreed cancellation/refund terms.', 'Review the written quote and contract before acceptance.']],
  ] },
  methodology: { title: 'Read the assumptions with the result.', description: 'Historical tests, simulated fills, costs and unavailable metrics explained.', sections: [
    ['Historical observations', ['Tests use available candles and your saved rules. Indicators may need earlier candles before values are usable.', 'Crossovers need a previous observation. Holidays, gaps and coverage affect calculations.']],
    ['Costs and fills', ['Choose a charge profile and slippage and inspect their effect on trades.', 'Candles do not reveal every movement or exchange queue. If stop and target both fall within a candle, the model uses its stated stop-first assumption.']],
    ['Terminal and Paper', ['Terminal simulates manual orders; Paper simulates automated execution of saved rules.', 'Neither establishes live broker fills. Broker partial fills and manual reductions are separate closes.']],
    ['Timing and coverage', ['Check timeframe and observation date. Completed candles and a current quote are different observations.', 'Missing history and unverified corporate-action adjustments can limit results. Availability depends on supported markets and your account.']],
    ['Unavailable metrics', ['Empty totals are zero; undefined ratios are N/A.', 'Recorded closes cannot supply historical equity metrics without the necessary series. Check remaining exposure and diagnostics too.']],
  ] },
  security: { title: 'Protect your workspace and your access.', description: 'Practical account controls and a clear way to report concerns.', sections: [
    ['Protect your account', ['Enable 2FA and keep recovery codes private.', 'Review sessions and revoke unfamiliar access. Keep credentials and cookies out of messages.']],
    ['Report a vulnerability', ['Choose Security report in Contact or email the published address.', 'Describe the page and reproduction steps without other people’s data. Do not run destructive production tests.']],
    ['Private responsibilities', ['Agree access, updates, backups, monitoring and incident responsibilities before installation.', 'Support access has an agreed scope and expiry; your agreement defines responsibilities.']],
    ['What to expect', ['Reports are triaged during published support hours.', 'Verified incidents are investigated and affected customers informed as appropriate. No 24/7 response or uptime SLA is implied.']],
  ] },
  changelog: { title: 'What you can use. What comes next.', description: 'Current capabilities and future work are presented separately.', sections: [
    ['Research and strategy development', ['Conversations, configurable screens, readable rules and version history.', 'Historical tests preserve settings and results; completed tests can be attached for research.']],
    ['Practice and review', ['Separate manual Terminal and automated Paper, with journal reviews and performance reports.', 'Account controls, usage, billing and support are connected to your workspace. Availability is shown in your account.']],
    ['Future development', ['Additional markets, instruments, integrations, imports and team workflows are future or separately scoped work.', 'They are not included as delivered public subscription capabilities. Share priorities through Feedback.']],
  ] },
};

```

## frontend/src/features/site/CustomerPages.jsx

```jsx
import { useEffect } from 'react';
import PropTypes from 'prop-types';
import { Link, useLocation, useParams } from 'react-router-dom';
import { ArrowRight, BookOpen, Code2, LockKeyhole, MessageSquare, Radio } from 'lucide-react';
import { usePlatform } from '@/shared/context/platform';
import { Button } from '@/shared/components/ui/button';
import { getFeaturePages } from './content/features';
import WorkspaceState from '@/shared/components/WorkspaceState';
import { generalPages } from './content/general';
import { faq } from './config';
import PageIntro from './PageIntro';
import PricingCards from './PricingCards';
import EnquiryForm from './EnquiryForm';
import SiteIllustration from './SiteIllustration';
import Documentation from './Documentation';
import { FeatureGrid, PointList, SectionTitle } from './SiteSections';
import NotFoundPage from '@/pages/NotFoundPage';

const policyPages = new Set(['privacy-policy', 'terms-of-service', 'refunds', 'methodology']);
const pageTitles = { pricing: 'Room for your next experiment.', features: 'Tools for every step of your process.', docs: 'Your QuantNest guide', contact: 'Tell us what you need.', feedback: 'Help shape your workspace.', faq: 'Your questions, answered.', status: 'Service status' };

function GeneralContent({ info, page }) {
  if (policyPages.has(page)) return <>
    <PageIntro title={info.title} description={info.description} eyebrow="The details that matter" />
    <div className="grid items-start gap-7 lg:grid-cols-[230px_1fr]"><nav aria-label="On this page" className="site-policy-nav rounded-2xl border bg-card p-5 lg:sticky lg:top-28"><p className="mb-4 text-xs font-semibold uppercase tracking-widest text-brand">On this page</p>{info.sections.map(([heading], index) => <a className="block rounded-lg px-2 py-2.5 text-sm text-muted-foreground hover:bg-accent hover:text-foreground" key={heading} href={`#section-${index}`}>{heading}</a>)}</nav>
      <article className="max-w-3xl divide-y">{info.sections.map(([heading, points], index) => <section id={`section-${index}`} className="scroll-mt-28 py-7 first:pt-0" key={heading}><h2 className="mb-5 text-xl font-semibold">{heading}</h2><PointList points={points} /></section>)}<p className="pt-5 text-sm leading-7 text-muted-foreground">Need clarification? <Link className="text-brand underline underline-offset-4" to="/contact/">Contact QuantNest</Link>.</p></article>
    </div>
  </>;
  if (page === 'product') return <>
    <div className="site-split-intro"><PageIntro title={info.title} description={info.description} eyebrow="The QuantNest workspace" /><SiteIllustration name="product" /></div>
    <div className="mb-8 grid gap-5 md:grid-cols-2">{info.sections.map(([heading, points], index) => <section className="site-card" key={heading}><p className="mb-4 text-xs text-brand">0{index + 1}</p><h2 className="mb-5 text-xl font-semibold">{heading}</h2><PointList points={points} /></section>)}</div>
    <SectionTitle eyebrow="Find your next task" title="Explore the complete toolkit." /><div className="mt-8"><FeatureGrid /></div><div className="mt-8 flex flex-wrap gap-3"><Button asChild><Link to="/register">Start with Explore<ArrowRight className="h-4 w-4" /></Link></Button><Button asChild variant="outline"><Link to="/docs/getting-started/">Read the getting-started guide</Link></Button></div>
  </>;
  if (page === 'private' || page === 'custom-development') {
    const custom = page === 'custom-development';
    const Icon = custom ? Code2 : LockKeyhole;
    return <><div className="site-split-intro"><div><div>{!custom && <p className="mb-3 inline-flex items-center gap-2 rounded-full border border-brand/25 bg-brand/10 px-3 py-2 text-xs font-medium text-brand"><Radio className="h-3.5 w-3.5" />Live trading supported in Private</p>}<PageIntro title={info.title} description={info.description} eyebrow={custom ? 'Custom software development' : 'QuantNest Private'} /></div><Button asChild size="lg" className="mb-8 rounded-full"><Link to={`/contact/?type=${info.kind}`}>{info.cta}<ArrowRight className="h-4 w-4" /></Link></Button></div><SiteIllustration name={custom ? 'development' : 'private'} /></div>
      <div className="grid items-start gap-7 lg:grid-cols-[1fr_300px]"><div className="space-y-6">{info.sections.map(([heading, points], index) => <section key={heading} className="grid gap-4 border-t pt-5 sm:grid-cols-[45px_1fr]"><span className="text-sm font-semibold text-brand">0{index + 1}</span><div><h2 className="mb-5 text-xl font-semibold">{heading}</h2><PointList points={points} /></div></section>)}</div><aside className="site-card h-fit lg:sticky lg:top-28"><Icon className="h-7 w-7 text-brand" /><h2 className="mb-5 mt-5 font-semibold">What to send in your enquiry</h2><PointList points={custom ? ['The task you want to complete.', 'Your inputs and expected outputs.', 'Existing tools, constraints and desired timing.'] : ['Modules and workflows you need.', 'Who will use the installation.', 'Hosting, broker and support requirements.']} /><Button asChild className="mt-6 w-full"><Link to={`/contact/?type=${info.kind}`}>Start the conversation</Link></Button></aside></div>
    </>;
  }
  if (page === 'about') return <><div className="site-about-intro border-b pb-10"><p className="site-eyebrow">About QuantNest</p><h1 className="mt-6 max-w-4xl text-4xl font-semibold leading-tight tracking-tight sm:text-5xl">{info.title}</h1><p className="mt-7 max-w-2xl text-lg leading-8 text-muted-foreground">{info.description}</p></div><div className="grid gap-8 py-8 lg:grid-cols-[.8fr_1.2fr]"><SiteIllustration name="about" /><div className="space-y-6">{info.sections.map(([heading, points]) => <section key={heading}><h2 className="mb-4 text-2xl font-semibold">{heading}</h2><PointList points={points} /></section>)}</div></div><Link to="/product/" className="inline-flex items-center gap-2 font-medium text-brand">See the product<ArrowRight className="h-4 w-4" /></Link></>;
  if (page === 'changelog') return <><PageIntro title={info.title} description={info.description} eyebrow="Product direction" /><div className="max-w-4xl border-l border-brand/30 pl-6 sm:pl-10">{info.sections.map(([heading, points], index) => <section className="relative pb-8" key={heading}><span className="absolute -left-[30px] top-1.5 h-3 w-3 rounded-full border border-brand bg-background sm:-left-[46px]" /><p className="mb-3 text-xs uppercase tracking-widest text-brand">{index < 2 ? 'Current product' : 'Future work'}</p><h2 className="mb-5 text-2xl font-semibold">{heading}</h2><PointList points={points} /></section>)}</div><Button asChild variant="outline"><Link to="/feedback/">Share a suggestion</Link></Button></>;
  return <><div className="site-split-intro"><PageIntro title={info.title} description={info.description} eyebrow={page === 'security' ? 'Security' : 'Trust centre'} /><SiteIllustration name={page === "security" ? "security" : "trust"} /></div><div className="grid gap-6 md:grid-cols-2">{info.sections.map(([heading, points]) => <section className="site-card" key={heading}><h2 className="mb-5 text-xl font-semibold">{heading}</h2><PointList points={points} /></section>)}</div><nav className="mt-8 flex flex-wrap gap-x-7 gap-y-4" aria-label="Trust information">{[['Privacy', '/privacy-policy'], ['Terms', '/terms-of-service'], ['Refunds', '/refunds/'], ['Simulation assumptions', '/methodology/'], ['Report a concern', '/contact/?type=security']].map(([label, to]) => <Link className="text-sm text-brand underline underline-offset-4" key={to} to={to}>{label}</Link>)}</nav></>;
}

function FeatureDetail({ feature, features }) {
  return <><div className="site-split-intro"><div><Link to="/features/" className="site-eyebrow inline-block">All features / {feature.name}</Link><h1 className="mt-5 text-3xl font-semibold leading-tight tracking-tight sm:text-4xl lg:text-5xl">{feature.task}</h1><p className="mt-6 text-lg leading-8 text-muted-foreground">{feature.summary}</p><div className="mt-7 flex flex-wrap gap-3"><Button asChild><Link to="/register">Start Explore<ArrowRight className="h-4 w-4" /></Link></Button><Button asChild variant="outline"><Link to={feature.documentation}><BookOpen className="h-4 w-4" />Read the guide</Link></Button></div></div><SiteIllustration name={feature.code} /></div>
    <SectionTitle eyebrow="What you can do" title={`Work with ${feature.name.toLowerCase()}.`} /><div className="mt-8 grid gap-5 md:grid-cols-2">{feature.capabilities.map(([heading, body]) => <section className="site-card" key={heading}><h3 className="text-lg font-semibold">{heading}</h3><p className="mt-4 text-sm leading-7 text-muted-foreground">{body}</p></section>)}</div>
    <div className="my-8 grid gap-7 lg:grid-cols-[1.25fr_1fr]"><section><h2 className="mb-7 text-2xl font-semibold">How you use it</h2><ol className="space-y-6">{feature.steps.map((step, index) => <li className="flex items-start gap-4" key={step}><span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-brand/30 text-sm text-brand">{index + 1}</span><p className="text-sm leading-7 text-muted-foreground">{step}</p></li>)}</ol></section><div className="site-card space-y-6">{[['What you provide', feature.inputs], ['What you receive', feature.outputs]].map(([heading, body]) => <section key={heading}><h2 className="font-semibold">{heading}</h2><p className="mt-3 text-sm leading-7 text-muted-foreground">{body}</p></section>)}</div></div>
    <section className="rounded-2xl border border-brand/25 bg-brand/5 p-6"><h2 className="font-semibold">What to keep in mind</h2><p className="mt-3 text-sm leading-7 text-muted-foreground">{feature.limitations}</p></section><nav aria-label="Related features" className="mt-8 flex flex-wrap gap-4">{features.filter(item => item.code !== feature.code).slice(0, 3).map(item => <Link key={item.code} className="text-sm text-brand underline underline-offset-4" to={`/features/${item.code}/`}>{item.name}</Link>)}<Link className="text-sm text-brand" to="/pricing/">Compare plan allowances →</Link></nav>
  </>;
}

function PricingDetail() {
  const { catalog } = usePlatform();
  const limits = ['research_instruments', 'saved_screens', 'backtest_attachments', 'monte_carlo'];
  return <><PageIntro title={pageTitles.pricing} description="Explore the workflow for free. Add capacity when you need more strategies, tests, research or Paper practice." eyebrow="Workspace subscriptions" /><PricingCards />
    <section className="my-8 grid gap-6 md:grid-cols-3">{[['A backtest credit', 'One credit covers 100,000 instrument-candles, including warmup. You see an estimate before confirming a test.'], ['Monthly allowances', 'Explore resets each calendar month. Paid allowances follow your billing period. Unused allowances do not roll over.'], ['Paper capacity', 'Deployment and instrument limits apply to active capacity. Paused deployments count until stopped and settled.']].map(([heading, text]) => <article key={heading} className="rounded-2xl border p-6"><h2 className="font-semibold">{heading}</h2><p className="mt-4 text-sm leading-7 text-muted-foreground">{text}</p></article>)}</section>
    {catalog && <section className="site-card"><h2 className="mb-6 text-2xl font-semibold">A closer comparison</h2><div className="overflow-auto scrollbar-thin"><table className="site-comparison w-full min-w-[540px] text-sm"><caption className="sr-only">Additional public plan allowances</caption><thead><tr><th scope="col">Allowance</th>{Object.values(catalog.plans).map(plan => <th scope="col" key={plan.code}>{plan.name}</th>)}</tr></thead><tbody>{limits.map(key => <tr key={key}><th scope="row">{catalog.limit_labels[key]}</th>{Object.values(catalog.plans).map(plan => <td key={plan.code}>{plan.limits[key]}</td>)}</tr>)}</tbody></table></div></section>}
    <div className="mt-8 grid gap-6 sm:grid-cols-2">{[['Private installation', 'Your infrastructure, agreed modules and separately assessed Live support.', '/private/'], ['Custom development', 'A tool or integration scoped to your own process and deliverables.', '/custom-development/']].map(([heading, text, to]) => <Link className="site-card group" key={to} to={to}><h2 className="text-xl font-semibold">{heading}</h2><p className="my-4 text-sm leading-7 text-muted-foreground">{text}</p><span className="inline-flex items-center gap-2 text-brand">Learn more<ArrowRight className="h-4 w-4" /></span></Link>)}</div><p className="mt-6 text-sm text-muted-foreground">Review the <Link className="text-brand underline" to="/refunds/">refund policy</Link> and <Link className="text-brand underline" to="/docs/billing/">billing guide</Link> before purchasing.</p>
  </>;
}
GeneralContent.propTypes = { info: PropTypes.object.isRequired, page: PropTypes.string.isRequired };
FeatureDetail.propTypes = { feature: PropTypes.object.isRequired, features: PropTypes.array.isRequired };

export default function CustomerPages() {
  const { pathname } = useLocation();
  const { slug } = useParams();
  const { catalog, loading, error, refresh } = usePlatform();
  const page = pathname.split('/')[1];
  const features = getFeaturePages(catalog?.features);
  const feature = features.find(item => item.code === slug);
  const info = generalPages[page];
  const title = feature?.name || info?.title || pageTitles[page] || 'QuantNest';
  useEffect(() => {
    if (page === 'docs') return;
    document.title = `${title} · QuantNest`;
    const description = document.querySelector('meta[name="description"]');
    if (description) description.content = info?.description || feature?.summary || 'Software for your own trading logic. Explore QuantNest research, strategy building, testing, simulation and custom development.';
  }, [page, title, info, feature]);
  if (slug && !catalog) return <div className="site-page"><WorkspaceState loading={loading} error={error ? 'This feature could not load. Please try again.' : ''} onRetry={error ? refresh : undefined} /></div>;
  if (slug && !feature) return <NotFoundPage />;
  return <div className={`site-page site-appear site-page-${page}`}>
    {info && <GeneralContent info={info} page={page} />}
    {page === 'features' && (feature ? <FeatureDetail feature={feature} features={features} /> : <><div className="site-split-intro"><PageIntro title={title} description="Explore how each tool helps you investigate, define, test, practise or review your own trading logic." eyebrow="The complete toolkit" /><SiteIllustration name="toolkit" /></div><FeatureGrid /><p className="mt-8 text-sm leading-7 text-muted-foreground">Public plans cover the supported workflow through Paper simulation. <Link className="text-brand" to="/private/">Private Live</Link> needs a separate assessment. See <Link className="text-brand" to="/pricing/">plan allowances</Link> for usage limits.</p></>)}
    {page === 'pricing' && <PricingDetail />}
    {page === 'faq' && <><PageIntro title={title} description="Plans, simulations, supported markets and custom work—in plain language." eyebrow="Frequently asked questions" /><div className="grid items-start gap-7 lg:grid-cols-[1fr_300px]"><div>{faq.map(([question, answer]) => <details className="site-faq border-b py-6 first:pt-0" key={question}><summary className="cursor-pointer font-medium leading-7">{question}</summary><p className="mt-4 text-sm leading-7 text-muted-foreground">{answer}</p></details>)}</div><aside className="site-card"><MessageSquare className="h-6 w-6 text-brand" /><h2 className="mt-5 font-semibold">Have a different question?</h2><p className="my-4 text-sm leading-7 text-muted-foreground">Tell us about your workflow, account issue or project requirements.</p><Button asChild variant="outline"><Link to="/contact/">Contact QuantNest</Link></Button></aside></div></>}
    {(page === 'contact' || page === 'feedback') && <><PageIntro title={title} description={page === 'feedback' ? 'Describe what you are trying to do, what gets in the way and what would make it easier. Your suggestions help us prioritise improvements.' : 'Ask about a subscription, private installation, custom tool or account issue. Give us enough context to understand your request.'} eyebrow={page === 'feedback' ? 'Feedback & suggestions' : 'Contact & support'} /><div className="grid items-start gap-7 lg:grid-cols-[1.5fr_1fr]"><EnquiryForm feedback={page === 'feedback'} /><aside className="site-card"><h2 className="font-semibold">A direct way to reach us</h2>{catalog?.contact && <><a href={`mailto:${catalog.contact.email}`} className="mt-4 block break-all text-brand">{catalog.contact.email}</a><p className="mt-4 text-sm leading-7 text-muted-foreground">{catalog.contact.hours}</p></>}<div className="mt-6 border-t pt-6"><PointList points={['Include the page or workflow involved.', 'For a project, describe inputs and expected outputs.', 'Keep passwords, tokens and broker secrets out of your message.']} /></div><p className="mt-6 text-sm leading-7 text-muted-foreground">Signed-in customers can track requests and replies in their workspace.</p><Button asChild variant="outline" className="mt-5"><Link to="/support">Open workspace support</Link></Button></aside></div></>}
    {page === 'status' && <><PageIntro title={title} description="Find maintenance and service updates, or report a problem affecting your workspace." eyebrow="Service information" /><section className="site-card max-w-3xl"><h2 className="text-xl font-semibold">Service support and maintenance</h2><p className="mt-4 text-sm leading-7 text-muted-foreground">Check workspace notifications for maintenance notices. If a page is unavailable, contact support with the affected page, approximate time and what you expected to happen. We will reply through your support request during our published support hours.</p><Link className="mt-6 block text-brand" to="/contact/?type=support">Report a service issue →</Link></section></>}
    {page === 'docs' && <Documentation />}
  </div>;
}

```

## frontend/src/features/site/illustrations/PageIllustrations.jsx

```jsx
import { Activity, ArrowRight, BrainCircuit, Check, Code2, FileCheck2, FileText, FlaskConical, Layers3, LockKeyhole, MessageSquare, Monitor, Radio, Search, Server, ShieldCheck, SlidersHorizontal } from 'lucide-react';
import { Link } from 'react-router-dom';
import { ChoiceNote, FlowConnector, IllustrationFrame, IllustrationNode } from './IllustrationElements';

export function HomeIllustration() {
  return <IllustrationFrame name="home" title="Give your idea a place to develop" icon={Layers3}>
    <div className="site-workspace-map"><svg viewBox="0 0 400 260" preserveAspectRatio="none" aria-hidden="true"><path d="M90 40L200 130L310 40 M90 220L200 130L310 220" stroke="currentColor" strokeWidth="1.5" fill="none" strokeDasharray="6 9" className="site-flow-path" /></svg><Link to="/features/research/"><IllustrationNode icon={BrainCircuit} title="Research" detail="Explore a question" /></Link><Link to="/features/builder/"><IllustrationNode icon={SlidersHorizontal} title="Define" detail="Make rules explicit" /></Link><div className="site-map-centre"><span className="site-signal h-2 w-2 rounded-full bg-brand" /><p className="font-semibold">Your trading idea</p><span className="text-xs text-muted-foreground">Your logic. Your decisions.</span></div><Link to="/features/backtesting/"><IllustrationNode icon={FlaskConical} title="Test" detail="Check past behaviour" /></Link><Link to="/features/paper/"><IllustrationNode icon={Activity} title="Practise" detail="Use simulated capital" /></Link></div>
    <Link className="mt-4 flex items-center justify-between rounded-xl border bg-background px-4 py-3 text-sm" to="/features/journal/"><span className="flex items-center gap-2"><FileCheck2 className="h-4 w-4 text-brand" />Review, then refine</span><ArrowRight className="h-4 w-4 text-brand" /></Link>
  </IllustrationFrame>;
}

export function ProductIllustration() {
  return <IllustrationFrame name="product" title="Keep the whole investigation connected" icon={Layers3}>
    <div className="site-product-lanes">{[
      ['Your decisions', BrainCircuit, ['Questions', 'Saved rules']],
      ['Your experiments', FlaskConical, ['Historical tests', 'Paper practice']],
      ['Your review', FileCheck2, ['Recorded results', 'Private notes']],
    ].map(([title, Icon, items]) => <div className="site-product-lane" key={title}><div className="flex items-center gap-2 text-xs font-medium text-brand"><Icon className="h-4 w-4" />{title}</div><div className="mt-3 grid grid-cols-2 gap-2">{items.map(label => <span className="rounded-lg border bg-background px-3 py-3 text-xs" key={label}>{label}</span>)}</div></div>)}</div>
    <ChoiceNote label="What keeps your work connected" choices={[
      ['Context', 'Return to the question, instruments and evidence behind an investigation.'],
      ['Configuration', 'Saved tests and deployments retain the rules and assumptions used.'],
      ['Review', 'Keep Terminal, Paper and activated Private Live records separate.'],
    ]} />
  </IllustrationFrame>;
}

export function ToolkitIllustration() {
  return <IllustrationFrame name="toolkit" title="Start with the task you have" icon={Search}>
    <div className="site-toolkit-tiles">{[[BrainCircuit, 'Investigate', 'Research & screening', '/features/research/'], [SlidersHorizontal, 'Define', 'Rules & saved versions', '/features/builder/'], [Activity, 'Practise', 'Terminal & Paper', '/features/paper/'], [FileText, 'Review', 'Journal & reports', '/features/journal/']].map(([Icon, title, detail, to]) => <Link key={title} to={to} className="site-toolkit-tile"><Icon className="h-6 w-6 text-brand" /><p className="mt-4 text-sm font-semibold">{title}</p><p className="mt-1 text-xs text-muted-foreground">{detail}</p><ArrowRight className="mt-3 h-4 w-4 text-brand" /></Link>)}</div>
    <p className="mt-4 text-xs leading-6 text-muted-foreground">Choose a task here or explore the individual tools below.</p>
  </IllustrationFrame>;
}

export function ResearchIntroIllustration() {
  return <IllustrationFrame name="research-intro" title="See what supports an answer" icon={BrainCircuit}>
    <div className="site-research-stack"><IllustrationNode icon={MessageSquare} title="Your question" detail="Stocks, rules or recorded results" /><FlowConnector vertical /><div className="site-research-sources"><div><Layers3 className="h-5 w-5 text-brand" /><span>Relevant context</span></div><div><Search className="h-5 w-5 text-brand" /><span>Calculated evidence</span></div></div><FlowConnector vertical /><IllustrationNode icon={FileCheck2} title="A result you can inspect" detail="Read sources and observation times" /></div>
    <p className="mt-4 text-xs leading-6 text-muted-foreground">Follow up on the same idea. Confirm proposed changes before they happen.</p>
  </IllustrationFrame>;
}

export function PrivateIllustration() {
  return <IllustrationFrame name="private" title="Live trading in QuantNest Private" icon={Radio}>
    <div className="site-private-server"><div className="site-live-label"><Radio className="h-4 w-4" />SUPPORTED LIVE EXECUTION</div><Server className="mx-auto mt-4 h-12 w-12 text-brand" /><p className="mt-3 font-semibold">Your private installation</p><p className="mt-1 text-xs text-muted-foreground">Customer-owned execution infrastructure</p></div>
    <div className="site-private-route"><span>Your saved strategy</span><FlowConnector /><span>Supported broker</span></div>
    <ChoiceNote label="Private installation capabilities" choices={[
      ['Live trading', 'Execute your own rules through a supported broker after the deployment scope, broker access and applicable requirements are agreed and activation is complete.'],
      ['Full workspace', 'Include research, screening, strategy building, backtesting, Terminal, Paper, journal and reports in the agreed installation.'],
      ['Ongoing support', 'Agree updates, monitoring, backups, licensing and support responsibilities before setup.'],
    ]} />
  </IllustrationFrame>;
}

export function DevelopmentIllustration() {
  return <IllustrationFrame name="development" title="From your specification to useful software" icon={Code2}>
    <div className="site-development-blueprint"><span className="site-blueprint-corner" aria-hidden="true" /><div className="site-blueprint-spec"><Code2 className="h-7 w-7 text-brand" /><p className="mt-3 font-medium">Your requirements</p><p className="mt-1 text-xs text-muted-foreground">A tool for the way you work</p></div><div className="site-blueprint-io">{['Inputs', 'Required behaviour', 'Outputs'].map(label => <span key={label}>{label}</span>)}</div></div>
    <div className="site-delivery-milestones">{['Scope', 'Build', 'Verify', 'Handover'].map((label, index) => <div key={label}><span>0{index + 1}</span><p>{label}</p></div>)}</div>
    <ChoiceNote label="Development deliverables" choices={[
      ['Specification', 'Agree inputs, outputs, environments, ownership and acceptance criteria in writing.'],
      ['Verification', 'Check delivered software against the agreed behaviour at each acceptance milestone.'],
      ['Handover', 'Receive agreed deliverables and choose optional maintenance and support.'],
    ]} />
  </IllustrationFrame>;
}

export function AboutIllustration() {
  return <IllustrationFrame name="about" title="Understand the reasoning" icon={BrainCircuit}>
    <div className="site-about-compass"><svg viewBox="0 0 240 160" aria-hidden="true" className="w-full text-brand"><path d="M120 10L220 80L120 150L20 80Z M120 40L178 80L120 120L62 80Z" fill="none" stroke="currentColor" opacity=".35" /><circle cx="120" cy="80" r="20" fill="currentColor" opacity=".15" /><path d="M120 56V104 M96 80H144" stroke="currentColor" strokeWidth="2" /></svg><p className="text-center text-lg font-semibold">Your decisions. Their context.</p></div>
    <div className="mt-5 flex flex-wrap justify-center gap-2">{['Rules', 'Assumptions', 'Recorded outcomes'].map(label => <span className="rounded-full border bg-background px-3 py-2 text-xs" key={label}>{label}</span>)}</div>
    <p className="mt-5 text-center text-xs leading-6 text-muted-foreground">Software that makes your process easier to inspect.</p>
  </IllustrationFrame>;
}

export function TrustIllustration() {
  return <IllustrationFrame name="trust" title="Clear boundaries, visible context" icon={FileCheck2}>
    <div className="site-trust-layers"><IllustrationNode icon={SlidersHorizontal} title="Rules you choose" detail="Your logic and assumptions" /><IllustrationNode icon={FileCheck2} title="Results you can inspect" detail="Settings, observations and limits" /><IllustrationNode icon={LockKeyhole} title="Choices you control" detail="Sharing and privacy preferences" /></div>
    <p className="mt-5 flex items-start gap-2 text-xs leading-6 text-muted-foreground"><Check className="mt-1 h-4 w-4 shrink-0 text-brand" />Understand the software before choosing a plan or installation.</p>
  </IllustrationFrame>;
}

export function SecurityIllustration() {
  return <IllustrationFrame name="security" title="Protect access. Report concerns." icon={ShieldCheck}>
    <div className="site-security-boundary"><LockKeyhole className="h-12 w-12 text-brand" /><div><p className="font-semibold">Your account access</p><p className="mt-2 text-xs leading-6 text-muted-foreground">Password + second verification step</p></div></div>
    <div className="site-security-devices"><span><Monitor className="h-4 w-4 text-brand" />Review sign-ins</span><span><ShieldCheck className="h-4 w-4 text-brand" />Keep recovery codes private</span></div>
    <ChoiceNote label="Security help" choices={[
      ['Protect', 'Enable two-factor authentication and revoke sign-in sessions you do not recognise.'],
      ['Report', 'Send a security concern through Contact, without passwords, tokens or other people’s data.'],
      ['Private access', 'Agree support access scope and expiry for a Private installation.'],
    ]} />
  </IllustrationFrame>;
}

```

## frontend/src/features/site/PricingCards.jsx

```jsx
import { formatCurrency } from "@/shared/utils/formatters";
import { Link } from "react-router-dom";
import { Check, ArrowRight } from "lucide-react";
import { usePlatform } from "@/shared/context/platform";
import WorkspaceState from "@/shared/components/WorkspaceState";
import { Button } from "@/shared/components/ui/button";
import PlanMarkets from "@/shared/components/PlanMarkets";

const highlights = [
  "strategies",
  "backtest_credits",
  "research_turns",
  "screens",
  "paper_deployments",
  "paper_instruments",
];
export default function PricingCards() {
  const { catalog, loading, error, refresh } = usePlatform();
  if (!catalog || error)
    return (
      <WorkspaceState
        loading={loading}
        error={error ? "Current plans could not be loaded. Please retry." : ""}
        onRetry={refresh}
      />
    );
  return (
    <>
      <div className="grid gap-4 lg:grid-cols-3">
        {Object.values(catalog.plans).map((plan) => (
          <article
            key={plan.code}
            className={`relative flex flex-col rounded-3xl border bg-card p-5 sm:p-6 ${plan.code === "build" ? "border-brand/50 shadow-[0_0_45px_-20px_hsl(var(--brand)/.3)]" : ""}`}
          >
            <p className="text-xs uppercase tracking-widest text-brand">
              {plan.code === "explore"
                ? "Discover the workflow"
                : plan.code === "build"
                  ? "Develop your practice"
                  : "More room to investigate"}
            </p>
            <h3 className="mt-3 text-2xl font-semibold">{plan.name}</h3>
            <p className="mt-4 text-4xl font-semibold">
              {plan.price_minor
                ? `${formatCurrency(plan.price_minor / 100, { minimumFractionDigits: 0 })}`
                : "Free"}
            </p>
            <p className="mt-2 text-xs text-muted-foreground">
              {plan.price_minor
                ? "per month + applicable tax"
                : "allowances per calendar month"}
            </p>
            <section className="my-5 border-y py-4">
              <h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Markets
              </h4>
              <PlanMarkets markets={plan.markets} />
            </section>
            <ul className="mb-5 space-y-3">
              {highlights.map((key) => (
                <li
                  key={key}
                  className="flex items-center justify-between gap-3 text-sm"
                >
                  <span className="flex items-center gap-2 text-muted-foreground">
                    <Check className="h-4 w-4 shrink-0 text-brand" />
                    {catalog.limit_labels[key]}
                  </span>
                  <strong>{plan.limits[key]}</strong>
                </li>
              ))}
            </ul>
            <p className="mb-5 text-sm leading-6 text-muted-foreground">
              Terminal, journal, reports, versions and account security are included.
            </p>
            <Button
              asChild
              className="mt-auto w-full rounded-full"
              variant={plan.code === "build" ? "default" : "outline"}
            >
              <Link
                to={
                  plan.code === "explore"
                    ? "/register"
                    : `/settings/billing?plan=${plan.code}`
                }
              >
                {plan.code === "explore"
                  ? "Start Explore"
                  : `Review ${plan.name}`}
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </article>
        ))}
      </div>
      <p className="mt-4 text-sm leading-7 text-muted-foreground">
        All public plans support NSE-stock workflows through Paper simulation.
        Futures and options are coming soon in Build and Pro; they are not
        available today and have no announced release date. Upgrading today adds
        capacity for current features. Review your workspace allowances
        before upgrading for a specific task. No rollover or automatic
        paid overages.
      </p>
      <p className="mt-2 text-sm leading-7 text-muted-foreground">
        <Link
          className="text-brand font-medium underline underline-offset-4"
          to="/private/"
        >
          Live trading is supported in QuantNest Private
        </Link>
        , after the installation and supported broker setup are agreed and
        activated. Public plans do not include Live execution.
      </p>
    </>
  );
}

```

## frontend/src/features/site/SiteFooter.jsx

```jsx
import { Link } from 'react-router-dom';
import { usePlatform } from '@/shared/context/platform';

const groups = {
  Workspace: [['Product', '/product/'], ['All features', '/features/'], ['Pricing', '/pricing/'], ['Documentation', '/docs/'], ['FAQ', '/faq/']],
  Company: [['About', '/about/'], ['Custom development', '/custom-development/'], ['Private', '/private/'], ['Contact & support', '/contact/'], ['Feedback', '/feedback/'], ['Changelog', '/changelog/'], ['Status', '/status/']],
  Trust: [['Trust centre', '/trust/'], ['Privacy', '/privacy-policy'], ['Terms', '/terms-of-service'], ['Refunds', '/refunds/'], ['Simulation & data', '/methodology/'], ['Security', '/security/']],
};
export default function SiteFooter() {
  const { catalog } = usePlatform();
  const contact = catalog?.contact;
  return <footer className="border-t bg-background"><div className="mx-auto w-[calc(100%_-_2rem)] max-w-7xl py-8">
    <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-[1.5fr_1fr_1fr_1fr]">
      <div><Link to="/" aria-label="QuantNest home"><img src="/logo_1-wordmark.png" alt="QuantNest" className="h-10 w-auto" /></Link><p className="my-5 max-w-sm text-sm leading-7 text-muted-foreground">Software for your own logic. Research, testing, simulation and review in one connected workspace.</p>{contact && <><a href={`mailto:${contact.email}`} className="break-all text-sm text-brand">{contact.email}</a><p className="mt-3 text-xs leading-6 text-muted-foreground">{contact.hours}</p></>}</div>
      {Object.entries(groups).map(([title, links]) => <nav key={title} aria-label={title}><h2 className="mb-4 text-sm font-semibold">{title}</h2><ul className="space-y-3">{links.map(([label, href]) => <li key={href}><Link className="text-sm text-muted-foreground transition-colors hover:text-brand" to={href}>{label}</Link></li>)}</ul></nav>)}
    </div><div className="mt-10 border-t pt-6 text-xs leading-6 text-muted-foreground"><p>QuantNest provides software, not investment advice or assured returns. Backtest and Paper results are simulations. Public plans cover simulation through Paper. Private Live requires separate qualification.</p>{contact && <p className="mt-3">© {new Date().getFullYear()} {contact.name}. All rights reserved.</p>}</div>
  </div></footer>;
}

```

## frontend/src/features/site/config.js

```jsx
export const brand = {
  site: import.meta.env.VITE_SITE_URL || "https://quantnest.site",
  turnstile: import.meta.env.VITE_TURNSTILE_SITE_KEY || "",
};
export const faq = [
  ["Does QuantNest give me trading strategies or investment advice?", "You choose your trading rules. QuantNest provides tools to define, test, simulate and review them. It does not provide a profitable-strategy catalogue, trading signals or discretionary account management."],
  ["Can I start without paying?", "Explore is free and includes small allowances for the supported public workflow. You can build rules, test ideas, research and practise within the limits of your plan. Some data-dependent and AI features may have restricted availability; check your workspace before upgrading for a specific task."],
  ["Does a public plan include Live trading?", "Live trading is supported in QuantNest Private with your own strategy logic and an agreed supported broker setup. It is activated after deployment assessment and applicable requirements are addressed. Public subscriptions cover simulation through Paper and do not activate Live."],
  ["Do unused credits roll over?", "No. Explore resets by calendar month in Asia/Kolkata. Paid allowances reset at the verified billing-period boundary. There are no automatic paid overages."],
  ["What happens if I cancel or don't renew?", "Cancellation disables future renewal while preserving the current paid period. Existing work remains available. New over-limit activity is restricted. Paper requires explicit resumption within your current limits; reductions and protective controls remain available."],
  ["Are backtests and Paper results actual broker results?", "No. Historical candles and observed-price simulation cannot reproduce exchange queues, all partial fills, market impact or broker latency. Costs, slippage, coverage and assumptions should be reviewed."],
  ["What is the refund policy?", "The first paid Workspace purchase has a seven-day refund window, alongside applicable remedies. Custom Development and Private have separately agreed terms. Submit a request from Billing and Usage."],
  ["Which markets can I work with?", "Explore, Build and Pro currently support NSE stocks. NSE futures and options are coming soon in Build and Pro, with no announced release date; they are not available for use today. Pro adds greater usage capacity. Public plans cover simulation; supported Live execution belongs to an activated Private installation."],
  ["Can you build a tool to my specifications?", "Yes. Request a scoped research, testing, reporting or integration project. Specifications, acceptance criteria, ownership, costs and maintenance are agreed before development."],
];

```

## frontend/src/pages/LandingPage.jsx

```jsx
import { useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ArrowRight, Check, Code2, LockKeyhole, Sparkles } from 'lucide-react';
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
    if (description) description.content = 'Research your own trading ideas, build rules, backtest and practise in Paper. Explore QuantNest subscriptions, private installations and custom software development.';
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
            <p className="mt-6 max-w-lg text-xs leading-6 text-muted-foreground">For supported NSE cash-stock workflows. Public plans cover simulation through Paper; Live needs a separate Private assessment.</p>
          </div>
          <div className="site-hero-visual relative min-w-0"><SiteIllustration name="home" /><div className="site-visual-caption mt-4 flex justify-between gap-3 px-2 text-xs text-muted-foreground"><span>From the first question to the next iteration</span><span className="shrink-0 text-brand">Built around your logic</span></div></div>
        </div>
      </section>

      <section className="site-home-section" id="workflow"><div className="site-container"><SectionTitle eyebrow="The connected workflow" title="Less scattered work. More context." description="Each step keeps the question, configuration and recorded outcome connected, so you can understand what you tested and why." />
        <ol className="mt-7 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">{journey.map(([title, detail, to], index) => <li key={title}><Link to={to} className="group block h-full rounded-2xl border bg-card p-5"><div className="flex items-center justify-between text-brand"><span className="text-xs font-semibold">0{index + 1}</span><ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" /></div><h3 className="mt-5 font-semibold">{title}</h3><p className="mt-3 text-sm leading-7 text-muted-foreground">{detail}</p></Link></li>)}</ol>
      </div></section>

      <section className="site-home-section border-y bg-muted/30" id="features"><div className="site-container"><div className="mb-7 flex flex-col justify-between gap-5 md:flex-row md:items-end"><SectionTitle eyebrow="Inside your workspace" title="Choose your next task." description="Explore every part of QuantNest, from your first research question to a detailed review of recorded results." /><Link to="/features/" className="flex shrink-0 items-center gap-2 text-sm font-medium text-brand">All features<ArrowRight className="h-4 w-4" /></Link></div><FeatureGrid /></div></section>

      <section className="site-home-section" id="research"><div className="site-container grid items-center gap-8 lg:grid-cols-2 lg:gap-12"><SiteIllustration name="research-intro" /><div><SectionTitle eyebrow="Research with context" title="Keep asking better questions." description="Use the assistant to investigate your own ideas, inspect supporting calculations and understand the results you already have." /><div className="my-7"><PointList points={['Attach selected stocks, a watchlist, your strategy or completed backtests.', 'Open sources and observation times instead of taking a written answer at face value.', 'Refine a draft in conversation and confirm it before anything is created or started.']} /></div><Link to="/features/research/" className="inline-flex items-center gap-2 font-medium text-brand">Explore AI research<ArrowRight className="h-4 w-4" /></Link></div></div></section>

      <section className="site-home-section border-y bg-muted/30" id="services"><div className="site-container"><SectionTitle eyebrow="Beyond the public workspace" title="Need a different kind of setup?" description="Choose a private installation or a scoped development project when your requirements go beyond a public subscription." /><div className="mt-7 grid gap-6 md:grid-cols-2">
        <article className="site-service-card site-card"><LockKeyhole className="h-7 w-7 text-brand" /><h3 className="mt-6 text-2xl font-semibold">QuantNest Private</h3><p className="mt-4 text-sm leading-7 text-muted-foreground">Supported Live trading for your own strategy logic in a customer-owned installation, alongside the agreed research, testing and review modules.</p><div className="my-6"><PointList points={['Agree hosting, access, backups and updates before setup.', 'Agree the supported broker connection and applicable requirements before Live activation.']} /></div><Button asChild variant="outline" className="rounded-full"><Link to="/private/">Explore Private<ArrowRight className="h-4 w-4" /></Link></Button></article>
        <article className="site-service-card site-card"><Code2 className="h-7 w-7 text-brand" /><h3 className="mt-6 text-2xl font-semibold">Custom software development</h3><p className="mt-4 text-sm leading-7 text-muted-foreground">Research utilities, testing tools, reports and integrations built around your own process and specification.</p><div className="my-6"><PointList points={['Agree inputs, deliverables, acceptance criteria and ownership.', 'Work through clear milestones, handover and optional maintenance.']} /></div><Button asChild variant="outline" className="rounded-full"><Link to="/custom-development/">Explore development services<ArrowRight className="h-4 w-4" /></Link></Button></article>
      </div></div></section>

      <section className="site-home-section" id="pricing"><div className="site-container"><div className="mb-7"><SectionTitle eyebrow="Simple workspace plans" title="Start small. Add room when you need it." description="Explore the public workflow with limited free usage. Choose Build or Pro when you need more saved strategies, tests, research and Paper capacity." /></div><PricingCards /><Link to="/pricing/" className="mt-6 inline-flex items-center gap-2 text-sm text-brand">Understand credits and compare plans<ArrowRight className="h-4 w-4" /></Link></div></section>

      <section className="site-home-section border-t" id="faq"><div className="site-container grid gap-10 lg:grid-cols-[.8fr_1.2fr]"><div><SectionTitle eyebrow="Before you begin" title="A few useful answers." description="Know what is included and what simulated results can tell you." /><Link to="/faq/" className="mt-6 inline-flex items-center gap-2 text-sm text-brand">Read all FAQs<ArrowRight className="h-4 w-4" /></Link><Link to="/docs/" className="mt-4 block text-sm text-brand">Read the user guides →</Link></div><div>{faq.slice(0, 5).map(([question, answer]) => <details className="site-faq border-b py-5 first:pt-0" key={question}><summary className="cursor-pointer text-base font-medium leading-7">{question}</summary><p className="mt-4 text-sm leading-7 text-muted-foreground">{answer}</p></details>)}</div></div></section>

      <section className="site-container pb-10 sm:pb-16"><div className="site-closing-panel relative overflow-hidden rounded-3xl border border-brand/30 bg-brand/5 px-6 py-8 text-center sm:px-12"><p className="site-eyebrow">A place to start thinking clearly</p><h2 className="mt-5 text-3xl font-semibold tracking-tight sm:text-4xl">Bring your idea. Keep the decisions yours.</h2><p className="mx-auto mt-5 max-w-2xl text-base leading-8 text-muted-foreground">Create a workspace for your own research and rules, or tell us about the software you need.</p><div className="mt-7 flex flex-wrap justify-center gap-3"><Button asChild size="lg" className="rounded-full"><Link to="/register">Create your workspace<ArrowRight className="h-4 w-4" /></Link></Button><Button asChild variant="outline" size="lg" className="rounded-full"><Link to="/contact/">Talk to QuantNest</Link></Button></div></div></section>
    </main><SiteFooter /><SiteEffects />
  </div>;
}

```

## frontend/src/features/site/content/docs/private.md

```markdown
---
title: Private Installation
description: Agree the setup, responsibilities, support and licence behaviour.
order: 11
---
## Agree your installation

- Private supports Live trading of your own strategy logic through an agreed supported broker connection.
- Live is activated after the installation, broker access and applicable requirements are reviewed. It is not enabled by buying a public plan.

- Define workflows, hosting responsibilities, supported brokers/releases and licence validity in writing. Software usage, users and broker-account counts have no subscription quota while the licence is active.
- Review setup fees, support allowance, licensing and third-party costs.
- Live activation is separately assessed. Customer-owned hosting is not a regulatory exemption.

## Deploy and manage Live strategies

Deploy from **My Strategies**: select a saved version, a verified broker account
and a capital amount. One strategy can have separate sessions on different broker
accounts. The same strategy cannot create another session on the same account;
use its existing deployment to start, pause, stop or change version/capital.

**Live Trading → Deployments** lists sessions and filters them by status.
Capital and version updates reach a running session automatically. Existing
positions keep their quantities, and version changes must retain their instruments.
The Portfolio page shows strategy results; account setup stays in Broker Integration.

## Assign responsibilities

- Decide who manages infrastructure, access, updates, monitoring, backups and recovery.
- Keep credentials and trading records in the installation.
- Review external AI processing before enabling it.
- Follow the setup/runbook supplied for your accepted deployment; do not expose internal services publicly.

## Licence and renewal

- Renewable installations verify a signed licence and refresh it periodically. Your agreement defines expiry and any bounded connectivity-outage allowance.
- Expiry restricts new user-initiated deployments, resumes and other licensed work. Running strategies have no background expiry check and continue until paused/stopped or blocked by execution controls. Monitoring, reconciliation and exports remain available.
- After renewal, an administrator enables new work in the licence panel. Resume paused/stopped sessions explicitly. Purchased perpetual continuing-use rights and maintenance expiry follow their separate terms.

## Operate safely

- Back up records and required installation state. Test recovery and release rollback before execution-affecting changes.
- Grant support access only for an agreed scope and expiry.
- Set your strategy's entry window and exit rules separately. End time stops new entries; close positions through exit rules or an explicit stop with position closure. Live P&L displays recorded price gains/losses before broker charges; check final fees against broker statements.
- Contact support with installation context and the affected workflow, keeping secrets out of messages.

```