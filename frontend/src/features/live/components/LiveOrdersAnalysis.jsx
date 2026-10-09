import { useMemo } from "react";
import { Activity } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/shared/components/ui/card";
import { Badge } from "@/shared/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/shared/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/components/ui/select";
import { formatNumber, formatBrokerAccount, formatDateTime } from "@/shared/utils/formatters";
import LiveTablePagination from "@/features/live/components/LiveTablePagination.jsx";

const ACTIVE = new Set(["PENDING", "PLACED", "PARTIAL_FILL", "UNKNOWN"]);
const tone = (status) => {
  if (status === "FILLED") return "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300";
  if (status === "REJECTED" || status === "CANCELLED" || status === "EXPIRED") return "border-rose-500/30 bg-rose-500/10 text-rose-700 dark:text-rose-300";
  if (ACTIVE.has(status)) return "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300";
  return "border-border bg-secondary/50 text-foreground";
};

function Metric({ title, value, note, color = "text-foreground" }) {
  return <Card className="border-border bg-card/50"><CardContent className="p-5"><p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{title}</p><p className={`mt-2 text-2xl font-semibold ${color}`}>{value}</p>{note && <p className="mt-1 text-xs text-muted-foreground">{note}</p>}</CardContent></Card>;
}

export default function LiveOrdersAnalysis({ orders = [], pagination, summary = {}, onPageChange, statusFilter = "", onStatusChange, allocationFilter = "", onAllocationChange }) {
  const stats = useMemo(() => ({
    filled: Number(summary.filled || 0) + Number(summary.partial || 0),
    active: Number(summary.active || 0),
    rejected: Number(summary.rejected || 0),
    total: Number(summary.total ?? pagination?.count ?? orders.length),
  }), [orders.length, pagination?.count, summary.active, summary.filled, summary.partial, summary.rejected, summary.total]);

  return (
    <div className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Metric title="Orders" value={stats.total} note="Matching filters · all pages" />
        <Metric title="Filled / partial" value={stats.filled} color="text-emerald-700 dark:text-emerald-400" />
        <Metric title="Active" value={stats.active} color="text-amber-700 dark:text-amber-300" />
        <Metric title="Rejected" value={stats.rejected} color="text-rose-700 dark:text-rose-400" />
      </div>
      <Card className="overflow-hidden border-border bg-card/50">
        <CardHeader className="flex flex-col gap-2 space-y-0 border-b border-border px-4 py-2 sm:flex-row sm:items-center sm:justify-between"><p className="text-xl text-foreground font-semibold">Live orders</p><div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row"><Select resource="live-allocations" value={allocationFilter || "ALL"} onValueChange={(value) => onAllocationChange(value === "ALL" ? "" : value)}><SelectTrigger className="h-9 w-full border-border bg-background text-foreground sm:w-64" aria-label="Filter orders by allocation"><SelectValue placeholder="All allocations" /></SelectTrigger><SelectContent><SelectItem persistent value="ALL">All allocations</SelectItem></SelectContent></Select><Select value={statusFilter || "ALL"} onValueChange={(value) => onStatusChange(value === "ALL" ? "" : value)}><SelectTrigger className="h-9 w-full border-border bg-background text-foreground sm:w-48" aria-label="Filter orders by status"><SelectValue placeholder="All statuses" /></SelectTrigger><SelectContent><SelectItem value="ALL">All statuses</SelectItem><SelectItem value="PENDING">Pending</SelectItem><SelectItem value="PLACED">Placed</SelectItem><SelectItem value="PARTIAL_FILL">Partial fill</SelectItem><SelectItem value="FILLED">Filled</SelectItem><SelectItem value="REJECTED">Rejected</SelectItem><SelectItem value="CANCELLED">Cancelled</SelectItem><SelectItem value="EXPIRED">Expired</SelectItem><SelectItem value="UNKNOWN">Unknown</SelectItem></SelectContent></Select></div></CardHeader>
        {orders.length === 0 ? (
          <CardContent className="py-14 text-center"><Activity className="mx-auto mb-3 h-8 w-8 text-muted-foreground" /><p className="text-foreground">No live orders</p><p className="mt-1 text-sm text-muted-foreground">Orders will appear when a live signal is dispatched.</p></CardContent>
        ) : (
          <>
            <CardContent className="p-0"><div className="overflow-x-auto scrollbar-thin-theme"><Table>
              <TableHeader className="bg-secondary/50"><TableRow className="border-border hover:bg-transparent"><TableHead className="text-foreground">Order</TableHead><TableHead className="text-foreground">Instrument</TableHead><TableHead className="text-foreground">Strategy</TableHead><TableHead className="text-foreground">Side / Type</TableHead><TableHead className="text-right text-foreground">Quantity</TableHead><TableHead className="text-right text-foreground">Filled</TableHead><TableHead className="text-right text-foreground">Average fill</TableHead><TableHead className="text-foreground">Status</TableHead><TableHead className="text-foreground">Placed</TableHead></TableRow></TableHeader>
              <TableBody>{orders.map((order) => <TableRow key={order.id} className="border-border">
                <TableCell className="font-mono text-xs text-muted-foreground">#{order.id}</TableCell>
                <TableCell><div className="font-medium text-foreground">{order.instrument_symbol || "—"}</div><div className="text-xs text-muted-foreground">{order.broker_order_id || "Broker ID pending"}</div></TableCell>
                <TableCell><div className="text-foreground">{order.strategy_name || "—"}</div><div className="text-xs text-muted-foreground">{formatBrokerAccount(order.broker_name, order.broker_label)}</div></TableCell>
                <TableCell><Badge variant="outline" className={order.side === "BUY" ? "border-emerald-500/30 text-emerald-700 dark:text-emerald-300" : "border-rose-500/30 text-rose-700 dark:text-rose-300"}>{order.side || "—"}</Badge><div className="mt-1 text-xs text-muted-foreground">{order.order_type} · {order.product_type}</div></TableCell>
                <TableCell className="text-right text-foreground">{formatNumber(order.quantity)}</TableCell>
                <TableCell className="text-right text-foreground">{formatNumber(order.filled_quantity)} / {formatNumber(order.quantity)}</TableCell>
                <TableCell className="text-right text-foreground">{order.avg_fill_price == null ? "—" : `₹${formatNumber(Number(order.avg_fill_price))}`}</TableCell>
                <TableCell><Badge variant="outline" className={tone(order.status)}>{order.status || "UNKNOWN"}</Badge>{order.rejection_reason && <div className="mt-1 max-w-48 text-xs text-rose-700 dark:text-rose-300">{order.rejection_reason}</div>}</TableCell>
                <TableCell className="whitespace-nowrap text-muted-foreground">{formatDateTime(order.placed_at)}</TableCell>
              </TableRow>)}</TableBody>
            </Table></div></CardContent>
            <LiveTablePagination page={pagination?.page || 1} count={pagination?.count || 0} onPageChange={onPageChange} />
          </>
        )}
      </Card>
    </div>
  );
}
