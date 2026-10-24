import { useEffect } from 'react';
import PropTypes from 'prop-types';
import { Link, useLocation, useParams } from 'react-router-dom';
import { ArrowRight, BookOpen, Code2, LockKeyhole, MessageSquare } from 'lucide-react';
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
    return <><div className="site-split-intro"><div><div>{!custom && <p className="site-eyebrow">Not available for purchase</p>}<PageIntro title={info.title} description={info.description} eyebrow={custom ? 'Custom software development' : 'QuantNest Private'} /></div><Button asChild size="lg" className="mb-8 rounded-full"><Link to={`/contact/?type=${info.kind}`}>{info.cta}<ArrowRight className="h-4 w-4" /></Link></Button></div><SiteIllustration name={custom ? 'development' : 'private'} /></div>
      <div className="grid items-start gap-7 lg:grid-cols-[1fr_300px]"><div className="space-y-6">{info.sections.map(([heading, points], index) => <section key={heading} className="grid gap-4 border-t pt-5 sm:grid-cols-[45px_1fr]"><span className="text-sm font-semibold text-brand">0{index + 1}</span><div><h2 className="mb-5 text-xl font-semibold">{heading}</h2><PointList points={points} /></div></section>)}</div><aside className="site-card h-fit lg:sticky lg:top-28"><Icon className="h-7 w-7 text-brand" /><h2 className="mb-5 mt-5 font-semibold">What to send in your enquiry</h2><PointList points={custom ? ['The task you want to complete.', 'Your inputs and expected outputs.', 'Existing tools, constraints and desired timing.'] : ['Your question about availability.', 'The workflow you are interested in.', 'Please do not send broker credentials.']} /><Button asChild className="mt-6 w-full"><Link to={`/contact/?type=${info.kind}`}>Start the conversation</Link></Button></aside></div>
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
    <div className="mt-8 grid gap-6 sm:grid-cols-2">{[['Custom development', 'A tool or integration scoped to your own process and deliverables.', '/custom-development/']].map(([heading, text, to]) => <Link className="site-card group" key={to} to={to}><h2 className="text-xl font-semibold">{heading}</h2><p className="my-4 text-sm leading-7 text-muted-foreground">{text}</p><span className="inline-flex items-center gap-2 text-brand">Learn more<ArrowRight className="h-4 w-4" /></span></Link>)}</div><p className="mt-6 text-sm text-muted-foreground">Review the <Link className="text-brand underline" to="/refunds/">refund policy</Link> and <Link className="text-brand underline" to="/docs/billing/">billing guide</Link> before purchasing.</p>
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
    {page === 'features' && (feature ? <FeatureDetail feature={feature} features={features} /> : <><div className="site-split-intro"><PageIntro title={title} description="Explore how each tool helps you investigate, define, test, practise or review your own trading logic." eyebrow="The complete toolkit" /><SiteIllustration name="toolkit" /></div><FeatureGrid /><p className="mt-8 text-sm leading-7 text-muted-foreground">Public plans cover the supported workflow through Paper simulation. Customer Live trading is not currently available. See <Link className="text-brand" to="/pricing/">plan allowances</Link> for usage limits.</p></>)}
    {page === 'pricing' && <PricingDetail />}
    {page === 'faq' && <><PageIntro title={title} description="Plans, simulations, supported markets and custom work—in plain language." eyebrow="Frequently asked questions" /><div className="grid items-start gap-7 lg:grid-cols-[1fr_300px]"><div>{faq.map(([question, answer]) => <details className="site-faq border-b py-6 first:pt-0" key={question}><summary className="cursor-pointer font-medium leading-7">{question}</summary><p className="mt-4 text-sm leading-7 text-muted-foreground">{answer}</p></details>)}</div><aside className="site-card"><MessageSquare className="h-6 w-6 text-brand" /><h2 className="mt-5 font-semibold">Have a different question?</h2><p className="my-4 text-sm leading-7 text-muted-foreground">Tell us about your workflow, account issue or project requirements.</p><Button asChild variant="outline"><Link to="/contact/">Contact QuantNest</Link></Button></aside></div></>}
    {(page === 'contact' || page === 'feedback') && <><PageIntro title={title} description={page === 'feedback' ? 'Describe what you are trying to do, what gets in the way and what would make it easier. Your suggestions help us prioritise improvements.' : 'Ask about a subscription, custom project, tool or account issue. Give us enough context to understand your request.'} eyebrow={page === 'feedback' ? 'Feedback & suggestions' : 'Contact & support'} /><div className="grid items-start gap-7 lg:grid-cols-[1.5fr_1fr]"><EnquiryForm feedback={page === 'feedback'} /><aside className="site-card"><h2 className="font-semibold">A direct way to reach us</h2>{catalog?.contact && <><a href={`mailto:${catalog.contact.email}`} className="mt-4 block break-all text-brand">{catalog.contact.email}</a><p className="mt-4 text-sm leading-7 text-muted-foreground">{catalog.contact.hours}</p></>}<div className="mt-6 border-t pt-6"><PointList points={['Include the page or workflow involved.', 'For a project, describe inputs and expected outputs.', 'Keep passwords, tokens and broker secrets out of your message.']} /></div><p className="mt-6 text-sm leading-7 text-muted-foreground">Signed-in customers can track requests and replies in their workspace.</p><Button asChild variant="outline" className="mt-5"><Link to="/support">Open workspace support</Link></Button></aside></div></>}
    {page === 'status' && <><PageIntro title={title} description="Find maintenance and service updates, or report a problem affecting your workspace." eyebrow="Service information" /><section className="site-card max-w-3xl"><h2 className="text-xl font-semibold">Service support and maintenance</h2><p className="mt-4 text-sm leading-7 text-muted-foreground">Check workspace notifications for maintenance notices. If a page is unavailable, contact support with the affected page, approximate time and what you expected to happen. We will reply through your support request during our published support hours.</p><Link className="mt-6 block text-brand" to="/contact/?type=support">Report a service issue →</Link></section></>}
    {page === 'docs' && <Documentation />}
  </div>;
}
