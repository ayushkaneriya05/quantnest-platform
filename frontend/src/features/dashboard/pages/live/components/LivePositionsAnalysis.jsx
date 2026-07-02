import React, { useMemo } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
import { Badge } from "@/shared/components/ui/badge";
import { TrendingUp, TrendingDown, BarChart3, AlertCircle } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/shared/components/ui/table";
import { formatNumber } from "@/shared/utils/formatters";

const StatCard = ({
  icon: Icon,
  title,
  value,
  subtitle,
  variant = "default",
}) => {
  const variantClasses = {
    default: "bg-sky-500/10 text-sky-400",
    positive: "bg-emerald-500/10 text-emerald-400",
    negative: "bg-rose-500/10 text-rose-400",
  };

  return (
    <Card className="bg-slate-900/50 border-slate-800 hover:border-slate-700 transition-colors">
      <CardContent className="p-6">
        <div className="flex items-start justify-between mb-4">
          <div className={`p-3 rounded-2xl ${variantClasses[variant]}`}>
            <Icon className="h-6 w-6" />
          </div>
        </div>
        <div>
          <p className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-1">
            {title}
          </p>
          <p className="text-2xl font-black text-white mb-1">{value}</p>
          {subtitle && <p className="text-xs text-slate-600">{subtitle}</p>}
        </div>
      </CardContent>
    </Card>
  );
};

export default function LivePositionsAnalysis({
  positions = [],
  sessions = [],
}) {
  const sessionsMap = useMemo(() => {
    return sessions.reduce((acc, s) => {
      acc[s.id] = s;
      return acc;
    }, {});
  }, [sessions]);

  const positionStats = useMemo(() => {
    if (!positions.length)
      return { total: 0, profitable: 0, loss: 0, avgSize: 0, totalPnl: 0 };

    const profitable = positions.filter((p) => p.unrealized_pnl >= 0).length;
    const atLoss = positions.filter((p) => p.unrealized_pnl < 0).length;
    const totalPnl = positions.reduce(
      (sum, p) => sum + (p.unrealized_pnl || 0),
      0,
    );
    const avgSize =
      positions.reduce((sum, p) => sum + (p.quantity || 0), 0) /
      positions.length;

    return {
      total: positions.length,
      profitable,
      loss: atLoss,
      avgSize: Math.round(avgSize),
      totalPnl,
    };
  }, [positions]);

  if (positions.length === 0) {
    return (
      <Card className="bg-slate-900/50 border-slate-800">
        <CardContent className="py-16 text-center">
          <TrendingUp className="h-12 w-12 text-slate-600 mx-auto mb-4" />
          <p className="text-slate-400 text-lg">No open positions</p>
          <p className="text-slate-500 text-sm mt-1">
            Positions will appear here when you place trades
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Positions Statistics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <StatCard
          icon={BarChart3}
          title="Total Positions"
          value={positionStats.total}
          subtitle="Open trades"
          variant="default"
        />
        <StatCard
          icon={TrendingUp}
          title="Profitable"
          value={positionStats.profitable}
          subtitle={`${((positionStats.profitable / positionStats.total) * 100).toFixed(1)}%`}
          variant="positive"
        />
        <StatCard
          icon={TrendingDown}
          title="At Loss"
          value={positionStats.loss}
          subtitle={`${((positionStats.loss / positionStats.total) * 100).toFixed(1)}%`}
          variant="negative"
        />
        <StatCard
          icon={BarChart3}
          title="Avg Position"
          value={positionStats.avgSize}
          subtitle="Units"
          variant="default"
        />
        <StatCard
          icon={TrendingUp}
          title="Total Unrealized P&L"
          value={`₹${formatNumber(Math.abs(positionStats.totalPnl))}`}
          subtitle={positionStats.totalPnl >= 0 ? "Gain" : "Loss"}
          variant={positionStats.totalPnl >= 0 ? "positive" : "negative"}
        />
      </div>

      {/* Detailed Positions Table */}
      <Card className="bg-slate-900/50 border-slate-800 overflow-hidden">
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">Open Positions Details</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader className="bg-slate-800/50">
                <TableRow className="border-slate-700 hover:bg-transparent">
                  <TableHead className="text-slate-300 font-bold">
                    Symbol
                  </TableHead>
                  <TableHead className="text-slate-300 font-bold text-right">
                    Quantity
                  </TableHead>
                  <TableHead className="text-slate-300 font-bold text-right">
                    Entry Price
                  </TableHead>
                  <TableHead className="text-slate-300 font-bold text-right">
                    Avg Price
                  </TableHead>
                  <TableHead className="text-slate-300 font-bold text-right">
                    Current Price
                  </TableHead>
                  <TableHead className="text-slate-300 font-bold text-right">
                    Unrealized P&L
                  </TableHead>
                  <TableHead className="text-slate-300 font-bold text-right">
                    Return %
                  </TableHead>
                  <TableHead className="text-slate-300 font-bold">
                    Strategy
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {positions.map((position, idx) => {
                  const pnl = position.unrealized_pnl || 0;
                  const returnPct = position.return_percent || 0;
                  const session = sessionsMap[position.session];

                  return (
                    <TableRow
                      key={`${position.symbol}-${idx}`}
                      className="border-slate-700 hover:bg-slate-800/30 transition-colors"
                    >
                      <TableCell className="font-medium text-white">
                        {position.symbol}
                      </TableCell>
                      <TableCell className="text-right">
                        <span
                          className={
                            position.side === "LONG"
                              ? "text-emerald-400"
                              : "text-rose-400"
                          }
                        >
                          {position.quantity} {position.side}
                        </span>
                      </TableCell>
                      <TableCell className="text-right text-slate-300">
                        ₹{formatNumber(position.entry_price)}
                      </TableCell>
                      <TableCell className="text-right text-slate-300">
                        ₹{formatNumber(position.average_price)}
                      </TableCell>
                      <TableCell className="text-right text-slate-300">
                        ₹{formatNumber(position.current_price)}
                      </TableCell>
                      <TableCell className="text-right">
                        <span
                          className={
                            pnl >= 0
                              ? "text-emerald-400 font-semibold"
                              : "text-rose-400 font-semibold"
                          }
                        >
                          ₹{formatNumber(pnl)}
                        </span>
                      </TableCell>
                      <TableCell className="text-right">
                        <span
                          className={
                            returnPct >= 0
                              ? "text-emerald-400 font-semibold"
                              : "text-rose-400 font-semibold"
                          }
                        >
                          {returnPct >= 0 ? "+" : ""}
                          {returnPct.toFixed(2)}%
                        </span>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className="bg-slate-800/50 text-slate-300 border-slate-700 text-xs"
                        >
                          {session?.strategy_name || "Unknown"}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Risk Analysis */}
      <Card className="bg-slate-900/50 border-slate-800">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-amber-400" />
            <span>Risk Analysis</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Largest Winner */}
            {positions.length > 0 && (
              <div className="p-4 bg-slate-800/30 rounded-lg border border-slate-700">
                <p className="text-slate-500 text-xs uppercase tracking-wider font-bold mb-2">
                  Largest Winner
                </p>
                {(() => {
                  const largest = positions.reduce((max, p) =>
                    (p.unrealized_pnl || 0) > (max.unrealized_pnl || 0)
                      ? p
                      : max,
                  );
                  return (
                    <>
                      <p className="text-white font-bold text-lg">
                        {largest.symbol}
                      </p>
                      <p className="text-emerald-400 font-semibold text-lg">
                        +₹{formatNumber(largest.unrealized_pnl)}
                      </p>
                    </>
                  );
                })()}
              </div>
            )}

            {/* Largest Loser */}
            {positions.length > 0 && (
              <div className="p-4 bg-slate-800/30 rounded-lg border border-slate-700">
                <p className="text-slate-500 text-xs uppercase tracking-wider font-bold mb-2">
                  Largest Loser
                </p>
                {(() => {
                  const largest = positions.reduce((min, p) =>
                    (p.unrealized_pnl || 0) < (min.unrealized_pnl || 0)
                      ? p
                      : min,
                  );
                  return (
                    <>
                      <p className="text-white font-bold text-lg">
                        {largest.symbol}
                      </p>
                      <p className="text-rose-400 font-semibold text-lg">
                        -₹{formatNumber(Math.abs(largest.unrealized_pnl))}
                      </p>
                    </>
                  );
                })()}
              </div>
            )}

            {/* Most Volatile */}
            <div className="p-4 bg-slate-800/30 rounded-lg border border-slate-700">
              <p className="text-slate-500 text-xs uppercase tracking-wider font-bold mb-2">
                Concentration
              </p>
              <p className="text-white font-bold text-lg">
                {(
                  (positionStats.profitable / positionStats.total) *
                  100
                ).toFixed(1)}
                % Profitable
              </p>
              <p className="text-slate-400 text-sm">Positions in green</p>
            </div>

            {/* Avg Unrealized */}
            <div className="p-4 bg-slate-800/30 rounded-lg border border-slate-700">
              <p className="text-slate-500 text-xs uppercase tracking-wider font-bold mb-2">
                Avg Unrealized P&L
              </p>
              <p
                className={`font-bold text-lg ${positionStats.totalPnl / positionStats.total >= 0 ? "text-emerald-400" : "text-rose-400"}`}
              >
                ₹{formatNumber(positionStats.totalPnl / positionStats.total)}
              </p>
              <p className="text-slate-400 text-sm">Per position</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
