import { useEffect } from "react";
import PropTypes from "prop-types";
import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import MainHeader from "@/shared/components/layout/main-header";
import { Card } from "@/shared/components/ui/card";
import { useTheme } from "@/shared/context/theme";
import { cn } from "@/shared/lib/utils";

export default function AuthLayout({ title, description, icon: Icon, authPage, aside, children }) {
  const { resolvedTheme } = useTheme();

  useEffect(() => {
    document.title = `${title} · QuantNest`;
  }, [title]);

  return (
    <div data-landing-theme={resolvedTheme} className="relative isolate flex min-h-[var(--viewport-height)] flex-col overflow-x-clip bg-background text-foreground selection:bg-brand/25">
      <div aria-hidden="true" className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
        <div className="landing-market-animation absolute inset-0 opacity-60" />
        <div className="landing-grid absolute inset-0 opacity-30" />
      </div>
      <a href="#auth-main" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-card focus:p-3">
        Skip to content
      </a>
      <MainHeader authPage={authPage} />

      <main id="auth-main" className={cn("relative flex flex-1 items-center justify-center px-4 py-6", !aside && "sm:py-8")}>
        <Card className={cn(
          "w-full min-w-0 overflow-hidden rounded-3xl border-border bg-card shadow-card",
          aside ? "grid max-w-4xl lg:grid-cols-[0.85fr_1.15fr]" : "max-w-md",
        )}>
          {aside && (
            <aside className="order-last min-w-0 border-t bg-brand/5 p-5 sm:p-7 lg:order-first lg:border-r lg:border-t-0">
              {aside}
            </aside>
          )}
          <div className={cn("min-w-0 p-5", aside ? "sm:p-6" : "sm:p-7")}>
            <header className={cn("text-center", aside ? "mb-5" : "mb-6")}>
              {Icon && <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl border border-brand/20 bg-brand/10"><Icon aria-hidden="true" className="h-6 w-6 text-brand" /></div>}
              <h1 className="text-2xl font-semibold leading-tight tracking-[-0.035em] sm:text-[1.75rem]">{title}</h1>
              <p className="mx-auto mt-2 max-w-sm text-sm leading-6 text-muted-foreground">{description}</p>
            </header>
            {children}
          </div>
        </Card>
      </main>

      <footer className="relative px-4 pb-4">
        <nav aria-label="Help and policies" className="mx-auto flex max-w-4xl flex-wrap items-center justify-center gap-x-4 text-xs text-muted-foreground">
          <Link to="/" className="focus-ring inline-flex min-h-9 items-center gap-1.5 rounded-sm hover:text-brand"><ArrowLeft aria-hidden="true" className="h-3.5 w-3.5" />Home</Link>
          <Link to="/docs/" className="focus-ring inline-flex min-h-9 items-center rounded-sm hover:text-brand">User guide</Link>
          <Link to="/contact/" className="focus-ring inline-flex min-h-9 items-center rounded-sm hover:text-brand">Support</Link>
          <Link to="/privacy-policy" className="focus-ring inline-flex min-h-9 items-center rounded-sm hover:text-brand">Privacy</Link>
          <Link to="/terms-of-service" className="focus-ring inline-flex min-h-9 items-center rounded-sm hover:text-brand">Terms</Link>
        </nav>
      </footer>
    </div>
  );
}

AuthLayout.propTypes = {
  title: PropTypes.string.isRequired,
  description: PropTypes.string.isRequired,
  icon: PropTypes.elementType,
  authPage: PropTypes.string,
  aside: PropTypes.node,
  children: PropTypes.node.isRequired,
};
