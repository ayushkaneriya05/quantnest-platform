import React, { useState, useEffect } from "react";
import { Search, FilterX, RefreshCw } from "lucide-react";
import { Input } from "@/shared/components/ui/input";
import { Button } from "@/shared/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select";
import useHistoricalData from "../hooks/useHistoricalData";
import OrderHistoryTable from "./OrderHistoryTable";
import TradeHistoryTable from "./TradeHistoryTable";
import PnLReportTable from "./PnLReportTable";

export default function HistoryDisplay() {
  const [activeSubTab, setActiveSubTab] = useState("orders"); // orders | trades | pnl
  const {
    orders,
    ordersLoading,
    ordersTotalCount,
    fetchOrders,
    trades,
    tradesLoading,
    tradesTotalCount,
    fetchTrades,
    pnlLogs,
    pnlLoading,
    pnlTotalCount,
    fetchPnlLogs,
  } = useHistoricalData();

  // Filters and Pagination
  const [symbolFilter, setSymbolFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [page, setPage] = useState(1);

  useEffect(() => {
    const params = {
      page,
      symbol: symbolFilter || undefined,
      status: statusFilter !== "all" ? statusFilter : undefined,
    };
    
    if (activeSubTab === "orders") {
      fetchOrders(params);
    } else if (activeSubTab === "trades") {
      fetchTrades(params);
    } else if (activeSubTab === "pnl") {
      // P&L Report doesn't use statusFilter
      const pnlParams = {
        page,
        symbol: symbolFilter || undefined,
      };
      fetchPnlLogs(pnlParams);
    }
  }, [activeSubTab, page, symbolFilter, statusFilter, fetchOrders, fetchTrades, fetchPnlLogs]);

  const handleRefresh = () => {
    const params = {
      page,
      symbol: symbolFilter || undefined,
      status: statusFilter !== "all" ? statusFilter : undefined,
    };
    if (activeSubTab === "orders") {
      fetchOrders(params);
    } else if (activeSubTab === "trades") {
      fetchTrades(params);
    } else if (activeSubTab === "pnl") {
      const pnlParams = {
        page,
        symbol: symbolFilter || undefined,
      };
      fetchPnlLogs(pnlParams);
    }
  };

  const clearFilters = () => {
    setSymbolFilter("");
    setStatusFilter("all");
    setPage(1);
  };

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Sub Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-1 bg-slate-900/50 p-1 rounded-xl border border-slate-800 backdrop-blur-md">
          <button
            onClick={() => {
              setActiveSubTab("orders");
              clearFilters();
            }}
            className={`flex-1 sm:flex-none px-6 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
              activeSubTab === "orders"
                ? "bg-slate-800 text-white shadow-sm"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
            }`}
          >
            Order Book
          </button>
          <button
            onClick={() => {
              setActiveSubTab("trades");
              clearFilters();
            }}
            className={`flex-1 sm:flex-none px-6 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
              activeSubTab === "trades"
                ? "bg-slate-800 text-white shadow-sm"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
            }`}
          >
            Trade Book
          </button>
          <button
            onClick={() => {
              setActiveSubTab("pnl");
              clearFilters();
            }}
            className={`flex-1 sm:flex-none px-6 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
              activeSubTab === "pnl"
                ? "bg-slate-800 text-white shadow-sm"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
            }`}
          >
            P&L Report
          </button>
        </div>

        <Button 
          variant="outline" 
          onClick={handleRefresh} 
          disabled={ordersLoading || tradesLoading || pnlLoading}
          className="border-slate-800 bg-slate-900/50 text-slate-300 hover:bg-slate-800 hover:text-white"
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${(ordersLoading || tradesLoading || pnlLoading) ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center gap-4 bg-slate-900/40 p-3 rounded-2xl border border-slate-800">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
          <Input
            placeholder="Search by symbol..."
            value={symbolFilter}
            onChange={(e) => {
              setSymbolFilter(e.target.value);
              setPage(1);
            }}
            className="pl-10 bg-slate-950/50 border-slate-800 text-white placeholder:text-slate-600 focus-visible:ring-slate-700"
          />
        </div>

        {activeSubTab === "orders" && (
          <div className="w-[180px]">
            <Select 
              value={statusFilter} 
              onValueChange={(val) => {
                setStatusFilter(val);
                setPage(1);
              }}
            >
              <SelectTrigger className="bg-slate-950/50 border-slate-800 text-white focus:ring-slate-700">
                <SelectValue placeholder="All Status" />
              </SelectTrigger>
              <SelectContent className="bg-slate-900 border-slate-800 text-slate-300">
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="OPEN">Open</SelectItem>
                <SelectItem value="COMPLETE">Complete</SelectItem>
                <SelectItem value="CANCELLED">Cancelled</SelectItem>
                <SelectItem value="REJECTED">Rejected</SelectItem>
              </SelectContent>
            </Select>
          </div>
        )}

        {(symbolFilter || statusFilter !== "all") && (
          <Button variant="ghost" onClick={clearFilters} className="text-slate-400 hover:text-white">
            <FilterX className="h-4 w-4 mr-2" />
            Clear
          </Button>
        )}
      </div>

      {/* Content */}
      {activeSubTab === "orders" && (
        <OrderHistoryTable
          orders={orders}
          loading={ordersLoading}
          page={page}
          totalCount={ordersTotalCount}
          onPageChange={setPage}
        />
      )}
      {activeSubTab === "trades" && (
        <TradeHistoryTable
          trades={trades}
          loading={tradesLoading}
          page={page}
          totalCount={tradesTotalCount}
          onPageChange={setPage}
        />
      )}
      {activeSubTab === "pnl" && (
        <PnLReportTable
          logs={pnlLogs}
          loading={pnlLoading}
          page={page}
          totalCount={pnlTotalCount}
          onPageChange={setPage}
        />
      )}
    </div>
  );
}
