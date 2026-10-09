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
import useHistoricalData from "@/features/terminal/hooks/useHistoricalData.js";
import OrderHistoryTable from "@/features/terminal/components/OrderHistoryTable.jsx";
import TradeHistoryTable from "@/features/terminal/components/TradeHistoryTable.jsx";
import PnLReportTable from "@/features/terminal/components/PnLReportTable.jsx";

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
        <div className="flex items-center gap-1 bg-card/50 p-1 rounded-xl border border-border backdrop-blur-md">
          <button
            onClick={() => {
              setActiveSubTab("orders");
              clearFilters();
            }}
            className={`flex-1 sm:flex-none px-6 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
              activeSubTab === "orders"
                ? "bg-secondary text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
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
                ? "bg-secondary text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
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
                ? "bg-secondary text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
            }`}
          >
            P&L Report
          </button>
        </div>

        <Button 
          variant="outline" 
          onClick={handleRefresh} 
          disabled={ordersLoading || tradesLoading || pnlLoading}
          className="border-border bg-card/50 text-foreground hover:bg-secondary hover:text-foreground"
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${(ordersLoading || tradesLoading || pnlLoading) ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center gap-4 bg-card/40 p-3 rounded-2xl border border-border">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search by symbol..."
            value={symbolFilter}
            onChange={(e) => {
              setSymbolFilter(e.target.value);
              setPage(1);
            }}
            className="pl-10 bg-background/50 border-border text-foreground placeholder:text-muted-foreground focus-visible:ring-slate-700"
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
              <SelectTrigger className="bg-background/50 border-border text-foreground focus:ring-slate-700">
                <SelectValue placeholder="All Status" />
              </SelectTrigger>
              <SelectContent className="bg-card border-border text-foreground">
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
          <Button variant="ghost" onClick={clearFilters} className="text-muted-foreground hover:text-foreground">
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
