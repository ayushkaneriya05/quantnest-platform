import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/shared/components/ui/table";
import { Badge } from "@/shared/components/ui/badge";
import { format } from "date-fns";

import { formatNumber } from "@/shared/utils/formatters";
import { statusTone as statusColors } from "@/shared/constants/statusColors";

export default function LiveOrdersTable({ orders }) {
  if (!orders || orders.length === 0) {
    return (
      <div className="py-12 text-center text-gray-500 border border-dashed border-gray-800 rounded-2xl">
        No recent orders.
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-gray-800 bg-gray-900/40 overflow-hidden">
      <Table>
        <TableHeader className="bg-gray-950/40">
          <TableRow className="border-gray-800 hover:bg-transparent">
            <TableHead className="text-gray-500 font-medium">Time</TableHead>
            <TableHead className="text-gray-500 font-medium">Instrument</TableHead>
            <TableHead className="text-gray-500 font-medium">Side</TableHead>
            <TableHead className="text-gray-500 font-medium">Qty</TableHead>
            <TableHead className="text-gray-500 font-medium text-right">Price</TableHead>
            <TableHead className="text-gray-500 font-medium text-right">Avg Fill</TableHead>
            <TableHead className="text-gray-500 font-medium text-center">Status</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {orders.map((order) => (
            <TableRow key={order.id} className="border-gray-800 hover:bg-white/5 transition-colors">
              <TableCell className="text-gray-400 text-xs">
                {format(new Date(order.placed_at || Date.now()), "HH:mm:ss")}
              </TableCell>
              <TableCell className="font-semibold text-white">
                {order.instrument_symbol}
              </TableCell>
              <TableCell>
                <span className={order.side === 'BUY' ? 'text-emerald-400 font-bold' : 'text-rose-400 font-bold'}>
                  {order.side}
                </span>
              </TableCell>
              <TableCell className="text-gray-300">
                {order.filled_quantity} / {order.quantity}
              </TableCell>
              <TableCell className="text-right text-gray-300 font-mono">
                {formatNumber(order.price)}
              </TableCell>
              <TableCell className="text-right text-gray-300 font-mono">
                {order.avg_fill_price ? formatNumber(order.avg_fill_price) : "-"}
              </TableCell>
              <TableCell className="text-center">
                <Badge className={statusColors[order.status] || "bg-gray-500/10 text-gray-300 border-gray-500/20"}>
                  {order.status}
                </Badge>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
