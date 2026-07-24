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
import { Badge } from "@/shared/components/ui/badge";
import { Card } from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { GlobalLoader } from "@/shared/components/ui/global-loader";

export default function TradeHistoryTable({
  trades,
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
                <TableHead className="text-[10px] font-bold uppercase tracking-widest text-slate-500 py-4">Execution Time</TableHead>
                <TableHead className="text-[10px] font-bold uppercase tracking-widest text-slate-500 py-4">Symbol</TableHead>
                <TableHead className="text-[10px] font-bold uppercase tracking-widest text-slate-500 py-4">Type</TableHead>
                <TableHead className="text-[10px] font-bold uppercase tracking-widest text-slate-500 text-right py-4">Qty</TableHead>
                <TableHead className="text-[10px] font-bold uppercase tracking-widest text-slate-500 text-right py-4">Fill Price</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading && trades.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="h-64 text-center">
                    <GlobalLoader text="Loading trades..." fullHeight={false} />
                  </TableCell>
                </TableRow>
              ) : trades.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="h-64 text-center text-slate-500 font-medium">
                    No trades found matching your criteria.
                  </TableCell>
                </TableRow>
              ) : (
                trades.map((trade) => (
                  <TableRow key={trade.id} className="border-slate-800/50 hover:bg-white/[0.02] transition-colors group">
                    <TableCell className="py-4 text-slate-400 font-mono text-xs">
                      {new Date(trade.timestamp).toLocaleString("en-IN", {
                        day: "numeric",
                        month: "short",
                        hour: "2-digit",
                        minute: "2-digit",
                        second: "2-digit",
                      })}
                    </TableCell>
                    <TableCell className="py-4">
                      <div className="flex items-center gap-3">
                        <div className={cn(
                          "px-2 py-0.5 rounded-lg text-[10px] font-black",
                          trade.transaction_type === "BUY" ? "bg-emerald-500/10 text-emerald-500" : "bg-rose-500/10 text-rose-500"
                        )}>
                          {trade.transaction_type}
                        </div>
                        <span className="font-black text-slate-100">{trade.instrument?.symbol}</span>
                      </div>
                    </TableCell>
                    <TableCell className="py-4">
                      <span className="text-[10px] font-bold text-slate-500 bg-slate-800 px-2 py-0.5 rounded-md border border-slate-700">
                        {trade.order_type}
                      </span>
                    </TableCell>
                    <TableCell className="text-right text-slate-100 font-mono font-bold py-4">
                      {trade.quantity}
                    </TableCell>
                    <TableCell className="text-right py-4">
                      <p className="text-sm font-bold text-emerald-400 font-mono">
                        ₹{Number(trade.executed_price).toFixed(2)}
                      </p>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </Card>

      {/* Pagination */}
      {totalCount > 50 && (
        <div className="flex items-center justify-between px-2 pt-2">
          <div className="text-sm font-medium text-slate-500">
            Showing {(page - 1) * 50 + 1} to {Math.min(page * 50, totalCount)} of {totalCount} trades
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
