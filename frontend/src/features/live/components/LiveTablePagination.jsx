import { Button } from "@/shared/components/ui/button";

export default function LiveTablePagination({ page, count, pageSize = 25, onPageChange }) {
  const pages = Math.max(1, Math.ceil(Number(count || 0) / pageSize));
  if (pages <= 1) return null;

  return (
    <div className="flex items-center justify-between border-t border-border px-4 py-3 text-sm">
      <span className="text-muted-foreground">
        Page {page} of {pages} <span className="text-muted-foreground">({count} records)</span>
      </span>
      <div className="flex gap-2">
        <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
          Previous
        </Button>
        <Button variant="outline" size="sm" disabled={page >= pages} onClick={() => onPageChange(page + 1)}>
          Next
        </Button>
      </div>
    </div>
  );
}
