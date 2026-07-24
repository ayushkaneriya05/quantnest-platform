import React, { useState } from "react";
import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/components/ui/button";
import { Card, CardContent } from "@/shared/components/ui/card";
import { Badge } from "@/shared/components/ui/badge";
import {
  Package,
  FileText,
  DollarSign,
  BarChart3,
  XCircle,
  X,
  Edit2,
  Settings2,
  ArrowRightLeft,
} from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/shared/components/ui/table";
import { useLivePositionsPnL } from "@/shared/hooks/useLivePositionsPnL";
import api from "@/shared/services/api";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { customConfirm } from "@/shared/components/ui/custom-dialog";

import ModifyOrderModal from "./ModifyOrderModal";
import ModifyPositionModal from "./ModifyPositionModal";

const StatCard = ({
  icon: Icon,
  title,
  value,
  subtitle,
  variant = "default",
}) => {
  const variants = {
    default: "border-slate-800/50 hover:border-sky-500/30",
    positive: "border-emerald-500/20 hover:border-emerald-500/40",
    negative: "border-rose-500/20 hover:border-rose-500/40",
  };

  return (
    <Card className={cn(
      "bg-slate-900/40 backdrop-blur-xl border-dashed transition-all duration-300",
      variants[variant] || variants.default
    )}>
      <CardContent className="p-5">
        <div className="flex items-center gap-4">
          <div className={cn(
            "p-3 rounded-2xl bg-slate-950/50 border border-white/5",
            variant === "positive" ? "text-emerald-400" : 
            variant === "negative" ? "text-rose-400" : "text-sky-400"
          )}>
            <Icon className="h-5 w-5" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">
              {title}
            </p>
            <p className="text-xl font-black text-white truncate tabular-nums">
              {value}
            </p>
            {subtitle && (
              <p className="text-[10px] text-slate-500 font-medium truncate mt-0.5 opacity-80">
                {subtitle}
              </p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

const safeNumber = (value, defaultValue = 0) => {
  const num = parseFloat(value);
  return isNaN(num) ? defaultValue : num;
};

const formatCurrency = (value) => {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 2,
  }).format(Number(value));
};

export default function PortfolioDisplay({ positions = [], orders = [], onRefresh }) {
  const { livePnLByPositionId, totals } = useLivePositionsPnL(positions);
  const totalInvestment = totals.totalInvested;
  const totalPnl = totals.totalUnrealizedPnL;
  const { notify } = useNotifications();
  
  // Modal states
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [selectedPosition, setSelectedPosition] = useState(null);
  const [isModifyOrderOpen, setIsModifyOrderOpen] = useState(false);
  const [isModifyPositionOpen, setIsModifyPositionOpen] = useState(false);

  const handleCancelOrder = async (orderId) => {
    try {
      await api.delete(`/trading/orders/${orderId}/`);
      notify.success("Order cancelled");
      if (onRefresh) onRefresh();
    } catch (error) {
      notify.error("Failed to cancel order");
    }
  };

  const handleClosePosition = async (position) => {
    const confirmClose = await customConfirm(`Are you sure you want to close ${position.instrument.symbol} position at Market Price?`);
    if (!confirmClose) return;

    try {
      const quantity = safeNumber(position.quantity);
      const transaction_type = quantity > 0 ? "SELL" : "BUY";
      
      await api.post("/trading/orders/", {
        instrument_symbol: position.instrument.symbol,
        order_type: "MARKET",
        transaction_type,
        quantity: Math.abs(quantity),
      });

      notify.success("Exit order placed successfully");
      if (onRefresh) onRefresh();
    } catch (error) {
      const errorData = error.response?.data;
      const errorMsg = errorData?.detail || 
                       (errorData && typeof errorData === 'object' ? Object.values(errorData).flat()[0] : null) ||
                       "Failed to place exit order";
      notify.error(errorMsg);
    }
  };

  const openModifyOrder = (order) => {
    setSelectedOrder(order);
    setIsModifyOrderOpen(true);
  };

  const openModifyPosition = (position) => {
    setSelectedPosition(position);
    setIsModifyPositionOpen(true);
  };



  return (
    <div className="space-y-6 animate-in fade-in duration-700">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        <StatCard
          icon={DollarSign}
          title="Total Investment"
          value={formatCurrency(totalInvestment)}
          subtitle="Capital deployed in active positions"
        />
        <StatCard
          icon={BarChart3}
          title="Unrealized P&L"
          value={formatCurrency(totalPnl)}
          subtitle={
            totalInvestment > 0
              ? `${((totalPnl / totalInvestment) * 100).toFixed(2)}% net return`
              : "No active investments"
          }
          variant={totalPnl >= 0 ? "positive" : "negative"}
        />
        <StatCard
          icon={Package}
          title="Portfolio Stats"
          value={`${positions.length} Active`}
          subtitle={`${orders.length} orders pending execution`}
        />
      </div>

      <div className="space-y-8">
        {/* Active Positions */}
        <section>
          <div className="flex items-center justify-between mb-4 px-2">
            <div className="flex items-center gap-2">
              <ArrowRightLeft className="h-5 w-5 text-sky-450" />
              <h3 className="font-black text-white uppercase tracking-tight">Active Positions</h3>
            </div>
          </div>
          
          {positions.length > 0 ? (
            <Card className="bg-slate-950/40 border-slate-800/50 backdrop-blur-xl overflow-hidden rounded-3xl">
              <div className="overflow-x-auto custom-scrollbar">
                <Table>
                  <TableHeader>
                    <TableRow className="border-slate-800/50 hover:bg-transparent bg-slate-900/40">
                      <TableHead className="text-[10px] font-bold uppercase tracking-widest text-slate-500 py-4">Instrument</TableHead>
                      <TableHead className="text-[10px] font-bold uppercase tracking-widest text-slate-500 text-right py-4">Qty</TableHead>
                      <TableHead className="text-[10px] font-bold uppercase tracking-widest text-slate-500 text-right py-4">Avg Price</TableHead>
                      <TableHead className="text-[10px] font-bold uppercase tracking-widest text-slate-500 text-right py-4">LTP</TableHead>
                      <TableHead className="text-[10px] font-bold uppercase tracking-widest text-slate-500 text-right py-4">Unrealized P&L</TableHead>
                      <TableHead className="text-[10px] font-bold uppercase tracking-widest text-slate-500 text-center py-4">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {positions.map((position) => {
                      const avgPrice = safeNumber(position.average_price);
                      const quantity = safeNumber(position.quantity);
                      const liveData = livePnLByPositionId[position.id] || { livePrice: safeNumber(position.current_price, avgPrice), pnl: 0 };
                      const currentPrice = liveData.livePrice;
                      const pnl = liveData.pnl;
                      
                      return (
                        <TableRow key={position.id} className="border-slate-800/50 hover:bg-white/[0.02] transition-colors group">
                          <TableCell className="py-4">
                            <div className="font-black text-slate-100">{position.instrument?.symbol}</div>
                            <div className="text-[10px] text-slate-500 truncate max-w-[150px] font-medium mt-0.5">
                              {position.instrument?.company_name}
                            </div>
                          </TableCell>
                          <TableCell className="text-right py-4">
                            <Badge className={cn(
                              "font-mono font-bold text-xs",
                              quantity > 0 ? "bg-emerald-500/10 text-emerald-400" : "bg-rose-500/10 text-rose-400"
                            )}>
                              {quantity > 0 ? "+" : ""}{quantity}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-right text-slate-400 font-mono text-sm py-4">₹{avgPrice.toFixed(2)}</TableCell>
                          <TableCell className="text-right text-slate-100 font-mono font-bold text-sm py-4">₹{currentPrice.toFixed(2)}</TableCell>
                          <TableCell className={cn(
                            "text-right font-mono font-black text-sm py-4",
                            pnl >= 0 ? "text-emerald-400" : "text-rose-400"
                          )}>
                            {pnl >= 0 ? "+" : ""}₹{pnl.toFixed(2)}
                            <div className="text-[9px] opacity-70">
                              {((pnl / (avgPrice * Math.abs(quantity))) * 100).toFixed(2)}%
                            </div>
                          </TableCell>
                          <TableCell className="text-center py-4 px-6 min-w-[100px]">
                            <div className="flex items-center justify-center gap-1">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => openModifyPosition(position)}
                                className="h-8 w-8 p-0 text-sky-450 hover:bg-sky-500/10 hover:text-sky-300 rounded-xl"
                                title="Adjust SL/TP"
                              >
                                <Settings2 className="h-4 w-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleClosePosition(position)}
                                className="h-8 w-8 p-0 text-rose-400 hover:bg-rose-500/10 hover:text-rose-300 rounded-xl"
                                title="Exit Market"
                              >
                                <XCircle className="h-4 w-4" />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            </Card>
          ) : (
            <div className="py-24 text-center bg-slate-900/20 rounded-[2.5rem] border border-dashed border-slate-800/60 transition-all hover:bg-slate-900/30">
              <div className="inline-flex p-5 rounded-3xl bg-slate-900/50 border border-slate-800 mb-4 text-slate-600">
                <Package className="h-10 w-10" />
              </div>
              <p className="text-slate-400 font-bold">Your portfolio is empty</p>
              <p className="text-xs text-slate-600 mt-1">Start trading to build your equity positions.</p>
            </div>
          )}
        </section>

        {/* Pending Orders */}
        {orders.length > 0 && (
          <section className="animate-in slide-in-from-bottom-5 duration-700">
            <div className="flex items-center gap-2 mb-4 px-2 text-slate-300">
              <FileText className="h-5 w-5 text-amber-500" />
              <h3 className="font-black text-white uppercase tracking-tight">Pending Orders</h3>
            </div>
            <Card className="bg-slate-950/40 border-slate-800/50 backdrop-blur-xl overflow-hidden rounded-3xl">
              <div className="overflow-x-auto custom-scrollbar">
                <Table>
                  <TableHeader>
                    <TableRow className="border-slate-800/50 hover:bg-transparent bg-slate-900/40">
                      <TableHead className="text-[10px] font-bold uppercase tracking-widest text-slate-500 py-4">Symbol</TableHead>
                      <TableHead className="text-[10px] font-bold uppercase tracking-widest text-slate-500 py-4">Type</TableHead>
                      <TableHead className="text-[10px] font-bold uppercase tracking-widest text-slate-500 text-right py-4">Qty</TableHead>
                      <TableHead className="text-[10px] font-bold uppercase tracking-widest text-slate-500 text-right py-4">Status / Price</TableHead>
                      <TableHead className="text-[10px] font-bold uppercase tracking-widest text-slate-500 text-center py-4">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {orders.map((order) => (
                      <TableRow key={order.id} className="border-slate-800/50 hover:bg-white/[0.02] transition-colors group">
                        <TableCell className="py-4">
                          <div className="flex items-center gap-3">
                            <div className={cn(
                              "px-2 py-0.5 rounded-lg text-[10px] font-black",
                              order.transaction_type === "BUY" ? "bg-emerald-500/10 text-emerald-500" : "bg-rose-500/10 text-rose-500"
                            )}>
                              {order.transaction_type}
                            </div>
                            <span className="font-black text-slate-100">{order.instrument?.symbol}</span>
                          </div>
                        </TableCell>
                        <TableCell className="py-4">
                          <span className="text-[10px] font-bold text-slate-500 bg-slate-800 px-2 py-0.5 rounded-md border border-slate-700">{order.order_type}</span>
                        </TableCell>
                        <TableCell className="text-right text-slate-100 font-mono font-bold py-4">{order.quantity}</TableCell>
                        <TableCell className="text-right py-4">
                          <p className="text-xs font-bold text-slate-300">
                            {order.price ? `₹${Number(order.price).toFixed(2)}` : order.order_type === "STOP" ? `Trigger: ₹${Number(order.trigger_price).toFixed(2)}` : "MARKET"}
                          </p>
                          <p className="text-[9px] text-amber-400 font-bold tracking-tighter mt-0.5">{order.status}</p>
                        </TableCell>
                        <TableCell className="text-center py-4 px-6 min-w-[200px]">
                          <div className="flex items-center justify-center gap-2">
                             <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => openModifyOrder(order)}
                              className="h-8 text-sky-450 hover:bg-sky-500/10 hover:text-sky-300 transition-all font-bold px-3 rounded-xl scale-90"
                            >
                              <Edit2 className="h-3 w-3 mr-1.5" />
                              Modify
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleCancelOrder(order.id)}
                              className="h-8 text-slate-500 hover:text-rose-400 transition-all font-bold px-3 rounded-xl scale-90"
                            >
                              <X className="h-3 w-3 mr-1.5" />
                              Cancel
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </Card>
          </section>
        )}
      </div>

      {/* Modals */}
      <ModifyOrderModal
        isOpen={isModifyOrderOpen}
        onClose={() => {
          setIsModifyOrderOpen(false);
          setSelectedOrder(null);
        }}
        order={selectedOrder}
        onOrderModified={onRefresh}
      />
      
      <ModifyPositionModal
        isOpen={isModifyPositionOpen}
        onClose={() => {
          setIsModifyPositionOpen(false);
          setSelectedPosition(null);
        }}
        position={selectedPosition}
        onPositionModified={onRefresh}
      />
    </div>
  );
}
