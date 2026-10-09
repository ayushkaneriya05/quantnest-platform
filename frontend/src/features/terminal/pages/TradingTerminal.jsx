import PageTabs from "@/shared/components/PageTabs";
import { Button } from "@/shared/components/ui/button";
import { Dialog, DialogContent, DialogTitle } from "@/shared/components/ui/dialog";
import { List } from "lucide-react";
import { useEffect, useState } from "react";
import { Briefcase, TrendingUp, User, Clock } from "lucide-react";

import { usePageActions } from "@/shared/context/pageActions";
import AccountSummary from "@/features/terminal/components/AccountSummary.jsx";
import PortfolioDisplay from "@/features/terminal/components/PortfolioDisplay.jsx";
import ChartView from "@/features/terminal/components/ChartView.jsx";
import OrderModal from "@/features/terminal/components/OrderModal.jsx";
import Watchlist from "@/features/terminal/components/Watchlist.jsx";
import HistoryDisplay from "@/features/terminal/components/HistoryDisplay.jsx";
import usePaperTradingTerminal from "@/features/terminal/hooks/usePaperTradingTerminal.js";

export default function TradingTerminal() {
  const [watchlistOpen, setWatchlistOpen] = useState(false);
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
    const HeaderTabs = () => <PageTabs value={activeTab} onValueChange={setActiveTab} label="Terminal sections" items={[
      { value: "trading", label: "Chart", icon: TrendingUp },
      { value: "portfolio", label: "Positions & orders", icon: Briefcase },
      { value: "history", label: "History", icon: Clock },
      { value: "account", label: "Account", icon: User },
    ]} />;

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
      className={`w-full text-foreground ${activeTab === "trading" ? "min-h-0 flex-1 flex flex-col" : "container-padding pt-6 pb-12"}`}
    >
      <div
        className={`w-full ${activeTab === "trading" ? "flex-1 flex flex-col min-h-0 px-3 py-3 sm:px-4 sm:py-4" : ""}`}
      >
        {activeTab === "trading" && (
          <div className="flex-1 flex flex-col min-h-0 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="mb-2 flex shrink-0 items-center justify-between gap-2 lg:hidden">
              <span className="min-w-0 truncate text-sm font-medium">{selectedSymbol || "Choose an instrument"}</span>
              <Button variant="outline" size="sm" onClick={() => setWatchlistOpen(true)}><List className="h-4 w-4" />Watchlist</Button>
            </div>
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
                <div className="flex-1 min-h-[440px] min-w-0 lg:min-h-0">
                  <ChartView
                    symbol={selectedSymbol}
                    instrumentId={selectedInstrumentId}
                    onBuyClick={() => openOrderModal("BUY")}
                    onSellClick={() => openOrderModal("SELL")}
                    className="h-full"
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

        {activeTab === "history" && (
          <HistoryDisplay />
        )}
      </div>

      <Dialog open={watchlistOpen} onOpenChange={setWatchlistOpen}>
        <DialogContent aria-describedby={undefined} className="left-0 top-[calc(var(--viewport-height)_*_0.15)] flex h-[calc(var(--viewport-height)_*_0.85)] max-h-[85dvh] w-full max-w-none translate-x-0 translate-y-0 flex-col overflow-hidden rounded-b-none rounded-t-2xl p-4">
          <DialogTitle className="pr-10">Terminal watchlist</DialogTitle>
          <div className="min-h-0 flex-1"><Watchlist items={watchlist} loading={loading} activeSymbol={selectedSymbol}
            onSymbolSelect={(symbol) => { setSelectedSymbol(symbol); setWatchlistOpen(false); }}
            onAddToWatchlist={addToWatchlist} onRemoveFromWatchlist={removeFromWatchlist} onRefresh={refreshSnapshot} /></div>
        </DialogContent>
      </Dialog>

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
