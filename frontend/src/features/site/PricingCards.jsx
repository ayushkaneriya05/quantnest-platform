import { Fragment } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Check, Minus, Server } from 'lucide-react';
import { formatCurrencyMinorUnits, formatNumber } from '@/shared/utils/formatters';
import { usePlatform } from '@/shared/context/platform';
import WorkspaceState from '@/shared/components/WorkspaceState';
import { Button } from '@/shared/components/ui/button';
import PlanMarkets from '@/shared/components/PlanMarkets';

const highlights = ['strategies', 'backtest_credits', 'research_tokens', 'screens', 'paper_deployments', 'paper_instruments'];
const introductions = { explore: 'Discover the workflow', build: 'Develop your practice', pro: 'More room to investigate' };
const allowanceGroups = [
  ['period', 'Period allowances'], ['inventory', 'Saved and deployed capacity'], ['per_request', 'Per-request limits'],
];

export default function PricingCards() {
  const { catalog, loading, error, refresh } = usePlatform();
  if (!catalog || error) return <WorkspaceState loading={loading} error={error ? 'Current plans could not be loaded. Please retry.' : ''} onRetry={refresh} />;
  const offers = [...Object.values(catalog.plans), catalog.private_offer];
  return <>
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
      {offers.map(offer => {
        const quoted = offer.pricing_type === 'contact';
        return <article key={offer.code} className={`flex min-w-0 flex-col rounded-2xl border bg-card p-4 ${offer.code === 'build' ? 'border-brand/50' : ''}`}>
          <p className="text-xs font-medium text-brand">{quoted ? 'Your dedicated workspace' : introductions[offer.code]}</p>
          <h3 className="mt-2 text-xl font-semibold">{offer.name}</h3>
          <p className="mt-3 text-3xl font-semibold tracking-tight">{quoted ? 'Custom pricing' : offer.price_minor === 0 ? 'Free' : formatCurrencyMinorUnits(offer.price_minor)}</p>
          <p className="mt-1 text-xs text-muted-foreground">{quoted ? 'Available on request · quotation agreed directly' : offer.price_minor === 0 ? 'allowances per calendar month' : 'per month + applicable tax'}</p>
          <section className="my-4 border-y py-3">
            <h4 className="mb-2 text-xs font-semibold text-muted-foreground">{quoted ? 'Managed deployment' : 'Simulation markets'}</h4>
            {quoted ? <p className="flex items-start gap-2 text-sm"><Server className="mt-0.5 h-4 w-4 shrink-0 text-brand" />{offer.description}</p> : <PlanMarkets markets={offer.markets} />}
          </section>
          {quoted ? <>
            <ul className="space-y-2.5 text-sm">{catalog.features.filter(feature => feature.included_in.length === 1 && feature.included_in.includes(offer.code)).map(feature => <li key={feature.code} className="flex items-center gap-2"><Check className="h-4 w-4 shrink-0 text-brand" />{feature.name}</li>)}</ul>
            <p className="mt-3 text-sm text-muted-foreground">Includes the research, testing, simulation and review workspace. Supported broker: {catalog.brokers.map(broker => broker.name).join(', ')}.</p>
            <p className="my-4 text-xs leading-5 text-muted-foreground">{offer.capacity_note}</p>
          </> : <>
            <ul className="space-y-2.5">{highlights.map(key => <li key={key} className="flex items-start justify-between gap-2 text-sm"><span className="text-muted-foreground">{catalog.limit_labels[key]}</span><strong className="shrink-0 tabular-nums">{formatNumber(offer.limits[key] / catalog.limit_divisors[key])}</strong></li>)}</ul>
            <p className="my-4 text-xs leading-5 text-muted-foreground">Research, testing and simulation within your plan allowances. Compare included features on Pricing. Broker connections and Live execution use Private.</p>
          </>}
          {quoted && <Link className="mb-3 text-center text-xs text-brand underline underline-offset-4" to="/private/">See how Private works</Link>}
          <Button asChild className="mt-auto w-full" variant={offer.code === 'build' ? 'default' : 'outline'}>
            <Link to={quoted ? offer.cta_url : offer.code === 'explore' ? '/register' : `/settings/billing?plan=${offer.code}`}>
              {quoted ? offer.cta_label : offer.code === 'explore' ? 'Start Explore' : `Review ${offer.name}`}<ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
        </article>;
      })}
    </div>
    <p className="mt-3 text-xs leading-6 text-muted-foreground">Public plans include NSE stocks, futures and options for backtesting, manual Terminal simulation and automated Paper. AI stock analysis and screening focus on active NSE stocks. Contract history affects what you can test. One AI credit equals 1,000 reported tokens; successful answers use actual tokens. Failed or cancelled requests use no credits. No rollover or automatic paid overages.</p>
  </>;
}

export function PricingComparison() {
  const { catalog } = usePlatform();
  if (!catalog) return null;
  const offers = [...Object.values(catalog.plans), catalog.private_offer];
  const rowLabel = 'sticky left-0 z-10 min-w-48 bg-card px-3 py-2.5 text-left font-medium';
  return <section className="mt-6" aria-labelledby="plan-comparison-title">
    <h2 id="plan-comparison-title" className="text-xl font-semibold">Compare features and allowances</h2>
    <p className="mb-3 mt-1 text-sm text-muted-foreground">Choose the capacity you need, or a dedicated Private workspace for broker-connected Live strategies.</p>
    <div tabIndex={0} role="region" aria-label="Plan feature and allowance comparison" className="relative min-w-0 max-w-full overflow-x-auto rounded-xl border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
      <table className="w-full min-w-[800px] border-collapse text-sm">
        <caption className="sr-only">QuantNest features and all allowances for Explore, Build, Pro and Private</caption>
        <thead><tr className="border-b bg-muted/30"><th scope="col" className={rowLabel}>Functionality</th>{offers.map(offer => <th key={offer.code} scope="col" className="min-w-32 px-3 py-3 text-center font-semibold">{offer.name}</th>)}</tr></thead>
        <tbody>
          {catalog.features.map(feature => <tr key={feature.code} className="border-b"><th scope="row" className={rowLabel}><Link className="hover:text-brand" to={`/features/${feature.code}/`}>{feature.name}</Link></th>{offers.map(offer => {
            const included = feature.included_in.includes(offer.code);
            const Icon = included ? Check : Minus;
            return <td key={offer.code} className="px-3 py-2.5 text-center"><Icon aria-hidden="true" className={`mx-auto h-4 w-4 ${included ? 'text-success' : 'text-muted-foreground'}`} /><span className="sr-only">{included ? 'Included' : 'Not included'}</span></td>;
          })}</tr>)}
          {allowanceGroups.map(([kind, title]) => <Fragment key={kind}>
            <tr className="border-b bg-muted/30"><th colSpan={offers.length + 1} className="px-3 py-2 text-left text-xs font-semibold text-muted-foreground">{title}</th></tr>
            {Object.entries(catalog.limit_labels).filter(([key]) => catalog.limit_kinds[key] === kind).map(([key, label]) => <tr key={key} className="border-b last:border-b-0">
              <th scope="row" className={rowLabel}>{label}</th>
              {offers.map(offer => <td key={offer.code} className="px-3 py-2.5 text-center tabular-nums">{offer.pricing_type === 'contact' ? <span className="text-xs text-muted-foreground">No public-plan quota</span> : formatNumber(offer.limits[key] / catalog.limit_divisors[key])}</td>)}
            </tr>)}
          </Fragment>)}
        </tbody>
      </table>
    </div>
    <p className="mt-2 text-xs leading-5 text-muted-foreground">{catalog.private_offer.capacity_note} Terminal remains simulated in every offering. Private includes automated Live strategy execution.</p>
  </section>;
}
