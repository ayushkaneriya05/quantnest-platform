import React, { useState, useCallback } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { TrendingUp, Briefcase, User } from "lucide-react";

import ChartView from "@/components/dashboard/trading/ChartView";
import Watchlist from "@/components/dashboard/trading/Watchlist";
import PortfolioDisplay from "@/components/dashboard/trading/PortfolioDisplay";
import AccountSummary from "@/components/dashboard/trading/AccountSummary";
import OrderModal from "@/components/dashboard/trading/OrderModal";

export default function PaperTrading() {
  // State to manage the currently selected symbol for trading
  const [selectedSymbol, setSelectedSymbol] = useState("RELIANCE");

  // State for the order modal
  const [isOrderModalOpen, setIsOrderModalOpen] = useState(false);
  const [transactionType, setTransactionType] = useState("BUY");

  // A key to force-refresh portfolio data after an order is placed
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
    // Increment the key to trigger a re-fetch in the PortfolioDisplay component
    setPortfolioKey((prevKey) => prevKey + 1);
  }, []);

  return (
    <div className="container-padding py-6 lg:py-8 h-full flex flex-col">
      <Tabs defaultValue="trading" className="flex flex-col h-full">
        <TabsList className="grid w-full grid-cols-3 max-w-xl mx-auto bg-gray-900 border border-gray-800">
          <TabsTrigger value="trading" className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4" /> Trading
          </TabsTrigger>
          <TabsTrigger value="portfolio" className="flex items-center gap-2">
            <Briefcase className="h-4 w-4" /> Portfolio
          </TabsTrigger>
          <TabsTrigger value="account" className="flex items-center gap-2">
            <User className="h-4 w-4" /> Account
          </TabsTrigger>
        </TabsList>

        <div className="flex-grow mt-6">
          <TabsContent value="trading" className="h-full">
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 h-full">
              <div className="lg:col-span-3 flex flex-col gap-4">
                <ChartView symbol={selectedSymbol} />
                <div className="flex gap-4">
                  <Button
                    onClick={() => handleOpenOrderModal("BUY")}
                    className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-lg py-6"
                  >
                    Buy
                  </Button>
                  <Button
                    onClick={() => handleOpenOrderModal("SELL")}
                    className="flex-1 bg-red-600 hover:bg-red-700 text-lg py-6"
                  >
                    Sell
                  </Button>
                </div>
              </div>
              <div className="lg:col-span-1">
                <Watchlist onSymbolSelect={setSelectedSymbol} />
              </div>
            </div>
          </TabsContent>

          <TabsContent value="portfolio">
            <PortfolioDisplay key={portfolioKey} />
          </TabsContent>

          <TabsContent value="account">
            <AccountSummary />
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
