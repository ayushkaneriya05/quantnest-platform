import { LoaderMark } from '@/shared/components/ui/global-loader';
import PropTypes from 'prop-types';
import { AlertCircle, Inbox } from 'lucide-react';
import { Button } from './ui/button';

export default function WorkspaceState({ loading = false, error = '', title, description, onRetry }) {
  const Icon = loading ? LoaderMark : error ? AlertCircle : Inbox;
  return <div role={error ? 'alert' : loading ? 'status' : undefined} className="rounded-xl border bg-card p-5">
    <div className="flex items-start gap-3"><Icon className={`mt-0.5 h-5 w-5 shrink-0 ${loading ? 'text-brand' : error ? 'text-destructive-text' : 'text-muted-foreground'}`} /><div className="min-w-0"><p className="text-sm font-medium">{title || (loading ? 'Loading…' : error ? 'Could not load this section' : 'Nothing here yet')}</p><p className={`mt-1 text-sm leading-6 ${error ? 'text-destructive-text' : 'text-muted-foreground'}`}>{error || description}</p>{onRetry && <Button type="button" variant="outline" size="sm" className="mt-3" onClick={onRetry} disabled={loading}>Try again</Button>}</div></div>
  </div>;
}
WorkspaceState.propTypes = { loading: PropTypes.bool, error: PropTypes.string, title: PropTypes.string, description: PropTypes.string, onRetry: PropTypes.func };
