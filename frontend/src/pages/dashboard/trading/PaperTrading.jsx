import React, { useState, useCallback } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { 
  TrendingUp, 
  Briefcase, 
  User,
  ArrowUp,
  ArrowDown
} from "lucide-react";

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
    const startX = e.clientX;
    const startWidth = watchlistWidth;

    const handleMouseMove = (e) => {
      const newWidth = Math.max(250, Math.min(500, startWidth + (e.clientX - startX)));
      setWatchlistWidth(newWidth);
    };

    const handleMouseUp = () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  };

  return (
    <div className="h-screen bg-[#0d1117] text-white flex flex-col overflow-hidden">
      <Tabs defaultValue="trading" className="h-full flex flex-col">
        {/* Full Width Tabbar Fixed at Top */}
        <div className="flex-shrink-0 border-b border-gray-800/50 bg-[#161b22] sticky top-0 z-10">
          <div className="w-full px-6 py-3">
            <TabsList className="w-full bg-[#21262d] border border-gray-700/50 rounded-lg p-1 h-12">
              <div className="grid grid-cols-3 gap-1 w-full">
                <TabsTrigger 
                  value="trading" 
                  className="data-[state=active]:bg-gray-600 data-[state=active]:text-white bg-transparent text-gray-400 hover:text-gray-200 hover:bg-gray-800/50 border-0 rounded-md px-4 py-2 font-medium transition-all duration-200 w-full"
                >
                  <TrendingUp className="h-4 w-4 mr-2" />
                  Trading
                </TabsTrigger>
                <TabsTrigger 
                  value="portfolio" 
                  className="data-[state=active]:bg-gray-600 data-[state=active]:text-white bg-transparent text-gray-400 hover:text-gray-200 hover:bg-gray-800/50 border-0 rounded-md px-4 py-2 font-medium transition-all duration-200 w-full"
                >
                  <Briefcase className="h-4 w-4 mr-2" />
                  Portfolio
                </TabsTrigger>
                <TabsTrigger 
                  value="account" 
                  className="data-[state=active]:bg-gray-600 data-[state=active]:text-white bg-transparent text-gray-400 hover:text-gray-200 hover:bg-gray-800/50 border-0 rounded-md px-4 py-2 font-medium transition-all duration-200 w-full"
                >
                  <User className="h-4 w-4 mr-2" />
                  Account
                </TabsTrigger>
              </div>
            </TabsList>
          </div>
        </div>

        {/* Main Content Area - No Page Scrolling */}
        <div className="flex-1 overflow-hidden">
          <TabsContent value="trading" className="h-full m-0 p-0">
            <div className="h-full flex">
              {/* Resizable Watchlist */}
              <div 
                className="flex-shrink-0 border-r border-gray-800/50 bg-[#0d1117] relative"
                style={{ width: `${watchlistWidth}px` }}
              >
                <Watchlist onSymbolSelect={setSelectedSymbol} />
                
                {/* Resize Handle */}
                <div
                  className="absolute top-0 right-0 w-1 h-full bg-transparent hover:bg-gray-600 cursor-col-resize group"
                  onMouseDown={handleMouseDown}
                >
                  <div className="w-full h-full group-hover:bg-gray-600 transition-colors duration-200" />
                </div>
              </div>

              {/* Main Trading Area */}
              <div className="flex-1 flex flex-col min-w-0">
                {/* Symbol Header */}
                <div className="flex-shrink-0 px-4 lg:px-6 py-4 border-b border-gray-800/50 bg-[#161b22]">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4 min-w-0">
                      <h1 className="text-xl lg:text-2xl font-bold text-white truncate">
                        {selectedSymbol}
                      </h1>
                      <div className="text-lg lg:text-2xl font-mono text-white">
                        ₹2,458.50
                      </div>
                      <div className="flex items-center text-sm text-emerald-400">
                        <ArrowUp className="h-4 w-4 mr-1" />
                        +24.50 (+1.01%)
                      </div>
                    </div>
                    
                    {/* Quick Trade Buttons */}
                    <div className="flex gap-2 lg:gap-3 flex-shrink-0">
                      <Button
                        onClick={() => handleOpenOrderModal("BUY")}
                        className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 lg:px-6 py-2 font-semibold transition-all duration-200 shadow-lg hover:shadow-emerald-500/25"
                      >
                        Buy
                      </Button>
                      <Button
                        onClick={() => handleOpenOrderModal("SELL")}
                        className="bg-red-600 hover:bg-red-700 text-white px-4 lg:px-6 py-2 font-semibold transition-all duration-200 shadow-lg hover:shadow-red-500/25"
                      >
                        Sell
                      </Button>
                    </div>
                  </div>
                </div>

                {/* Chart Area */}
                <div className="flex-1 bg-[#0d1117] overflow-hidden">
                  <ChartView symbol={selectedSymbol} />
                </div>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="portfolio" className="h-full m-0 p-0 bg-[#0d1117]">
            <div className="h-full w-full overflow-y-auto scrollbar-thin scrollbar-track-gray-800 scrollbar-thumb-gray-600">
              <div className="p-6">
                <PortfolioDisplay key={portfolioKey} />
              </div>
            </div>
          </TabsContent>

          <TabsContent value="account" className="h-full m-0 p-0 bg-[#0d1117]">
            <div className="h-full w-full overflow-y-auto scrollbar-thin scrollbar-track-gray-800 scrollbar-thumb-gray-600">
              <div className="p-6">
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
