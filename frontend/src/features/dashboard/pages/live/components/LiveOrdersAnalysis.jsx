import React, { useMemo } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
import { Badge } from "@/shared/components/ui/badge";
import { Activity, CheckCircle, Clock, AlertCircle } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/shared/components/ui/table";
import { formatNumber, formatDateTime } from "@/shared/utils/formatters";

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
    warning: "bg-amber-500/10 text-amber-400",
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

const getStatusVariant = (status) => {
  if (!status) return "default";
  const lower = status.toLowerCase();
  if (lower.includes("filled")) return "positive";
  if (lower.includes("cancel") || lower.includes("reject")) return "negative";
  if (lower.includes("pending") || lower.includes("new")) return "warning";
  return "default";
};

const getStatusColor = (status) => {
  if (!status) return "text-slate-400";
  const lower = status.toLowerCase();
  if (lower.includes("filled")) return "text-emerald-400";
  if (lower.includes("cancel") || lower.includes("reject"))
    return "text-rose-400";
  if (lower.includes("pending") || lower.includes("new"))
    return "text-amber-400";
  return "text-slate-400";
};

export default function LiveOrdersAnalysis({ orders = [], sessions = [] }) {
  const sessionsMap = useMemo(() => {
    return sessions.reduce((acc, s) => {
      acc[s.id] = s;
      return acc;
    }, {});
  }, [sessions]);

  const orderStats = useMemo(() => {
    if (!orders.length)
      return {
        total: 0,
        filled: 0,
        pending: 0,
        canceled: 0,
        avgFillTime: 0,
        totalValue: 0,
      };

    const filled = orders.filter((o) =>
      o.status?.toLowerCase().includes("filled"),
    ).length;
    const pending = orders.filter(
      (o) =>
        o.status?.toLowerCase().includes("new") ||
        o.status?.toLowerCase().includes("pending"),
    ).length;
    const canceled = orders.filter((o) =>
      o.status?.toLowerCase().includes("cancel"),
    ).length;
    const totalValue = orders.reduce(
      (sum, o) => sum + (o.price || 0) * (o.quantity || 0),
      0,
    );

    return {
      total: orders.length,
      filled,
      pending,
      canceled,
      avgFillTime: 0,
      totalValue,
    };
  }, [orders]);

  if (orders.length === 0) {
    return (
      <Card className="bg-slate-900/50 border-slate-800">
        <CardContent className="py-16 text-center">
          <Activity className="h-12 w-12 text-slate-600 mx-auto mb-4" />
          <p className="text-slate-400 text-lg">No orders</p>
          <p className="text-slate-500 text-sm mt-1">
            Orders will appear here when you place trades
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Order Statistics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <StatCard
          icon={Activity}
          title="Total Orders"
          value={orderStats.total}
          subtitle="All orders"
          variant="default"
        />
        <StatCard
          icon={CheckCircle}
          title="Filled"
          value={orderStats.filled}
          subtitle={`${((orderStats.filled / orderStats.total) * 100).toFixed(1)}%`}
          variant="positive"
        />
        <StatCard
          icon={Clock}
          title="Pending"
          value={orderStats.pending}
          subtitle={`${((orderStats.pending / orderStats.total) * 100).toFixed(1)}%`}
          variant="warning"
        />
        <StatCard
          icon={AlertCircle}
          title="Canceled"
          value={orderStats.canceled}
          subtitle={`${orderStats.total > 0 ? ((orderStats.canceled / orderStats.total) * 100).toFixed(1) : 0}%`}
          variant="negative"
        />
        <StatCard
          icon={Activity}
          title="Total Value"
          value={`₹${formatNumber(Math.abs(orderStats.totalValue))}`}
          subtitle="Notional value"
          variant="default"
        />
      </div>

      {/* Detailed Orders Table */}
      <Card className="bg-slate-900/50 border-slate-800 overflow-hidden">
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">Order Details</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader className="bg-slate-800/50">
                <TableRow className="border-slate-700 hover:bg-transparent">
                  <TableHead className="text-slate-300 font-bold">
                    Order ID
                  </TableHead>
                  <TableHead className="text-slate-300 font-bold">
                    Symbol
                  </TableHead>
                  <TableHead className="text-slate-300 font-bold">
                    Type
                  </TableHead>
                  <TableHead className="text-slate-300 font-bold text-right">
                    Qty
                  </TableHead>
                  <TableHead className="text-slate-300 font-bold text-right">
                    Price
                  </TableHead>
                  <TableHead className="text-slate-300 font-bold text-right">
                    Filled
                  </TableHead>
                  <TableHead className="text-slate-300 font-bold">
                    Status
                  </TableHead>
                  <TableHead className="text-slate-300 font-bold">
                    Placed At
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {orders.map((order, idx) => {
                  const filled = order.filled_quantity || 0;
                  const total = order.quantity || 0;
                  const fillPercent = total > 0 ? (filled / total) * 100 : 0;

                  return (
                    <TableRow
                      key={`${order.order_id}-${idx}`}
                      className="border-slate-700 hover:bg-slate-800/30 transition-colors"
                    >
                      <TableCell className="font-mono text-slate-300 text-sm">
                        {order.order_id?.substring(0, 8)}...
                      </TableCell>
                      <TableCell className="font-medium text-white">
                        {order.symbol}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className={`${order.side === "BUY" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30" : "bg-rose-500/10 text-rose-400 border-rose-500/30"} text-xs`}
                        >
                          {order.side}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right text-slate-300">
                        {formatNumber(total)}
                      </TableCell>
                      <TableCell className="text-right text-slate-300">
                        ₹{formatNumber(order.price)}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-2">
                          <div className="w-20 h-2 bg-slate-700 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-emerald-500 transition-all"
                              style={{ width: `${fillPercent}%` }}
                            />
                          </div>
                          <span className="text-slate-300 text-sm min-w-12">
                            {fillPercent.toFixed(0)}%
                          </span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className={`${getStatusVariant(order.status)} text-xs`}
                        >
                          {order.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-slate-400 text-sm">
                        {formatDateTime(order.created_at)}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Order Status Distribution */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Status Breakdown */}
        <Card className="bg-slate-900/50 border-slate-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-emerald-400" />
              <span>Filled Orders</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-emerald-400">
              {orderStats.filled}
            </p>
            <p className="text-slate-400 text-sm mt-2">
              {((orderStats.filled / orderStats.total) * 100).toFixed(1)}% of
              total
            </p>
          </CardContent>
        </Card>

        <Card className="bg-slate-900/50 border-slate-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <Clock className="h-4 w-4 text-amber-400" />
              <span>Pending Orders</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-amber-400">
              {orderStats.pending}
            </p>
            <p className="text-slate-400 text-sm mt-2">
              {((orderStats.pending / orderStats.total) * 100).toFixed(1)}% of
              total
            </p>
          </CardContent>
        </Card>

        <Card className="bg-slate-900/50 border-slate-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-rose-400" />
              <span>Canceled Orders</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-rose-400">
              {orderStats.canceled}
            </p>
            <p className="text-slate-400 text-sm mt-2">
              {orderStats.total > 0
                ? ((orderStats.canceled / orderStats.total) * 100).toFixed(1)
                : 0}
              % of total
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Order Flow Analysis */}
      <Card className="bg-slate-900/50 border-slate-800">
        <CardHeader>
          <CardTitle className="text-lg">Order Flow</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {(() => {
            const buyOrders = orders.filter((o) => o.side === "BUY").length;
            const sellOrders = orders.filter((o) => o.side === "SELL").length;
            const buyCost = orders
              .filter((o) => o.side === "BUY")
              .reduce((sum, o) => sum + (o.price || 0) * (o.quantity || 0), 0);
            const sellCost = orders
              .filter((o) => o.side === "SELL")
              .reduce((sum, o) => sum + (o.price || 0) * (o.quantity || 0), 0);

            return (
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 bg-slate-800/30 rounded-lg border border-slate-700">
                  <p className="text-slate-500 text-xs uppercase tracking-wider font-bold mb-2">
                    Buy Orders
                  </p>
                  <p className="text-emerald-400 font-bold text-lg">
                    {buyOrders}
                  </p>
                  <p className="text-slate-400 text-sm">
                    Value: ₹{formatNumber(buyCost)}
                  </p>
                </div>
                <div className="p-4 bg-slate-800/30 rounded-lg border border-slate-700">
                  <p className="text-slate-500 text-xs uppercase tracking-wider font-bold mb-2">
                    Sell Orders
                  </p>
                  <p className="text-rose-400 font-bold text-lg">
                    {sellOrders}
                  </p>
                  <p className="text-slate-400 text-sm">
                    Value: ₹{formatNumber(sellCost)}
                  </p>
                </div>
              </div>
            );
          })()}
        </CardContent>
      </Card>
    </div>
  );
}
