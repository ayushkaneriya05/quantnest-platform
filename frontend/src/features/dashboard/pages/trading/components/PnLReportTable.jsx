import React from "react";
import { cn } from "@/shared/lib/utils";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/shared/components/ui/table";
import { Card } from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import { ChevronLeft, ChevronRight, TrendingUp, TrendingDown } from "lucide-react";
import { GlobalLoader } from "@/shared/components/ui/global-loader";

export default function PnLReportTable({
  logs,
  loading,
  page,
  totalCount,
  onPageChange,
}) {
  const totalPages = Math.ceil(totalCount / 50);

  return (
    <div className="space-y-4">
      <Card className="bg-slate-950/40 border-slate-800/50 backdrop-blur-xl overflow-hidden rounded-3xl">
        <div className="overflow-x-auto custom-scrollbar min-h-[400px]">
          <Table>
            <TableHeader>
              <TableRow className="border-slate-800/50 hover:bg-transparent bg-slate-900/40">
                <TableHead className="text-[10px] font-bold uppercase tracking-widest text-slate-500 py-4">Exit Time</TableHead>
                <TableHead className="text-[10px] font-bold uppercase tracking-widest text-slate-500 py-4">Symbol</TableHead>
                <TableHead className="text-[10px] font-bold uppercase tracking-widest text-slate-500 text-right py-4">Qty</TableHead>
                <TableHead className="text-[10px] font-bold uppercase tracking-widest text-slate-500 text-right py-4">Entry Price</TableHead>
                <TableHead className="text-[10px] font-bold uppercase tracking-widest text-slate-500 text-right py-4">Exit Price</TableHead>
                <TableHead className="text-[10px] font-bold uppercase tracking-widest text-slate-500 text-right py-4">Net P&L</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading && logs.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="h-64 text-center">
                    <GlobalLoader text="Loading P&L Report..." fullHeight={false} />
                  </TableCell>
                </TableRow>
              ) : logs.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="h-64 text-center text-slate-500 font-medium">
                    No closed positions found.
                  </TableCell>
                </TableRow>
              ) : (
                logs.map((log) => {
                  const pnl = Number(log.realized_pnl);
                  const isProfit = pnl >= 0;
                  
                  return (
                    <TableRow key={log.id} className="border-slate-800/50 hover:bg-white/[0.02] transition-colors group">
                      <TableCell className="py-4 text-slate-400 font-mono text-xs">
                        {new Date(log.exit_time).toLocaleString("en-IN", {
                          day: "numeric",
                          month: "short",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </TableCell>
                      <TableCell className="py-4">
                        <div className="flex items-center gap-3">
                          <div className={cn(
                            "px-2 py-0.5 rounded-lg text-[10px] font-black",
                            log.side === "LONG" ? "bg-emerald-500/10 text-emerald-500" : "bg-rose-500/10 text-rose-500"
                          )}>
                            {log.side}
                          </div>
                          <span className="font-black text-slate-100">{log.instrument?.symbol}</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-right text-slate-100 font-mono font-bold py-4">
                        {log.quantity}
                      </TableCell>
                      <TableCell className="text-right py-4">
                        <p className="text-sm font-bold text-slate-300 font-mono">
                          ₹{Number(log.entry_price).toFixed(2)}
                        </p>
                      </TableCell>
                      <TableCell className="text-right py-4">
                        <p className="text-sm font-bold text-slate-300 font-mono">
                          ₹{Number(log.exit_price).toFixed(2)}
                        </p>
                      </TableCell>
                      <TableCell className="text-right py-4">
                        <div className="flex items-center justify-end gap-2">
                          <span className={cn(
                            "text-sm font-black font-mono tracking-tight",
                            isProfit ? "text-emerald-400" : "text-rose-400"
                          )}>
                            {isProfit ? "+" : "-"}₹{Math.abs(pnl).toFixed(2)}
                          </span>
                          {isProfit ? (
                            <TrendingUp className="h-4 w-4 text-emerald-500" />
                          ) : (
                            <TrendingDown className="h-4 w-4 text-rose-500" />
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </div>
      </Card>

      {/* Pagination */}
      {totalCount > 50 && (
        <div className="flex items-center justify-between px-2 pt-2">
          <div className="text-sm font-medium text-slate-500">
            Showing {(page - 1) * 50 + 1} to {Math.min(page * 50, totalCount)} of {totalCount} records
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page === 1 || loading}
              onClick={() => onPageChange(page - 1)}
              className="border-slate-800 bg-slate-900/50 text-slate-300 hover:bg-slate-800 hover:text-white transition-colors"
            >
              <ChevronLeft className="h-4 w-4 mr-1" />
              Previous
            </Button>
            <div className="flex items-center gap-1">
              <span className="text-sm font-medium text-slate-400 px-3 py-1 bg-slate-900/30 rounded-md border border-slate-800/50">
                Page {page} of {totalPages}
              </span>
            </div>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages || loading}
              onClick={() => onPageChange(page + 1)}
              className="border-slate-800 bg-slate-900/50 text-slate-300 hover:bg-slate-800 hover:text-white transition-colors"
            >
              Next
              <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
