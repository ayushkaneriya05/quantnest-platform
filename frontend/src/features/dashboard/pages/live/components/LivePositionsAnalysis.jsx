import { useMemo } from "react";
import { AlertCircle } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/shared/components/ui/card";
import { Badge } from "@/shared/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/shared/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/components/ui/select";
import { formatNumber, formatBrokerAccount, formatDateTime } from "@/shared/utils/formatters";
import { useLivePositionsPnL } from "@/shared/hooks/useLivePositionsPnL";
import LiveTablePagination from "./LiveTablePagination";

function Metric({ title, value, note, color = "text-white" }) {
  return <Card className="border-slate-800 bg-slate-900/50"><CardContent className="p-5"><p className="text-xs font-semibold uppercase tracking-wider text-slate-500">{title}</p><p className={`mt-2 text-2xl font-semibold ${color}`}>{value}</p>{note && <p className="mt-1 text-xs text-slate-500">{note}</p>}</CardContent></Card>;
}

export default function LivePositionsAnalysis({ positions = [], positionsForPnL, pagination, summary = {}, onPageChange, sessions = [], allocationFilter = "", onAllocationChange }) {
  const pnlPositions = useMemo(() => {
    if (!Array.isArray(positionsForPnL)) return positions;
    return allocationFilter
      ? positionsForPnL.filter((position) => String(position.allocation_id) === String(allocationFilter))
      : positionsForPnL;
  }, [allocationFilter, positions, positionsForPnL]);
  const { livePnLByPositionId } = useLivePositionsPnL(pnlPositions);
  const stats = useMemo(() => {
    const pnlValues = pnlPositions.map((position) =>
      livePnLByPositionId[position.id]?.pnl ?? Number(position.unrealized_pnl || 0),
    );
    return {
      pnl: pnlValues.reduce((total, pnl) => total + pnl, 0),
      profitable: pnlValues.filter((pnl) => pnl > 0).length,
      atLoss: pnlValues.filter((pnl) => pnl < 0).length,
      count: Number(summary.count ?? pagination?.count ?? pnlPositions.length),
    };
  }, [livePnLByPositionId, pagination?.count, pnlPositions, summary.count]);

  return (
    <div className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Metric title="Open positions" value={stats.count} note="Matching allocation · all pages" />
        <Metric title="Unrealized P&L" value={`₹${formatNumber(stats.pnl)}`} color={stats.pnl >= 0 ? "text-emerald-400" : "text-rose-400"} />
        <Metric title="In profit" value={stats.profitable} color="text-emerald-400" />
        <Metric title="At loss" value={stats.atLoss} color="text-rose-400" />
      </div>
      <Card className="overflow-hidden border-slate-800 bg-slate-900/50">
        <CardHeader className="flex flex-col gap-2 space-y-0 border-b border-slate-800 px-4 py-2 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xl text-slate-300 font-semibold">Live positions</p>
          <Select value={allocationFilter || "ALL"} onValueChange={(value) => onAllocationChange(value === "ALL" ? "" : value)}><SelectTrigger className="h-9 w-full border-slate-700 bg-slate-950 text-slate-200 sm:w-64" aria-label="Filter positions by allocation"><SelectValue placeholder="All allocations" /></SelectTrigger><SelectContent>
            <SelectItem value="ALL">All allocations</SelectItem>
            {sessions.filter((session) => session.allocation?.id).map((session) => <SelectItem key={session.allocation.id} value={String(session.allocation.id)}>{session.strategy_name} · {formatBrokerAccount(session.broker_name, session.broker_label)}</SelectItem>)}
          </SelectContent></Select>
        </CardHeader>
        {positions.length === 0 ? (
          <CardContent className="py-14 text-center">
            <AlertCircle className="mx-auto mb-3 h-8 w-8 text-slate-600" />
            <p className="text-slate-300">No open positions</p>
            <p className="mt-1 text-sm text-slate-500">Positions appear here after a live fill is reconciled.</p>
          </CardContent>
        ) : (
          <>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader className="bg-slate-800/50"><TableRow className="border-slate-700 hover:bg-transparent">
                    <TableHead className="text-slate-300">Instrument</TableHead><TableHead className="text-slate-300">Strategy / Account</TableHead><TableHead className="text-slate-300">Side</TableHead><TableHead className="text-right text-slate-300">Qty</TableHead><TableHead className="text-right text-slate-300">Avg price</TableHead><TableHead className="text-right text-slate-300">Last price</TableHead><TableHead className="text-right text-slate-300">Unrealized P&amp;L</TableHead><TableHead className="text-right text-slate-300">Return</TableHead><TableHead className="text-slate-300">Opened</TableHead>
                  </TableRow></TableHeader>
                  <TableBody>{positions.map((position) => {
                    const livePosition = livePnLByPositionId[position.id];
                    const pnl = livePosition?.pnl ?? Number(position.unrealized_pnl || 0);
                    const livePrice = livePosition?.livePrice ?? Number(position.current_price || 0);
                    const isBuy = position.side === "BUY";
                    return <TableRow key={position.id} className="border-slate-800">
                      <TableCell className="font-medium text-white">{position.instrument_symbol || "—"}</TableCell>
                      <TableCell><div className="text-slate-200">{position.strategy_name || "Unassigned strategy"}</div><div className="text-xs text-slate-500">{formatBrokerAccount(position.broker_name, position.broker_label)}</div></TableCell>
                      <TableCell><Badge variant="outline" className={isBuy ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300" : "border-rose-500/30 bg-rose-500/10 text-rose-300"}>{position.side || "—"}</Badge></TableCell>
                      <TableCell className="text-right text-slate-200">{formatNumber(position.quantity)}</TableCell>
                      <TableCell className="text-right text-slate-300">₹{formatNumber(Number(position.avg_price))}</TableCell>
                      <TableCell className="text-right text-slate-300">{livePrice > 0 ? `₹${formatNumber(livePrice)}` : "—"}</TableCell>
                      <TableCell className={`text-right font-medium ${pnl >= 0 ? "text-emerald-400" : "text-rose-400"}`}>₹{formatNumber(pnl)}</TableCell>
                      <TableCell className={`text-right ${(livePosition?.pnlPercent ?? Number(position.return_percent || 0)) >= 0 ? "text-emerald-400" : "text-rose-400"}`}>{(livePosition?.pnlPercent ?? Number(position.return_percent || 0)).toFixed(2)}%</TableCell>
                      <TableCell className="whitespace-nowrap text-slate-400">{formatDateTime(position.opened_at)}</TableCell>
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
