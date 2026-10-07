import React from "react";
import PropTypes from "prop-types";
import { useLocation } from "react-router-dom";
import { AlertTriangle, RefreshCw, Home, RotateCcw } from "lucide-react";
import { Button } from "@/shared/components/ui/button";

class PageErrorBoundary extends React.Component {
  state = { hasError: false, error: null, componentStack: "" };
  static getDerivedStateFromError(error) { return { hasError: true, error }; }
  componentDidCatch(error, info) {
    console.error("Page rendering failed:", error, info);
    this.setState({ componentStack: info.componentStack });
  }
  componentDidUpdate(previous) {
    if (this.state.hasError && previous.resetKey !== this.props.resetKey) this.reset();
  }
  reset = () => this.setState({ hasError: false, error: null, componentStack: "" });
  render() {
    if (!this.state.hasError) return this.props.children;
    return <main className="scrollbar-theme flex min-h-[100dvh] items-center justify-center overflow-y-auto bg-background px-4 py-10 text-foreground">
      <section aria-labelledby="page-error-title" role="alert" className="w-full max-w-xl rounded-2xl border border-border bg-card p-6 shadow-xl sm:p-8">
        <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-xl border border-amber-500/20 bg-amber-500/10 text-amber-300"><AlertTriangle aria-hidden="true" /></div>
        <p className="mb-2 text-xs font-medium uppercase tracking-widest text-muted-foreground">QuantNest</p>
        <h1 id="page-error-title" className="text-2xl font-semibold">This page could not load</h1>
        <p className="mt-3 text-sm leading-relaxed text-muted-foreground">Try opening it again. If the error continues, reload the page or return to the home page.</p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Button onClick={this.reset}><RotateCcw />Try again</Button>
          <Button variant="outline" onClick={() => window.location.reload()}><RefreshCw />Reload page</Button>
          <Button variant="outline" onClick={() => window.location.assign("/")}><Home />Home</Button>
        </div>
        {import.meta.env.DEV && <details className="mt-6 rounded-lg border border-border p-3">
          <summary className="cursor-pointer text-sm text-muted-foreground">Development error details</summary>
          <pre className="scrollbar-theme mt-3 max-h-64 overflow-auto whitespace-pre-wrap break-words text-xs text-muted-foreground">{this.state.error?.stack || String(this.state.error)}{"\n"}{this.state.componentStack}</pre>
        </details>}
      </section>
    </main>;
  }
}
PageErrorBoundary.propTypes = { children: PropTypes.node, resetKey: PropTypes.string };

export default function ErrorBoundary({ children }) {
  const location = useLocation();
  return <PageErrorBoundary resetKey={location.key}>{children}</PageErrorBoundary>;
}
ErrorBoundary.propTypes = { children: PropTypes.node };
