import { Loader2 } from 'lucide-react';

export function GlobalLoader({ text = "Loading...", fullHeight = true }) {
  return (
    <div className={`flex justify-center items-center flex-col gap-3 ${fullHeight ? 'h-96' : 'py-12'}`}>
      <Loader2 className="h-8 w-8 text-indigo-700 dark:text-indigo-400 animate-spin" />
      <p className="text-muted-foreground text-sm">{text}</p>
    </div>
  );
}
