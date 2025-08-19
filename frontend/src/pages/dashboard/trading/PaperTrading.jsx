import React, { useState, useCallback } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { 
  TrendingUp, 
  Briefcase, 
  User, 
  Play, 
  DollarSign,
  BarChart3,
  Activity,
  Target,
  Zap
} from "lucide-react";

import ChartView from "@/components/dashboard/trading/ChartView";
import Watchlist from "@/components/dashboard/trading/Watchlist";
import PortfolioDisplay from "@/components/dashboard/trading/PortfolioDisplay";
import AccountSummary from "@/components/dashboard/trading/AccountSummary";
import OrderModal from "@/components/dashboard/trading/OrderModal";

const QuickStatCard = ({ icon: Icon, title, value, change, changeType }) => (
  <Card className="bg-gradient-to-br from-gray-900/80 to-gray-800/50 border-gray-700/50 hover:border-gray-600/50 transition-all duration-300 hover:shadow-lg hover:shadow-cyan-500/10">
    <CardContent className="p-4">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-gradient-to-br from-cyan-500/20 to-blue-500/20">
          <Icon className="h-5 w-5 text-cyan-400" />
        </div>
        <div className="flex-1">
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">{title}</p>
          <p className="text-lg font-bold text-slate-100">{value}</p>
          {change && (
            <p className={`text-xs font-medium ${
              changeType === 'positive' ? 'text-emerald-400' : 'text-red-400'
            }`}>
              {change}
            </p>
          )}
        </div>
      </div>
    </CardContent>
  </Card>
);

const ActionButton = ({ onClick, type, icon: Icon, label, className = "" }) => (
  <Button
    onClick={onClick}
    className={`
      flex-1 relative group overflow-hidden
      transition-all duration-300 transform hover:scale-105
      py-6 text-lg font-semibold
      shadow-lg hover:shadow-xl
      ${type === 'buy' 
        ? 'bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-500 hover:to-emerald-400 shadow-emerald-500/25' 
        : 'bg-gradient-to-r from-red-600 to-red-500 hover:from-red-500 hover:to-red-400 shadow-red-500/25'
      }
      ${className}
    `}
  >
    <div className="absolute inset-0 bg-gradient-to-r from-white/0 via-white/10 to-white/0 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700" />
    <div className="relative flex items-center gap-3">
      <Icon className="h-5 w-5" />
      {label}
    </div>
  </Button>
);

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
    <div className="container-padding py-6 lg:py-8 h-full flex flex-col">
      {/* Header Section */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 rounded-lg bg-gradient-to-br from-cyan-500/20 to-blue-500/20">
            <Play className="h-6 w-6 text-cyan-400" />
          </div>
          <div>
            <h1 className="text-2xl lg:text-3xl font-bold text-slate-100">
              Paper Trading
            </h1>
            <p className="text-slate-400 text-sm">
              Practice trading with virtual money • No real money at risk
            </p>
          </div>
        </div>
        
        {/* Quick Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
          <QuickStatCard
            icon={DollarSign}
            title="Portfolio Value"
            value="₹1,25,000"
            change="+2.34%"
            changeType="positive"
          />
          <QuickStatCard
            icon={BarChart3}
            title="Day's P&L"
            value="₹2,450"
            change="+1.96%"
            changeType="positive"
          />
          <QuickStatCard
            icon={Activity}
            title="Active Positions"
            value="5"
          />
          <QuickStatCard
            icon={Target}
            title="Success Rate"
            value="68%"
            change="+5% this week"
            changeType="positive"
          />
        </div>
      </div>

      <Tabs defaultValue="trading" className="flex flex-col h-full">
        <TabsList className="grid w-full grid-cols-3 max-w-2xl mx-auto bg-gradient-to-r from-gray-900 to-gray-800 border border-gray-700/50 shadow-lg">
          <TabsTrigger 
            value="trading" 
            className="flex items-center gap-2 data-[state=active]:bg-gradient-to-r data-[state=active]:from-cyan-500/20 data-[state=active]:to-blue-500/20 data-[state=active]:text-cyan-300 transition-all duration-300"
          >
            <TrendingUp className="h-4 w-4" /> Trading
          </TabsTrigger>
          <TabsTrigger 
            value="portfolio" 
            className="flex items-center gap-2 data-[state=active]:bg-gradient-to-r data-[state=active]:from-cyan-500/20 data-[state=active]:to-blue-500/20 data-[state=active]:text-cyan-300 transition-all duration-300"
          >
            <Briefcase className="h-4 w-4" /> Portfolio
          </TabsTrigger>
          <TabsTrigger 
            value="account" 
            className="flex items-center gap-2 data-[state=active]:bg-gradient-to-r data-[state=active]:from-cyan-500/20 data-[state=active]:to-blue-500/20 data-[state=active]:text-cyan-300 transition-all duration-300"
          >
            <User className="h-4 w-4" /> Account
          </TabsTrigger>
        </TabsList>

        <div className="flex-grow mt-8">
          <TabsContent value="trading" className="h-full">
            <div className="grid grid-cols-1 xl:grid-cols-4 gap-6 h-full">
              <div className="xl:col-span-3 flex flex-col gap-6">
                {/* Selected Symbol Header */}
                <Card className="bg-gradient-to-r from-gray-900/80 to-gray-800/50 border-gray-700/50">
                  <CardContent className="p-6">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className="p-3 rounded-xl bg-gradient-to-br from-cyan-500/20 to-blue-500/20">
                          <Zap className="h-6 w-6 text-cyan-400" />
                        </div>
                        <div>
                          <h2 className="text-2xl font-bold text-slate-100">{selectedSymbol}</h2>
                          <p className="text-slate-400">Reliance Industries Ltd.</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-2xl font-bold text-slate-100">₹2,458.50</p>
                        <p className="text-emerald-400 text-sm font-medium">+24.50 (+1.01%)</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Chart Section */}
                <Card className="bg-gradient-to-br from-gray-900/80 to-gray-800/50 border-gray-700/50 flex-1">
                  <CardContent className="p-6 h-full">
                    <ChartView symbol={selectedSymbol} />
                  </CardContent>
                </Card>

                {/* Trading Actions */}
                <div className="flex gap-4">
                  <ActionButton
                    onClick={() => handleOpenOrderModal("BUY")}
                    type="buy"
                    icon={TrendingUp}
                    label="Buy Order"
                  />
                  <ActionButton
                    onClick={() => handleOpenOrderModal("SELL")}
                    type="sell"
                    icon={TrendingUp}
                    label="Sell Order"
                    className="rotate-180"
                  />
                </div>
              </div>

              {/* Sidebar */}
              <div className="xl:col-span-1">
                <Watchlist onSymbolSelect={setSelectedSymbol} />
              </div>
            </div>
          </TabsContent>

          <TabsContent value="portfolio" className="h-full">
            <Card className="bg-gradient-to-br from-gray-900/80 to-gray-800/50 border-gray-700/50 h-full">
              <CardContent className="p-6 h-full">
                <PortfolioDisplay key={portfolioKey} />
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="account" className="h-full">
            <Card className="bg-gradient-to-br from-gray-900/80 to-gray-800/50 border-gray-700/50 h-full">
              <CardContent className="p-6 h-full">
                <AccountSummary />
              </CardContent>
            </Card>
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
