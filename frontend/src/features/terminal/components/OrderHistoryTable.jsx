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
import { ChevronLeft, ChevronRight, Eye } from "lucide-react";
import { GlobalLoader } from "@/shared/components/ui/global-loader";

export default function OrderHistoryTable({
  orders,
  loading,
  page,
  totalCount,
  onPageChange,
}) {
  const totalPages = Math.ceil(totalCount / 50);

  const getStatusColor = (status) => {
    switch (status) {
      case "COMPLETE":
        return "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20";
      case "REJECTED":
      case "CANCELLED":
        return "bg-rose-500/10 text-rose-700 dark:text-rose-400 border-rose-500/20";
      case "OPEN":
        return "bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20";
      default:
        return "bg-muted/10 text-muted-foreground border-border/20";
    }
  };

  return (
    <div className="space-y-4">
      <Card className="bg-background/40 border-border/50 backdrop-blur-xl overflow-hidden rounded-3xl">
        <div className="overflow-x-auto scrollbar-thin-theme min-h-[400px]">
          <Table>
            <TableHeader>
              <TableRow className="border-border/50 hover:bg-transparent bg-card/40">
                <TableHead className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground py-4">Time</TableHead>
                <TableHead className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground py-4">Symbol</TableHead>
                <TableHead className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground py-4">Type</TableHead>
                <TableHead className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground text-right py-4">Qty</TableHead>
                <TableHead className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground text-right py-4">Price</TableHead>
                <TableHead className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground text-right py-4">Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading && orders.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="h-64 text-center">
                    <GlobalLoader text="Loading orders..." fullHeight={false} />
                  </TableCell>
                </TableRow>
              ) : orders.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="h-64 text-center text-muted-foreground font-medium">
                    No orders found matching your criteria.
                  </TableCell>
                </TableRow>
              ) : (
                orders.map((order) => (
                  <TableRow key={order.id} className="border-border/50 hover:bg-muted/50 transition-colors group">
                    <TableCell className="py-4 text-muted-foreground font-mono text-xs">
                      {new Date(order.created_at).toLocaleString("en-IN", {
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
                          order.transaction_type === "BUY" ? "bg-emerald-500/10 text-success" : "bg-rose-500/10 text-loss"
                        )}>
                          {order.transaction_type}
                        </div>
                        <span className="font-black text-foreground">{order.instrument?.symbol}</span>
                      </div>
                    </TableCell>
                    <TableCell className="py-4">
                      <span className="text-[10px] font-bold text-muted-foreground bg-secondary px-2 py-0.5 rounded-md border border-border">
                        {order.order_type}
                      </span>
                    </TableCell>
                    <TableCell className="text-right text-foreground font-mono font-bold py-4">
                      {order.quantity}
                    </TableCell>
                    <TableCell className="text-right py-4">
                      <p className="text-xs font-bold text-foreground font-mono">
                        {order.price ? `₹${Number(order.price).toFixed(2)}` : order.order_type === "STOP" ? `Trigger: ₹${Number(order.trigger_price).toFixed(2)}` : "MARKET"}
                      </p>
                    </TableCell>
                    <TableCell className="text-right py-4">
                      <Badge className={cn("text-[10px] px-2 py-0.5 rounded-md border", getStatusColor(order.status))}>
                        {order.status}
                      </Badge>
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
          <div className="text-sm font-medium text-muted-foreground">
            Showing {(page - 1) * 50 + 1} to {Math.min(page * 50, totalCount)} of {totalCount} orders
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
