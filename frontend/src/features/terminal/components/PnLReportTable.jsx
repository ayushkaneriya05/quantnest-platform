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
      <Card className="bg-background/40 border-border/50 backdrop-blur-xl overflow-hidden rounded-3xl">
        <div className="overflow-x-auto scrollbar-thin-theme min-h-[400px]">
          <Table>
            <TableHeader>
              <TableRow className="border-border/50 hover:bg-transparent bg-card/40">
                <TableHead className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground py-4">Exit Time</TableHead>
                <TableHead className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground py-4">Symbol</TableHead>
                <TableHead className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground text-right py-4">Qty</TableHead>
                <TableHead className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground text-right py-4">Entry Price</TableHead>
                <TableHead className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground text-right py-4">Exit Price</TableHead>
                <TableHead className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground text-right py-4">Net P&L</TableHead>
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
                  <TableCell colSpan={6} className="h-64 text-center text-muted-foreground font-medium">
                    No closed positions found.
                  </TableCell>
                </TableRow>
              ) : (
                logs.map((log) => {
                  const pnl = Number(log.realized_pnl);
                  const isProfit = pnl >= 0;
                  
                  return (
                    <TableRow key={log.id} className="border-border/50 hover:bg-muted/50 transition-colors group">
                      <TableCell className="py-4 text-muted-foreground font-mono text-xs">
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
                            log.side === "LONG" ? "bg-emerald-500/10 text-success" : "bg-rose-500/10 text-loss"
                          )}>
                            {log.side}
                          </div>
                          <span className="font-black text-foreground">{log.instrument?.symbol}</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-right text-foreground font-mono font-bold py-4">
                        {log.quantity}
                      </TableCell>
                      <TableCell className="text-right py-4">
                        <p className="text-sm font-bold text-foreground font-mono">
                          ₹{Number(log.entry_price).toFixed(2)}
                        </p>
                      </TableCell>
                      <TableCell className="text-right py-4">
                        <p className="text-sm font-bold text-foreground font-mono">
                          ₹{Number(log.exit_price).toFixed(2)}
                        </p>
                      </TableCell>
                      <TableCell className="text-right py-4">
                        <div className="flex items-center justify-end gap-2">
                          <span className={cn(
                            "text-sm font-black font-mono tracking-tight",
                            isProfit ? "text-emerald-700 dark:text-emerald-400" : "text-rose-700 dark:text-rose-400"
                          )}>
                            {isProfit ? "+" : "-"}₹{Math.abs(pnl).toFixed(2)}
                          </span>
                          {isProfit ? (
                            <TrendingUp className="h-4 w-4 text-success" />
                          ) : (
                            <TrendingDown className="h-4 w-4 text-loss" />
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
          <div className="text-sm font-medium text-muted-foreground">
            Showing {(page - 1) * 50 + 1} to {Math.min(page * 50, totalCount)} of {totalCount} records
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page === 1 || loading}
              onClick={() => onPageChange(page - 1)}
              className="border-border bg-card/50 text-foreground hover:bg-secondary hover:text-foreground transition-colors"
            >
              <ChevronLeft className="h-4 w-4 mr-1" />
              Previous
            </Button>
            <div className="flex items-center gap-1">
              <span className="text-sm font-medium text-muted-foreground px-3 py-1 bg-card/30 rounded-md border border-border/50">
                Page {page} of {totalPages}
              </span>
            </div>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages || loading}
              onClick={() => onPageChange(page + 1)}
              className="border-border bg-card/50 text-foreground hover:bg-secondary hover:text-foreground transition-colors"
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
