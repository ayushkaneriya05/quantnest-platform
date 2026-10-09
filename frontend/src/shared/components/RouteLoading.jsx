import { Loader2 } from "lucide-react";

export default function RouteLoading() {
  return <div role="status" className="flex min-h-48 flex-1 items-center justify-center gap-3 bg-background p-6 text-muted-foreground"><Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" />Loading page…</div>;
}
