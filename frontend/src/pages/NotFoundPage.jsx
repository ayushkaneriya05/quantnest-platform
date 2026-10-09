import { Link } from "react-router-dom";
import { Button } from "@/shared/components/ui/button";
import ThemeSwitch from "@/shared/components/ThemeSwitch";

export default function NotFoundPage() {
  return <main className="flex min-h-dvh items-center justify-center bg-background p-6 text-foreground">
    <section className="w-full max-w-md rounded-2xl border bg-card p-6 sm:p-8">
      <div className="flex items-center justify-between"><p className="text-sm text-muted-foreground">QuantNest · 404</p><ThemeSwitch /></div>
      <h1 className="mt-4 text-2xl font-semibold">Page not found</h1>
      <p className="mt-3 text-muted-foreground">This address does not match a page. Open your workspace or return to the home page.</p>
      <div className="mt-6 flex flex-wrap gap-3"><Button asChild><Link to="/overview">Open workspace</Link></Button><Button asChild variant="outline"><Link to="/">Home</Link></Button></div>
    </section>
  </main>;
}
