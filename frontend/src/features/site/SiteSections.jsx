import { Link } from 'react-router-dom';
import PropTypes from 'prop-types';
import { Activity, ArrowRight, BrainCircuit, FileText, FlaskConical, Search, ShieldCheck, SlidersHorizontal, Terminal } from 'lucide-react';
import { getFeaturePages } from './content/features';
import { usePlatform } from '@/shared/context/platform';
import WorkspaceState from '@/shared/components/WorkspaceState';

const icons = { research: BrainCircuit, screener: Search, builder: SlidersHorizontal, backtesting: FlaskConical, terminal: Terminal, paper: Activity, journal: FileText, controls: ShieldCheck };
export function SectionTitle({ eyebrow, title, description }) {
  return <div className="max-w-3xl"><p className="site-eyebrow">{eyebrow}</p><h2 className="mt-4 text-3xl font-semibold tracking-tight sm:text-4xl lg:text-5xl">{title}</h2>{description && <p className="mt-5 text-base leading-8 text-muted-foreground sm:text-lg">{description}</p>}</div>;
}
export function FeatureGrid() {
  const { catalog, loading, error, refresh } = usePlatform();
  if (!catalog) return <WorkspaceState loading={loading} error={error ? 'Features could not load. Please try again.' : ''} onRetry={error ? refresh : undefined} />;
  return <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{getFeaturePages(catalog.features).map((feature, index) => {
    const Icon = icons[feature.code];
    return <Link key={feature.code} to={`/features/${feature.code}/`} className="site-feature-card group flex flex-col rounded-2xl border bg-card p-6 transition-all hover:-translate-y-1 hover:border-brand/50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand">
      <div className="flex items-center justify-between"><span className="flex h-11 w-11 items-center justify-center rounded-xl border border-brand/20 bg-brand/10"><Icon className="h-5 w-5 text-brand" /></span><span className="text-xs text-muted-foreground">{`0${index + 1}`}</span></div><h3 className="mb-3 mt-6 text-lg font-semibold">{feature.name}</h3><p className="mb-6 text-sm leading-7 text-muted-foreground">{feature.summary}</p><span className="mt-auto inline-flex items-center gap-2 text-sm font-medium text-brand">Explore feature<ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" /></span>
    </Link>;
  })}</div>;
}
export function PointList({ points }) {
  return <ul className="space-y-3">{points.map(point => <li key={point} className="flex items-start gap-3 text-sm leading-7 text-muted-foreground"><span className="mt-3 h-1.5 w-1.5 shrink-0 rounded-full bg-brand" /><span>{point}</span></li>)}</ul>;
}
SectionTitle.propTypes = { eyebrow: PropTypes.string.isRequired, title: PropTypes.string.isRequired, description: PropTypes.string };
PointList.propTypes = { points: PropTypes.arrayOf(PropTypes.string).isRequired };
