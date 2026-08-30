import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/shared/components/ui/table";
import { Badge } from "@/shared/components/ui/badge";
import { ArrowUpRight, ArrowDownRight } from "lucide-react";

import { formatNumber } from "@/shared/utils/formatters";

export default function LivePositionsTable({ positions }) {
  if (!positions || positions.length === 0) {
    return (
      <div className="py-12 text-center text-gray-500 border border-dashed border-gray-800 rounded-2xl">
        No open positions.
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-gray-800 bg-gray-900/40 overflow-hidden">
      <Table>
        <TableHeader className="bg-gray-950/40">
          <TableRow className="border-gray-800 hover:bg-transparent">
            <TableHead className="text-gray-500 font-medium">
              Instrument
            </TableHead>
            <TableHead className="text-gray-500 font-medium">Broker</TableHead>
            <TableHead className="text-gray-500 font-medium">Side</TableHead>
            <TableHead className="text-gray-500 font-medium">Qty</TableHead>
            <TableHead className="text-gray-500 font-medium text-right">
              Avg Price
            </TableHead>
            <TableHead className="text-gray-500 font-medium text-right">
              LTP
            </TableHead>
            <TableHead className="text-gray-500 font-medium text-right">
              P&L
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {positions.map((pos) => {
            const isProfit = Number(pos.unrealized_pnl || 0) >= 0;
            return (
              <TableRow
                key={pos.id}
                className="border-gray-800 hover:bg-white/5 transition-colors"
              >
                <TableCell className="font-semibold text-white">
                  {pos.instrument_name || pos.instrument_symbol}
                </TableCell>
                <TableCell className="text-gray-400 text-sm">
                  {pos.broker_label || pos.broker_name || "-"}
                </TableCell>
                <TableCell>
                  <Badge
                    className={
                      pos.side === "BUY"
                        ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/20"
                        : "bg-rose-500/10 text-rose-300 border-rose-500/20"
                    }
                  >
                    {pos.side}
                  </Badge>
                </TableCell>
                <TableCell className="text-gray-300">{pos.quantity}</TableCell>
                <TableCell className="text-right text-gray-300 font-mono">
                  {formatNumber(pos.avg_price)}
                </TableCell>
                <TableCell className="text-right text-gray-300 font-mono">
                  {formatNumber(pos.current_price)}
                </TableCell>
                <TableCell
                  className={`text-right font-mono font-bold ${isProfit ? "text-emerald-300" : "text-rose-300"}`}
                >
                  <div className="flex items-center justify-end gap-1">
                    {isProfit ? (
                      <ArrowUpRight className="h-3 w-3" />
                    ) : (
                      <ArrowDownRight className="h-3 w-3" />
                    )}
                    Rs {formatNumber(pos.unrealized_pnl)}
                  </div>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
