import React, { useState, useCallback } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { TrendingUp, Briefcase, User, ArrowUp, ArrowDown } from "lucide-react";

import ChartView from "@/components/dashboard/trading/ChartView";
import Watchlist from "@/components/dashboard/trading/Watchlist";
import PortfolioDisplay from "@/components/dashboard/trading/PortfolioDisplay";
import AccountSummary from "@/components/dashboard/trading/AccountSummary";
import OrderModal from "@/components/dashboard/trading/OrderModal";

export default function PaperTrading() {
  const [selectedSymbol, setSelectedSymbol] = useState("RELIANCE");
  const [isOrderModalOpen, setIsOrderModalOpen] = useState(false);
  const [transactionType, setTransactionType] = useState("BUY");
  const [portfolioKey, setPortfolioKey] = useState(0);
  const [watchlistWidth, setWatchlistWidth] = useState(320);

  const handleOpenOrderModal = (type) => {
    setTransactionType(type);
    setIsOrderModalOpen(true);
  };

  const handleCloseOrderModal = () => {
    setIsOrderModalOpen(false);
  };

  const handleOrderPlaced = useCallback(() => {
    handleCloseOrderModal();
    setPortfolioKey((prevKey) => prevKey + 1);
  }, []);

  const handleMouseDown = (e) => {
    e.preventDefault();
    const startX = e.clientX;
    const startWidth = watchlistWidth;

    const handleMouseMove = (e) => {
      const newWidth = Math.max(
        250,
        Math.min(500, startWidth + (e.clientX - startX))
      );
      setWatchlistWidth(newWidth);
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
    <div className="h-full bg-[#0d1117] text-white flex flex-col">
      <Tabs defaultValue="trading" className="h-full flex flex-col">
        {/* Full Width Tabbar Fixed at Top */}
        <div className="flex-shrink-0 border-b border-gray-800/50 bg-[#161b22] z-10">
          <div className="w-full px-3 sm:px-4 lg:px-6 py-3">
            <TabsList className="w-full bg-[#21262d] border border-gray-700/50 rounded-lg p-1 h-10 sm:h-12">
              <div className="grid grid-cols-3 gap-1 w-full">
                <TabsTrigger
                  value="trading"
                  className="data-[state=active]:bg-gray-600 data-[state=active]:text-white bg-transparent text-gray-400 hover:text-gray-200 hover:bg-gray-800/50 border-0 rounded-md px-2 sm:px-4 py-2 font-medium transition-all duration-200 w-full text-xs sm:text-sm"
                >
                  <TrendingUp className="h-3 w-3 sm:h-4 sm:w-4 mr-1 sm:mr-2" />
                  <span className="hidden sm:inline">Trading</span>
                  <span className="sm:hidden">Trade</span>
                </TabsTrigger>
                <TabsTrigger
                  value="portfolio"
                  className="data-[state=active]:bg-gray-600 data-[state=active]:text-white bg-transparent text-gray-400 hover:text-gray-200 hover:bg-gray-800/50 border-0 rounded-md px-2 sm:px-4 py-2 font-medium transition-all duration-200 w-full text-xs sm:text-sm"
                >
                  <Briefcase className="h-3 w-3 sm:h-4 sm:w-4 mr-1 sm:mr-2" />
                  <span className="hidden sm:inline">Portfolio</span>
                  <span className="sm:hidden">Port.</span>
                </TabsTrigger>
                <TabsTrigger
                  value="account"
                  className="data-[state=active]:bg-gray-600 data-[state=active]:text-white bg-transparent text-gray-400 hover:text-gray-200 hover:bg-gray-800/50 border-0 rounded-md px-2 sm:px-4 py-2 font-medium transition-all duration-200 w-full text-xs sm:text-sm"
                >
                  <User className="h-3 w-3 sm:h-4 sm:w-4 mr-1 sm:mr-2" />
                  <span className="hidden sm:inline">Account</span>
                  <span className="sm:hidden">Acc.</span>
                </TabsTrigger>
              </div>
            </TabsList>
          </div>
        </div>

        {/* Main Content Area with Scrollbars */}
        <div className="flex-1 min-h-0 overflow-auto scrollbar-theme">
          <TabsContent value="trading" className="h-full m-0 p-0">
            <div className="min-h-full flex flex-col lg:flex-row">
              {/* Resizable Watchlist - Hidden on mobile, sidebar on larger screens */}
              <div className="hidden lg:block">
                <div
                  className="flex-shrink-0 border-r border-gray-800/50 bg-[#0d1117] relative h-full"
                  style={{ width: `${watchlistWidth}px` }}
                >
                  <Watchlist onSymbolSelect={setSelectedSymbol} />

                  {/* Resize Handle */}
                  <div
                    className="absolute top-0 right-0 w-1 h-full bg-transparent hover:bg-gray-600 cursor-col-resize group z-10"
                    onMouseDown={handleMouseDown}
                  >
                    <div className="w-full h-full group-hover:bg-gray-600 transition-colors duration-200" />
                  </div>
                </div>
              </div>

              {/* Main Trading Area */}
              <div className="flex-1 flex flex-col min-w-0 min-h-0">
                {/* Chart Area with Scrollbar Support */}
                <div className="flex-1 bg-[#0d1117] min-h-0 overflow-auto scrollbar-theme">
                  <div className="h-full min-h-[400px] lg:min-h-[600px]">
                    <ChartView
                      symbol={selectedSymbol}
                      onBuyClick={() => handleOpenOrderModal("BUY")}
                      onSellClick={() => handleOpenOrderModal("SELL")}
                    />
                  </div>
                </div>

                {/* Mobile Watchlist - Show on small screens */}
                <div className="lg:hidden border-t border-gray-800/50 bg-[#0d1117] h-48 sm:h-64 overflow-auto scrollbar-thin-theme">
                  <Watchlist onSymbolSelect={setSelectedSymbol} />
                </div>
              </div>
            </div>
          </TabsContent>

          <TabsContent
            value="portfolio"
            className="h-full m-0 p-0 bg-[#0d1117]"
          >
            <div className="h-full w-full overflow-y-auto scrollbar-theme">
              <div className="p-3 sm:p-4 lg:p-6 max-w-7xl mx-auto min-h-full">
                <PortfolioDisplay key={portfolioKey} />
              </div>
            </div>
          </TabsContent>

          <TabsContent value="account" className="h-full m-0 p-0 bg-[#0d1117]">
            <div className="h-full w-full overflow-y-auto scrollbar-theme">
              <div className="p-3 sm:p-4 lg:p-6 max-w-7xl mx-auto min-h-full">
                <AccountSummary />
              </div>
            </div>
          </TabsContent>
        </div>
      </Tabs>

      <OrderModal
        isOpen={isOrderModalOpen}
        onClose={handleCloseOrderModal}
        symbol={selectedSymbol}
        transactionType={transactionType}
        onOrderPlaced={handleOrderPlaced}
      />
    </div>
  );
}
