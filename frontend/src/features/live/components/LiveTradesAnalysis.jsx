import { Card, CardContent, CardHeader } from "@/shared/components/ui/card";
import { Badge } from "@/shared/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/shared/components/ui/table";
import { formatNumber, formatBrokerAccount, formatDateTime } from "@/shared/utils/formatters";
import LiveTablePagination from "@/features/live/components/LiveTablePagination.jsx";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/components/ui/select";

function Metric({ title, value, detail, color = "text-foreground" }) {
  return <Card className="border-border bg-card/50"><CardContent className="p-5"><p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{title}</p><p className={`mt-2 text-2xl font-semibold ${color}`}>{value}</p>{detail && <p className="mt-1 text-xs text-muted-foreground">{detail}</p>}</CardContent></Card>;
}

export default function LiveTradesAnalysis({ trades = [], pagination, summary = {}, onPageChange, allocationFilter = "", onAllocationChange }) {
  const total = Number(summary.count ?? pagination?.count ?? trades.length);
  const winners = Number(summary.winning || 0);
  const losers = Number(summary.losing || 0);
  const realized = Number(summary.realized_pnl || 0);
  const winRate = total ? (winners / total) * 100 : null;
  return (
    <div className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Metric title="Closed trades" value={total} detail="Matching allocation · all pages" />
        <Metric title="Realized P&L" value={`₹${formatNumber(realized)}`} color={realized >= 0 ? "text-emerald-700 dark:text-emerald-400" : "text-rose-700 dark:text-rose-400"} />
        <Metric title="Winning trades" value={winners} detail={`${losers} losing trades`} color="text-emerald-700 dark:text-emerald-400" />
        <Metric title="Win rate" value={winRate == null ? "—" : `${winRate.toFixed(2)}%`} detail="Across all closed trades" />
      </div>
      <Card className="overflow-hidden border-border bg-card/50">
      <CardHeader className="flex flex-col gap-2 space-y-0 border-b border-border px-4 py-2 sm:flex-row sm:items-center sm:justify-between"><p className="text-xl text-foreground font-semibold">Live Trades</p><Select resource="live-allocations" value={allocationFilter || "ALL"} onValueChange={(value) => onAllocationChange(value === "ALL" ? "" : value)}><SelectTrigger className="h-9 w-full border-border bg-background text-foreground sm:w-64" aria-label="Filter trades by allocation"><SelectValue placeholder="All allocations" /></SelectTrigger><SelectContent><SelectItem persistent value="ALL">All allocations</SelectItem></SelectContent></Select></CardHeader>
      {trades.length === 0 ? (
        <CardContent className="py-14 text-center text-muted-foreground">No closed live trades yet.</CardContent>
      ) : (
        <>
          <CardContent className="p-0">
            <div className="overflow-x-auto scrollbar-thin-theme">
              <Table>
                <TableHeader className="bg-secondary/50"><TableRow className="border-border hover:bg-transparent">
                  <TableHead className="text-foreground">Instrument</TableHead><TableHead className="text-foreground">Strategy · broker account</TableHead><TableHead className="text-foreground">Side</TableHead><TableHead className="text-right text-foreground">Qty</TableHead><TableHead className="text-right text-foreground">Entry</TableHead><TableHead className="text-right text-foreground">Exit</TableHead><TableHead className="text-right text-foreground">Realized P&amp;L</TableHead><TableHead className="text-foreground">Entry time</TableHead><TableHead className="text-foreground">Exit time</TableHead>
                </TableRow></TableHeader>
                <TableBody>{trades.map((trade) => {
                  const pnl = Number(trade.realized_pnl || 0);
                  return <TableRow key={trade.id} className="border-border">
                    <TableCell className="font-medium text-foreground">{trade.instrument_symbol || "—"}</TableCell>
                    <TableCell><div className="text-foreground">{trade.strategy_name || "Unassigned strategy"}</div><div className="text-xs text-muted-foreground">{formatBrokerAccount(trade.broker_name, trade.broker_label)}</div></TableCell>
                    <TableCell><Badge variant="outline" className={trade.side === "BUY" ? "border-emerald-500/30 text-emerald-700 dark:text-emerald-300" : "border-rose-500/30 text-rose-700 dark:text-rose-300"}>{trade.side}</Badge></TableCell>
                    <TableCell className="text-right text-foreground">{formatNumber(trade.quantity)}</TableCell>
                    <TableCell className="text-right text-foreground">₹{formatNumber(trade.entry_price)}</TableCell>
                    <TableCell className="text-right text-foreground">₹{formatNumber(trade.exit_price)}</TableCell>
                    <TableCell className={`text-right font-medium ${pnl >= 0 ? "text-emerald-700 dark:text-emerald-400" : "text-rose-700 dark:text-rose-400"}`}>₹{formatNumber(pnl)}</TableCell>
                    <TableCell className="whitespace-nowrap text-muted-foreground">{formatDateTime(trade.entry_time)}</TableCell>
                    <TableCell className="whitespace-nowrap text-muted-foreground">{formatDateTime(trade.exit_time)}</TableCell>
                  </TableRow>;
                })}</TableBody>
              </Table>
            </div>
          </CardContent>
          <LiveTablePagination page={pagination?.page || 1} count={pagination?.count || 0} onPageChange={onPageChange} />
        </>
      )}
      </Card>
    </div>
  );
}
