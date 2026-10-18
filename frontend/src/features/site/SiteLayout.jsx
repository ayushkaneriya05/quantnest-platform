import { useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import MainHeader from '@/shared/components/layout/main-header';
import SiteFooter from './SiteFooter';
import SiteEffects from './SiteEffects';
import './site.css';

export default function SiteLayout() {
  const { pathname, hash } = useLocation();
  useEffect(() => {
    if (hash) document.getElementById(hash.slice(1))?.scrollIntoView();
    else window.scrollTo({ top: 0 });
  }, [pathname, hash]);
  return <div className="site-root flex min-h-dvh flex-col overflow-x-clip bg-background text-foreground selection:bg-brand/25"><a href="#site-main" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-card focus:p-3">Skip to content</a><MainHeader /><main id="site-main" className="site-main"><Outlet /></main><SiteFooter /><SiteEffects /></div>;
}
