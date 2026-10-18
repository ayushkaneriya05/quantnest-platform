import { useEffect, useRef } from 'react';
import PropTypes from 'prop-types';
import { brand } from './config';
let loading;
function loadTurnstileSdk() {
  if (window.turnstile) return Promise.resolve(window.turnstile);
  if (!loading) loading = new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';
    script.async = true;
    script.onload = () => resolve(window.turnstile);
    script.onerror = () => { script.remove(); loading = null; reject(new Error('Verification could not load. Retry or contact support.')); };
    document.head.append(script);
  });
  return loading;
}
export default function Turnstile({ action, onToken, onError, reset }) {
  const element = useRef(null);
  useEffect(() => {
    if (!brand.turnstile) return;
    let cancelled = false; let widget; let provider;
    loadTurnstileSdk().then(api => {
      provider = api;
      if (cancelled) return;
      widget = api.render(element.current, { sitekey: brand.turnstile, action, callback: onToken, 'expired-callback': () => onToken(''), 'error-callback': () => onError('Verification failed. Please retry.'), theme: 'auto' });
    }).catch(error => { if (!cancelled) onError(error.message); });
    return () => { cancelled = true; if (widget !== undefined) provider.remove(widget); };
  }, [action, onToken, onError, reset]);
  return brand.turnstile ? <div ref={element} className="my-4 max-w-full overflow-x-auto" /> : null;
}
Turnstile.propTypes = { action: PropTypes.string.isRequired, onToken: PropTypes.func.isRequired, onError: PropTypes.func.isRequired, reset: PropTypes.number };
