import PropTypes from "prop-types";
import { AlertCircle } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/shared/components/ui/card";
import { Badge } from "@/shared/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/shared/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/components/ui/select";
import { formatNumber, formatBrokerAccount, formatDateTime, formatCurrency } from "@/shared/utils/formatters";
import { useLivePositionsPnL } from "@/shared/hooks/useLivePositionsPnL";
import Pagination from "@/shared/components/Pagination";

function Metric({ title, value, note, color = "text-foreground" }) {
  return <Card className="border-border bg-card/50"><CardContent className="p-3"><p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{title}</p><p className={`mt-2 text-2xl font-semibold ${color}`}>{value}</p>{note && <p className="mt-1 text-xs text-muted-foreground">{note}</p>}</CardContent></Card>;
}

export default function LivePositionsAnalysis({ positions = [], pagination, summary = {}, onPageChange, onPageSizeChange, loading, allocationFilter = "", onAllocationChange }) {
  const { livePnLByPositionId } = useLivePositionsPnL(positions);
  const stats = { count: summary.count || 0, pnl: Number(summary.unrealized_pnl || 0), profitable: summary.profitable || 0, atLoss: summary.losing || 0 };

  return (
    <div className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Metric title="Open positions" value={stats.count} note="Matching allocation · all pages" />
        <Metric title="Unrealized P&L" value={`${formatCurrency(stats.pnl)}`} color={stats.pnl >= 0 ? "text-success" : "text-loss"} />
        <Metric title="In profit" value={stats.profitable} color="text-success" />
        <Metric title="At loss" value={stats.atLoss} color="text-loss" />
      </div>
      <Card className="overflow-hidden border-border bg-card/50">
        <CardHeader className="flex flex-col gap-2 space-y-0 border-b border-border px-4 py-2 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xl text-foreground font-semibold">Live positions</p>
          <Select resource="live-allocations" value={allocationFilter || "ALL"} onValueChange={(value) => onAllocationChange(value === "ALL" ? "" : value)}><SelectTrigger className="w-full border-border bg-background text-foreground sm:w-64" aria-label="Filter positions by allocation"><SelectValue placeholder="All allocations" /></SelectTrigger><SelectContent>
            <SelectItem persistent value="ALL">All allocations</SelectItem>
          </SelectContent></Select>
        </CardHeader>
        {positions.length === 0 ? (
          <CardContent className="py-14 text-center">
            <AlertCircle className="mx-auto mb-3 h-8 w-8 text-muted-foreground" />
            <p className="text-foreground">No open positions</p>
            <p className="mt-1 text-sm text-muted-foreground">Positions appear here after a live fill is reconciled.</p>
          </CardContent>
        ) : (
          <>
            <CardContent className="p-0">
              <div className="overflow-x-auto scrollbar-thin-theme">
                <Table>
                  <TableHeader className="bg-secondary/50"><TableRow className="border-border hover:bg-transparent">
                    <TableHead className="text-foreground">Instrument</TableHead><TableHead className="text-foreground">Strategy / Account</TableHead><TableHead className="text-foreground">Side</TableHead><TableHead className="text-right text-foreground">Qty</TableHead><TableHead className="text-right text-foreground">Avg price</TableHead><TableHead className="text-right text-foreground">Last price</TableHead><TableHead className="text-right text-foreground">Unrealized P&amp;L</TableHead><TableHead className="text-right text-foreground">Return</TableHead><TableHead className="text-foreground">Opened</TableHead>
                  </TableRow></TableHeader>
                  <TableBody>{positions.map((position) => {
                    const livePosition = livePnLByPositionId[position.id];
                    const pnl = livePosition?.pnl ?? Number(position.unrealized_pnl || 0);
                    const livePrice = livePosition?.livePrice ?? Number(position.current_price || 0);
                    const isBuy = position.side === "BUY";
                    return <TableRow key={position.id} className="border-border">
                      <TableCell className="font-medium text-foreground">{position.instrument_symbol || "—"}</TableCell>
                      <TableCell><div className="text-foreground">{position.strategy_name || "Unassigned strategy"}</div><div className="text-xs text-muted-foreground">{formatBrokerAccount(position.broker_name, position.broker_label)}</div></TableCell>
                      <TableCell><Badge variant="outline" className={isBuy ? "border-success/30 bg-success/10 text-success" : "border-loss/30 bg-loss/10 text-loss"}>{position.side || "—"}</Badge></TableCell>
                      <TableCell className="text-right text-foreground">{formatNumber(position.quantity, { maximumFractionDigits: 0 })}</TableCell>
                      <TableCell className="text-right text-foreground">{formatCurrency(Number(position.avg_price))}</TableCell>
                      <TableCell className="text-right text-foreground">{livePrice > 0 ? `${formatCurrency(livePrice)}` : "—"}</TableCell>
                      <TableCell className={`text-right font-medium ${pnl >= 0 ? "text-success" : "text-loss"}`}>{formatCurrency(pnl)}</TableCell>
                      <TableCell className={`text-right ${(livePosition?.pnlPercent ?? Number(position.return_percent || 0)) >= 0 ? "text-success" : "text-loss"}`}>{formatNumber(livePosition?.pnlPercent ?? Number(position.return_percent || 0))}%</TableCell>
                      <TableCell className="whitespace-nowrap text-muted-foreground">{formatDateTime(position.opened_at)}</TableCell>
                    </TableRow>;
                  })}</TableBody>
                </Table>
              </div>
            </CardContent>
          </>
        )}

            <Pagination {...pagination} loading={loading} onPageChange={onPageChange} onPageSizeChange={onPageSizeChange} label="LivePositionsAnalysis pages" />
      </Card>
    </div>
  );
}

Metric.propTypes = {
  ...Metric.propTypes,
  color: PropTypes.string,
  note: PropTypes.string,
  title: PropTypes.string,
  value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
};

LivePositionsAnalysis.propTypes = {
  ...LivePositionsAnalysis.propTypes,
  onPageSizeChange: PropTypes.func, loading: PropTypes.bool,
  allocationFilter: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  onAllocationChange: PropTypes.func,
  onPageChange: PropTypes.func,
  pagination: PropTypes.object,
  positions: PropTypes.array,
  summary: PropTypes.object,
};
