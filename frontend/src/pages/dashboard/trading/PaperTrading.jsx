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
    <div className="h-screen bg-[#0d1117] text-white flex flex-col overflow-hidden">
      {/* Top Navigation */}
      <div className="flex-shrink-0 border-b border-gray-800/50 bg-[#161b22]">
        <Tabs defaultValue="trading" className="w-full">
          <div className="px-4 py-2">
            <TabsList className="bg-transparent border-0 p-0 gap-1">
              <TabsTrigger 
                value="trading" 
                className="data-[state=active]:bg-[#0969da] data-[state=active]:text-white bg-transparent text-gray-400 hover:text-gray-200 hover:bg-gray-800/50 border-0 rounded-md px-4 py-2"
              >
                <TrendingUp className="h-4 w-4 mr-2" />
                Trading
              </TabsTrigger>
              <TabsTrigger 
                value="portfolio" 
                className="data-[state=active]:bg-[#0969da] data-[state=active]:text-white bg-transparent text-gray-400 hover:text-gray-200 hover:bg-gray-800/50 border-0 rounded-md px-4 py-2"
              >
                <Briefcase className="h-4 w-4 mr-2" />
                Portfolio
              </TabsTrigger>
              <TabsTrigger 
                value="account" 
                className="data-[state=active]:bg-[#0969da] data-[state=active]:text-white bg-transparent text-gray-400 hover:text-gray-200 hover:bg-gray-800/50 border-0 rounded-md px-4 py-2"
              >
                <User className="h-4 w-4 mr-2" />
                Account
              </TabsTrigger>
            </TabsList>
          </div>

          {/* Main Content Area */}
          <div className="h-[calc(100vh-60px)]">
            <TabsContent value="trading" className="h-full m-0 p-0">
              <div className="flex h-full">
                {/* Left Sidebar - Watchlist */}
                <div className="w-80 border-r border-gray-800/50 bg-[#0d1117] flex-shrink-0">
                  <Watchlist onSymbolSelect={setSelectedSymbol} />
                </div>

                {/* Main Trading Area */}
                <div className="flex-1 flex flex-col">
                  {/* Symbol Header */}
                  <div className="flex-shrink-0 px-6 py-4 border-b border-gray-800/50 bg-[#161b22]">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <h1 className="text-2xl font-bold text-white">
                          {selectedSymbol}
                        </h1>
                        <div className="text-2xl font-mono text-white">
                          ₹2,458.50
                        </div>
                        <div className="flex items-center text-sm text-emerald-400">
                          <ArrowUp className="h-4 w-4 mr-1" />
                          +24.50 (+1.01%)
                        </div>
                      </div>
                      
                      {/* Quick Trade Buttons */}
                      <div className="flex gap-3">
                        <Button
                          onClick={() => handleOpenOrderModal("BUY")}
                          className="bg-emerald-600 hover:bg-emerald-700 text-white px-6 py-2 font-semibold"
                        >
                          Buy
                        </Button>
                        <Button
                          onClick={() => handleOpenOrderModal("SELL")}
                          className="bg-red-600 hover:bg-red-700 text-white px-6 py-2 font-semibold"
                        >
                          Sell
                        </Button>
                      </div>
                    </div>
                  </div>

                  {/* Chart Area */}
                  <div className="flex-1 bg-[#0d1117]">
                    <ChartView symbol={selectedSymbol} />
                  </div>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="portfolio" className="h-full m-0 p-6 bg-[#0d1117] overflow-auto">
              <PortfolioDisplay key={portfolioKey} />
            </TabsContent>

            <TabsContent value="account" className="h-full m-0 p-6 bg-[#0d1117] overflow-auto">
              <AccountSummary />
            </TabsContent>
          </div>
        </Tabs>
      </div>

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
