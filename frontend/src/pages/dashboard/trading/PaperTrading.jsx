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

  return (
    <div className="h-full bg-[#0d1117] text-white flex flex-col overflow-hidden">
      <Tabs defaultValue="trading" className="h-full flex flex-col">
        {/* Fixed Tabbar at Top */}
        <div className="flex-shrink-0 border-b border-gray-800/50 bg-[#161b22] sticky top-0 z-10">
          <div className="container mx-auto px-4 py-3">
            <TabsList className="grid w-full max-w-md mx-auto grid-cols-3 bg-[#21262d] border border-gray-700/50 rounded-lg p-1">
              <TabsTrigger 
                value="trading" 
                className="data-[state=active]:bg-gray-600 data-[state=active]:text-white bg-transparent text-gray-400 hover:text-gray-200 hover:bg-gray-800/50 border-0 rounded-md px-4 py-2 font-medium transition-all duration-200"
              >
                <TrendingUp className="h-4 w-4 mr-2" />
                Trading
              </TabsTrigger>
              <TabsTrigger 
                value="portfolio" 
                className="data-[state=active]:bg-gray-600 data-[state=active]:text-white bg-transparent text-gray-400 hover:text-gray-200 hover:bg-gray-800/50 border-0 rounded-md px-4 py-2 font-medium transition-all duration-200"
              >
                <Briefcase className="h-4 w-4 mr-2" />
                Portfolio
              </TabsTrigger>
              <TabsTrigger 
                value="account" 
                className="data-[state=active]:bg-gray-600 data-[state=active]:text-white bg-transparent text-gray-400 hover:text-gray-200 hover:bg-gray-800/50 border-0 rounded-md px-4 py-2 font-medium transition-all duration-200"
              >
                <User className="h-4 w-4 mr-2" />
                Account
              </TabsTrigger>
            </TabsList>
          </div>
        </div>

        {/* Main Content Area - Full Height */}
        <div className="flex-1 overflow-hidden">
          <TabsContent value="trading" className="h-full m-0 p-0">
            <div className="h-full flex">
              {/* Left Sidebar - Watchlist */}
              <div className="w-80 flex-shrink-0 border-r border-gray-800/50 bg-[#0d1117]">
                <Watchlist onSymbolSelect={setSelectedSymbol} />
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
            <div className="h-full w-full">
              <div className="h-full overflow-y-auto scrollbar-thin scrollbar-track-gray-800 scrollbar-thumb-gray-600 p-4 lg:p-6">
                <div className="max-w-7xl mx-auto">
                  <PortfolioDisplay key={portfolioKey} />
                </div>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="account" className="h-full m-0 p-0 bg-[#0d1117]">
            <div className="h-full w-full">
              <div className="h-full overflow-y-auto scrollbar-thin scrollbar-track-gray-800 scrollbar-thumb-gray-600 p-4 lg:p-6">
                <div className="max-w-7xl mx-auto">
                  <AccountSummary />
                </div>
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
