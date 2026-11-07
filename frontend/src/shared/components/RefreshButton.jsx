import { useRef, useState } from 'react';
import PropTypes from 'prop-types';
import { RefreshCw } from 'lucide-react';
import { Button } from './ui/button';
import { useNotifications } from '@/shared/hooks/useNotifications';
import { getApiErrorMessage } from '@/shared/utils/apiErrors';

/** One refresh action: labelled tooltip, busy feedback and no duplicate clicks. */
export default function RefreshButton({ onClick, loading = false, disabled = false, label = 'Refresh', className }) {
  const [pending, setPending] = useState(false);
  const inFlight = useRef(false);
  const { notify } = useNotifications();
  const busy = loading || pending;
  async function refresh(event) {
    if (inFlight.current || loading || disabled) return;
    inFlight.current = true;
    setPending(true);
    try { await onClick(event); }
    catch (error) { notify.error(getApiErrorMessage(error, 'Could not refresh this view.')); }
    finally { inFlight.current = false; setPending(false); }
  }
  return <Button type="button" variant="ghost" size="icon" className={className} title={label}
    data-refresh="true" disabled={busy || disabled} aria-busy={busy} onClick={refresh}>
    <RefreshCw aria-hidden="true" className={busy ? 'motion-safe:animate-spin' : undefined} />
  </Button>;
}
RefreshButton.propTypes = { onClick: PropTypes.func.isRequired, loading: PropTypes.bool, disabled: PropTypes.bool, label: PropTypes.string, className: PropTypes.string };
