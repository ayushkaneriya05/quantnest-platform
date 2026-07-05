import { useEffect, useState } from "react";
import { Briefcase, TrendingUp, User } from "lucide-react";

import { usePageActions } from "@/shared/context/PageActionsContext";
import AccountSummary from "./components/AccountSummary";
import PortfolioDisplay from "./components/PortfolioDisplay";
import ChartView from "./components/ChartView";
import OrderModal from "./components/OrderModal";
import Watchlist from "./components/Watchlist";
import usePaperTradingTerminal from "./hooks/usePaperTradingTerminal";

export default function PaperTrading() {
  const [activeTab, setActiveTab] = useState("trading");
  const { setPageHeader, clearPageHeader } = usePageActions();

  const {
    loading,
    watchlist,
    account,
    positions,
    openOrders,
    recentTrades,
    terminalMetrics,
    selectedSymbol,
    selectedInstrumentId,
    setSelectedSymbol,
    watchlistWidth,
    setWatchlistWidth,
    isOrderModalOpen,
    transactionType,
    openOrderModal,
    closeOrderModal,
    handleOrderPlaced,
    refreshSnapshot,
    addToWatchlist,
    removeFromWatchlist,
  } = usePaperTradingTerminal();

  // Inject tab navigation into MainContentHeader
  useEffect(() => {
    const HeaderTabs = () => (
      <div className="flex space-x-1 bg-gray-800/30 border border-gray-700/30 rounded-lg p-1 w-full max-w-md mx-auto sm:mx-0 sm:ml-4">
        <button
          onClick={() => setActiveTab("trading")}
          className={`flex-1 flex justify-center items-center gap-2 rounded-md px-3 sm:px-4 py-2 sm:py-2.5 text-xs sm:text-sm font-medium transition-all duration-200 ${
            activeTab === "trading"
              ? "bg-gray-700/70 text-slate-100 shadow-sm"
              : "text-slate-400 hover:text-slate-300 hover:bg-gray-800/50"
          }`}
        >
          <TrendingUp className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
          <span className="hidden sm:inline">Trading</span>
        </button>
        <button
          onClick={() => setActiveTab("portfolio")}
          className={`flex-1 flex justify-center items-center gap-2 rounded-md px-3 sm:px-4 py-2 sm:py-2.5 text-xs sm:text-sm font-medium transition-all duration-200 ${
            activeTab === "portfolio"
              ? "bg-gray-700/70 text-slate-100 shadow-sm"
              : "text-slate-400 hover:text-slate-300 hover:bg-gray-800/50"
          }`}
        >
          <Briefcase className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
          <span className="hidden sm:inline">Portfolio</span>
        </button>
        <button
          onClick={() => setActiveTab("account")}
          className={`flex-1 flex justify-center items-center gap-2 rounded-md px-3 sm:px-4 py-2 sm:py-2.5 text-xs sm:text-sm font-medium transition-all duration-200 ${
            activeTab === "account"
              ? "bg-gray-700/70 text-slate-100 shadow-sm"
              : "text-slate-400 hover:text-slate-300 hover:bg-gray-800/50"
          }`}
        >
          <User className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
          <span className="hidden sm:inline">Account</span>
        </button>
      </div>
    );

    setPageHeader(<HeaderTabs />);

    return () => {
      clearPageHeader();
    };
  }, [setPageHeader, clearPageHeader, activeTab]);

  const handleResizeStart = (event) => {
    event.preventDefault();
    const startX = event.clientX;
    const startWidth = watchlistWidth;

    const handleMouseMove = (moveEvent) => {
      const nextWidth = Math.max(
        280,
        Math.min(460, startWidth + (moveEvent.clientX - startX)),
      );
      setWatchlistWidth(nextWidth);
    };

    const handleMouseUp = () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
      document.body.style.userSelect = "";
      document.body.style.cursor = "";
    };

    document.body.style.userSelect = "none";
    document.body.style.cursor = "col-resize";
    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
  };

  return (
    <div
      className={`w-full text-white ${activeTab === "trading" ? "h-full flex flex-col overflow-hidden" : "container-padding pt-6 pb-12"}`}
    >
      <div
        className={`w-full ${activeTab === "trading" ? "flex-1 flex flex-col min-h-0 px-4 py-4" : ""}`}
      >
        {activeTab === "trading" && (
          <div className="flex-1 flex flex-col min-h-0 animate-in fade-in slide-in-from-bottom-4 duration-500">
            {/* Main Trading Layout: Watchlist + Chart */}
            <div className="flex-1 flex gap-4 min-h-0">
              {/* Watchlist (Desktop) */}
              <div
                className="hidden lg:block shrink-0"
                style={{ width: `${watchlistWidth}px` }}
              >
                <div className="relative h-full">
                  <Watchlist
                    items={watchlist}
                    loading={loading}
                    activeSymbol={selectedSymbol}
                    onSymbolSelect={setSelectedSymbol}
                    onAddToWatchlist={addToWatchlist}
                    onRemoveFromWatchlist={removeFromWatchlist}
                    onRefresh={refreshSnapshot}
                  />
                  <div
                    onMouseDown={handleResizeStart}
                    className="absolute right-[-8px] top-0 h-full w-4 cursor-col-resize"
                  />
                </div>
              </div>

              {/* Chart */}
              <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-4">
                <div className="flex-1 min-h-0 min-w-0">
                  <ChartView
                    symbol={selectedSymbol}
                    instrumentId={selectedInstrumentId}
                    onBuyClick={() => openOrderModal("BUY")}
                    onSellClick={() => openOrderModal("SELL")}
                    className="h-full"
                  />
                </div>

                {/* Watchlist (Mobile) - only visible if screen is small */}
                <div className="lg:hidden flex-none">
                  <Watchlist
                    items={watchlist}
                    loading={loading}
                    activeSymbol={selectedSymbol}
                    onSymbolSelect={setSelectedSymbol}
                    onAddToWatchlist={addToWatchlist}
                    onRemoveFromWatchlist={removeFromWatchlist}
                    onRefresh={refreshSnapshot}
                    className="max-h-48"
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === "portfolio" && (
          <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
            <PortfolioDisplay
              positions={positions}
              orders={openOrders}
              onRefresh={refreshSnapshot}
            />
          </div>
        )}

        {activeTab === "account" && (
          <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
            <AccountSummary
              account={account}
              trades={recentTrades}
              metrics={terminalMetrics}
              onRefresh={refreshSnapshot}
            />
          </div>
        )}
      </div>

      <OrderModal
        isOpen={isOrderModalOpen}
        onClose={closeOrderModal}
        symbol={selectedSymbol}
        transactionType={transactionType}
        onOrderPlaced={handleOrderPlaced}
      />
    </div>
  );
}
