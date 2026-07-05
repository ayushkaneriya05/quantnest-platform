import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Activity,
  BarChart3,
  Plus,
  Radio,
  RefreshCw,
  RotateCcw,
  Trash2,
  Wallet,
  Terminal,
  TrendingUp,
} from "lucide-react";

import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/shared/components/ui/dialog";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/components/ui/select";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { useWebSocket } from "@/shared/hooks/useWebSocket";
import { paperApi } from "@/shared/services/paperApi";
import { portfolioApi } from "@/shared/services/portfolioApi";
import { strategyApi } from "@/shared/services/strategyApi";
import { customConfirm } from "@/shared/components/ui/custom-dialog";
import { useLivePositionsPnL } from "@/shared/hooks/useLivePositionsPnL";
import { GlobalLoader } from '@/shared/components/ui/global-loader';

export default function PaperTradingDashboard({ selectedAccountId }) {
  const { notify } = useNotifications();
  const { connectionStatus, getTickData, lastMessage } = useWebSocket();
  const refreshTimerRef = React.useRef(null);
  const [accounts, setAccounts] = useState([]);
  const [positions, setPositions] = useState([]);
  const [trades, setTrades] = useState([]);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);
  const [createForm, setCreateForm] = useState({
    strategy_id: "",
    name: "Paper Account",
  });
  const [allocations, setAllocations] = useState([]);
  const [strategies, setStrategies] = useState([]);
  const [deleteDialog, setDeleteDialog] = useState(null);

  const fetchData = async () => {
    try {
      const [
        accountsRes,
        positionsRes,
        tradesRes,
        allocRes,
        stratRes,
      ] = await Promise.all([
        paperApi.getAccounts(),
        paperApi.getPositions(),
        paperApi.getTrades(),
        portfolioApi.getAllocations(),
        strategyApi.getAll(),
      ]);
      setAccounts(accountsRes.data || []);
      setPositions(positionsRes.data || []);
      setTrades(tradesRes.data || []);
      setAllocations(allocRes.data || []);

      let strategiesData = [];
      if (Array.isArray(stratRes.data)) {
        strategiesData = stratRes.data;
      } else if (stratRes.data?.results) {
        strategiesData = stratRes.data.results;
      }
      setStrategies(strategiesData);
    } catch (error) {
      if (loading) notify.error("Failed to load paper account data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const handleOpenCreate = () => setCreateOpen(true);
    window.addEventListener('open-new-paper-account', handleOpenCreate);

    return () => {
      window.removeEventListener('open-new-paper-account', handleOpenCreate);
    };
  }, []);

  useEffect(() => {
    if (!lastMessage) return;
    const msgType = lastMessage.type;
    if (msgType === "order_update" || msgType === "order.update" || msgType === "position_update" || msgType === "position.update") {
      if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
      refreshTimerRef.current = setTimeout(fetchData, 150);
    }
  }, [lastMessage]);

  const selectedAccountData = useMemo(
    () => accounts.find((a) => String(a.id) === String(selectedAccountId)),
    [accounts, selectedAccountId]
  );

  const filteredPositions = useMemo(
    () =>
      positions.filter(
        (p) => String(p.account) === String(selectedAccountId),
      ),
    [positions, selectedAccountId],
  );

  const filteredTrades = useMemo(
    () =>
      trades.filter(
        (t) => String(t.account) === String(selectedAccountId),
      ),
    [trades, selectedAccountId],
  );

  const { livePnLByPositionId } = useLivePositionsPnL(positions);

  const accountStats = useMemo(() => {
    const winners = filteredTrades.filter((t) => Number(t.net_pnl || 0) > 0).length;
    return {
      totalTrades: filteredTrades.length,
      winRate: filteredTrades.length ? (winners / filteredTrades.length) * 100 : 0,
    };
  }, [filteredTrades]);

  const handleReset = async () => {
    if (!selectedAccountData) return;
    const confirmed = await customConfirm(`Reset ${selectedAccountData.name}?`);
    if (!confirmed) return;
    try {
      setBusy(true);
      await paperApi.resetAccount(selectedAccountData.id);
      notify.success("Paper account reset");
      await fetchData();
    } catch (error) {
      notify.error("Failed to reset account");
    } finally {
      setBusy(false);
    }
  };

  const handleConfirmDelete = async () => {
    try {
      setBusy(true);
      await paperApi.deleteAccount(selectedAccountData.id);
      setDeleteDialog(null);
      notify.success("Paper account deleted");
      await fetchData();
    } catch (error) {
      notify.error(error?.response?.data?.error || "Failed to delete account");
    } finally {
      setBusy(false);
    }
  };

  const handleToggleStatus = async (account) => {
    try {
      setBusy(true);
      if (account.is_active) {
        await paperApi.deactivateAccount(account.id);
        notify.success(`${account.name} disabled`);
      } else {
        await paperApi.activateAccount(account.id);
        notify.success(`${account.name} activated`);
      }
      await fetchData();
    } catch (error) {
      notify.error("Failed to update account status");
    } finally {
      setBusy(false);
    }
  };

  const handleCreateAccount = async () => {
    if (!createForm.strategy_id) return notify.error("Select a strategy allocation");
    try {
      setBusy(true);
      await portfolioApi.createPaperAccount(createForm.strategy_id);
      setCreateOpen(false);
      notify.success("Paper account created");
      await fetchData();
    } catch (error) {
      notify.error(error?.response?.data?.error || "Failed to create account");
    } finally {
      setBusy(false);
    }
  };

  const formatCurrency = (value) =>
    new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(Number(value || 0));

  // Summary stats for all accounts
  const globalStats = useMemo(() => {
    let totalBalance = 0;
    let totalPnl = 0;
    let totalMargin = 0;
    
    accounts.forEach(account => {
      const accountPositions = positions.filter(p => String(p.account) === String(account.id));
      const dynamicUnrealizedPnl = accountPositions.reduce((sum, p) => sum + (livePnLByPositionId[p.id]?.pnl || Number(p.unrealized_pnl || 0)), 0);
      
      const serverUnrealizedPnl = Number(account.unrealized_pnl || 0);
      const realizedPnl = Number(account.realized_pnl !== undefined ? account.realized_pnl : (Number(account.total_pnl || 0) - serverUnrealizedPnl));
      const accountLiveTotalPnl = realizedPnl + dynamicUnrealizedPnl;
      
      totalBalance += Number(account.current_balance || 0);
      totalPnl += accountLiveTotalPnl;
      totalMargin += Number(account.margin_available || 0);
    });
    
    return { totalBalance, totalPnl, totalMargin, totalAccounts: accounts.length };
  }, [accounts, positions, livePnLByPositionId]);

  if (loading) return (
    <div className="flex items-center justify-center py-20">
      <GlobalLoader />
    </div>
  );

  // Mode 1: Summary Mode (No selectedAccountId provided)
  if (!selectedAccountId) {
    return (
      <div className="container-padding py-4 sm:py-6 lg:py-8 space-y-8 animate-in fade-in duration-500">

        {/* Global Stats Row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="bg-gray-900/40 border-gray-800 backdrop-blur-sm hover:border-gray-700 transition-colors">
            <CardContent className="p-5 flex items-center gap-4">
              <div className="p-3 bg-indigo-500/10 rounded-2xl">
                <Wallet className="h-6 w-6 text-indigo-400" />
              </div>
              <div>
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Total Equity</p>
                <p className="text-xl font-bold text-white mt-0.5">{formatCurrency(globalStats.totalBalance)}</p>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-gray-900/40 border-gray-800 backdrop-blur-sm hover:border-gray-700 transition-colors">
            <CardContent className="p-5 flex items-center gap-4">
              <div className="p-3 bg-emerald-500/10 rounded-2xl">
                <TrendingUp className="h-6 w-6 text-emerald-400" />
              </div>
              <div>
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Total P&L</p>
                <p className={`text-xl font-bold mt-0.5 ${globalStats.totalPnl >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                  {globalStats.totalPnl >= 0 ? "+" : ""}{formatCurrency(globalStats.totalPnl)}
                </p>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-gray-900/40 border-gray-800 backdrop-blur-sm hover:border-gray-700 transition-colors">
            <CardContent className="p-5 flex items-center gap-4">
              <div className="p-3 bg-sky-500/10 rounded-2xl">
                <Activity className="h-6 w-6 text-sky-400" />
              </div>
              <div>
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Total Accounts</p>
                <p className="text-xl font-bold text-white mt-0.5">{accounts.length}</p>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-gray-900/40 border-gray-800 backdrop-blur-sm hover:border-gray-700 transition-colors">
            <CardContent className="p-5 flex items-center gap-4">
              <div className="p-3 bg-amber-500/10 rounded-2xl">
                <Radio className="h-6 w-6 text-amber-400" />
              </div>
              <div>
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Engine Status</p>
                <div className="flex items-center gap-2 mt-1">
                  <div className={`h-2 w-2 rounded-full ${connectionStatus === "connected" ? "bg-emerald-500 animate-pulse shadow-[0_0_10px_rgba(16,185,129,0.5)]" : "bg-amber-500"}`} />
                  <p className="text-sm font-semibold text-gray-200 capitalize">{connectionStatus}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Accounts List */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
          <h3 className="text-lg font-bold text-white">Active Virtual Accounts</h3>
            <Button size="sm" className="bg-indigo-600 hover:bg-indigo-700" onClick={() => setCreateOpen(true)}>
              <Plus className="h-4 w-4 mr-1" /> New Account
            </Button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {accounts.length === 0 ? (
              <Card className="col-span-full bg-gray-900/20 border-gray-800 border-dashed py-12 text-center">
                <CardHeader>
                  <CardTitle className="text-white text-base">No paper accounts yet</CardTitle>
                  <CardDescription>Allocate capital to a strategy to create your first virtual trading account.</CardDescription>
                </CardHeader>
                <CardContent>
                   <div className="max-w-xs mx-auto space-y-4">
                    <Select
                      value={createForm.strategy_id?.toString() || ""}
                      onValueChange={(val) => setCreateForm({...createForm, strategy_id: val})}
                    >
                      <SelectTrigger className="w-full bg-gray-800 border-gray-700 text-white p-2.5 rounded-lg text-sm h-[42px]">
                        <SelectValue placeholder="Select allocation..." />
                      </SelectTrigger>
                      <SelectContent className="bg-gray-900 border-gray-800 text-white">
                        {allocations.map(a => (
                          <SelectItem key={a.id} value={a.strategy?.toString() || ""} className="focus:bg-gray-800 focus:text-white">
                            {a.strategy_name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Button className="w-full bg-indigo-600 hover:bg-indigo-700" onClick={handleCreateAccount} disabled={busy || !createForm.strategy_id}>
                      Create First Account
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ) : (
              accounts.map((account) => (
                <Card key={account.id} className="bg-gray-900/60 border-gray-800 hover:border-indigo-500/50 transition-all duration-300 group overflow-hidden relative">
                  <div className="absolute top-0 left-0 w-1 h-full bg-indigo-500 opacity-0 group-hover:opacity-100 transition-opacity" />
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-white text-base font-bold">{account.name}</CardTitle>
                      <Badge 
                        onClick={(e) => { e.stopPropagation(); handleToggleStatus(account); }}
                        className={`cursor-pointer transition-all duration-200 hover:scale-105 ${account.is_active ? "bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 border border-emerald-500/30" : "bg-gray-500/10 text-gray-400 hover:bg-gray-500/20 border border-gray-700/50"}`}
                        title={account.is_active ? "Click to Disable" : "Click to Activate"}
                      >
                        {account.is_active ? "Active" : "Disabled"}
                      </Badge>
                    </div>
                    <CardDescription className="text-xs text-gray-500 truncate">Strategy: {account.strategy_name}</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-0.5">
                        <p className="text-[10px] uppercase text-gray-500 font-medium">Balance</p>
                        <p className="text-lg font-bold text-white">{formatCurrency(account.current_balance)}</p>
                      </div>
                      <div className="space-y-0.5 text-right">
                        <p className="text-[10px] uppercase text-gray-500 font-medium">Total P&L</p>
                        {(() => {
                          const accountPositions = positions.filter(p => String(p.account) === String(account.id));
                          const dynamicUnrealizedPnl = accountPositions.reduce((sum, p) => sum + (livePnLByPositionId[p.id]?.pnl || Number(p.unrealized_pnl || 0)), 0);
                          const serverUnrealizedPnl = Number(account.unrealized_pnl || 0);
                          const realizedPnl = Number(account.realized_pnl !== undefined ? account.realized_pnl : (Number(account.total_pnl || 0) - serverUnrealizedPnl));
                          const liveTotalPnl = realizedPnl + dynamicUnrealizedPnl;
                          return (
                            <p className={`text-lg font-bold ${liveTotalPnl >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                              {liveTotalPnl >= 0 ? "+" : ""}{formatCurrency(liveTotalPnl)}
                            </p>
                          );
                        })()}
                      </div>
                    </div>
                    <Link to={`/dashboard/paper/portfolio?account_id=${account.id}`} className="block w-full">
                      <Button variant="outline" className="w-full border-gray-800 hover:bg-indigo-600 hover:text-white transition-all text-xs h-9">
                        View Portfolio <RotateCcw className="h-3 w-3 ml-2" />
                      </Button>
                    </Link>
                  </CardContent>
                </Card>
              ))
            )}
          </div>
        </div>

        {/* Add Account Modal */}
        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
          <DialogContent className="bg-gray-900 border-gray-800 text-white">
            <DialogHeader>
              <DialogTitle>Create Virtual Account</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label>Capital Source</Label>
                <Select
                  value={createForm.strategy_id?.toString() || ""}
                  onValueChange={(val) => setCreateForm({...createForm, strategy_id: val})}
                >
                  <SelectTrigger className="w-full bg-gray-800 border-gray-700 text-white p-2.5 rounded-lg text-sm h-[42px]">
                    <SelectValue placeholder="Select allocation..." />
                  </SelectTrigger>
                  <SelectContent className="bg-gray-900 border-gray-800 text-white">
                    {allocations.map(a => (
                      <SelectItem key={a.id} value={a.strategy?.toString() || ""} className="focus:bg-gray-800 focus:text-white">
                        {a.strategy_name} (₹{Number(a.available_amount).toLocaleString()})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Account Name</Label>
                <Input 
                  value={createForm.name} 
                  onChange={(e) => setCreateForm({...createForm, name: e.target.value})}
                  placeholder="e.g., My Aggressive Account"
                  className="bg-gray-800 border-gray-700"
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="ghost" onClick={() => setCreateOpen(false)}>Cancel</Button>
              <Button onClick={handleCreateAccount} className="bg-indigo-600 hover:bg-indigo-700" disabled={busy}>
                Create Account
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    );
  }

  // Mode 2: Detailed Mode (selectedAccountId provided)
  if (!selectedAccountData) {
    return (
      <Card className="bg-gray-900/50 border-gray-800 py-12 text-center">
        <p className="text-gray-500 italic">Select an account from the dropdown above to view details.</p>
      </Card>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Quick Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="bg-gray-900/50 border-gray-800 hover:border-gray-700 transition-colors">
          <CardContent className="py-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-indigo-500/20 rounded-lg">
                <Wallet className="h-5 w-5 text-indigo-400" />
              </div>
              <div>
                <p className="text-xs text-gray-400">Balance</p>
                <p className="text-lg font-bold text-white">
                  {formatCurrency(selectedAccountData?.current_balance)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gray-900/50 border-gray-800 hover:border-gray-700 transition-colors">
          <CardContent className="py-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-500/20 rounded-lg">
                <BarChart3 className="h-5 w-5 text-green-400" />
              </div>
              <div>
                <p className="text-xs text-gray-400">Total P&L</p>
                {(() => {
                  const accountPositions = filteredPositions;
                  const dynamicUnrealizedPnl = accountPositions.reduce((sum, p) => sum + (livePnLByPositionId[p.id]?.pnl || Number(p.unrealized_pnl || 0)), 0);
                  const serverUnrealizedPnl = Number(selectedAccountData.unrealized_pnl || 0);
                  const realizedPnl = Number(selectedAccountData.realized_pnl !== undefined ? selectedAccountData.realized_pnl : (Number(selectedAccountData.total_pnl || 0) - serverUnrealizedPnl));
                  const liveTotalPnl = realizedPnl + dynamicUnrealizedPnl;
                  return (
                    <p className={`text-lg font-bold ${liveTotalPnl >= 0 ? "text-green-400" : "text-red-400"}`}>
                      {formatCurrency(liveTotalPnl)}
                    </p>
                  );
                })()}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gray-900/50 border-gray-800 hover:border-gray-700 transition-colors">
          <CardContent className="py-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-500/20 rounded-lg">
                <Activity className="h-5 w-5 text-purple-400" />
              </div>
              <div>
                <p className="text-xs text-gray-400">Margin Available</p>
                <p className="text-lg font-bold text-white">
                  {formatCurrency(selectedAccountData?.margin_available)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gray-900/50 border-gray-800 hover:border-gray-700 transition-colors">
          <CardContent className="py-4">
            <div className="flex items-center gap-3 text-sm">
              <div className="p-2 bg-amber-500/20 rounded-lg">
                <RefreshCw className="h-5 w-5 text-amber-400" />
              </div>
              <div>
                <p className="text-xs text-gray-400">Status</p>
                <div className="flex items-center gap-1.5">
                  <div className={`h-1.5 w-1.5 rounded-full ${connectionStatus === "connected" ? "bg-emerald-500 animate-pulse" : "bg-amber-500"}`} />
                  <span className="font-medium text-white capitalize">{connectionStatus}</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2 bg-gray-900/50 border-gray-800">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-white text-base">Active Positions</CardTitle>
            <Link to="#" onClick={(e) => { e.preventDefault(); }} className="text-xs text-indigo-400 hover:text-indigo-300">View All</Link>
          </CardHeader>
          <CardContent className="space-y-3">
            {filteredPositions.length === 0 ? (
              <div className="py-8 text-center text-gray-500 text-sm italic">
                No active positions for this account.
              </div>
            ) : (
              filteredPositions.slice(0, 5).map((position) => {
                const liveTick = getTickData(position.instrument_symbol);
                return (
                  <div key={position.id} className="rounded-xl bg-gray-800/30 p-4 border border-gray-800/50 hover:border-gray-700 transition-all">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-lg ${position.side === "BUY" ? "bg-emerald-500/10" : "bg-rose-500/10"}`}>
                           <Activity className={`h-4 w-4 ${position.side === "BUY" ? "text-emerald-400" : "text-rose-400"}`} />
                        </div>
                        <div>
                          <div className="text-white font-semibold flex items-center gap-2">
                            {position.instrument_symbol}
                            <Badge variant="outline" className="text-[10px] py-0 h-4 border-gray-700 text-gray-400">{position.quantity} Qty</Badge>
                          </div>
                          <div className="text-[10px] text-gray-500 mt-0.5">
                            Avg: {formatCurrency(position.avg_price)}
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-white font-medium text-sm">
                          {formatCurrency(livePnLByPositionId[position.id]?.livePrice || position.current_price)}
                        </div>
                        <div className={`text-xs font-bold ${(livePnLByPositionId[position.id]?.pnl || Number(position.unrealized_pnl || 0)) >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                          {(livePnLByPositionId[position.id]?.pnl || Number(position.unrealized_pnl || 0)) >= 0 ? "+" : ""}{formatCurrency(livePnLByPositionId[position.id]?.pnl || position.unrealized_pnl)}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </CardContent>
        </Card>

        <Card className="bg-gray-900/50 border-gray-800">
          <CardHeader>
            <CardTitle className="text-white text-base">Performance Metrics</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {[
              { label: "Total Trades", value: accountStats.totalTrades, icon: Terminal, color: "sky" },
              { label: "Win Rate", value: `${accountStats.winRate.toFixed(1)}%`, icon: BarChart3, color: "emerald" },
              { label: "Today's Trades", value: selectedAccountData?.today_trades || 0, icon: Activity, color: "amber" },
              { label: "Daily P&L", value: formatCurrency(selectedAccountData?.today_pnl || 0), icon: Wallet, color: "indigo", pnl: true },
            ].map((stat, i) => {
              const Icon = stat.icon;
              return (
                <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-gray-800/20">
                  <div className="flex items-center gap-3">
                    <Icon className={`h-4 w-4 text-${stat.color}-400`} />
                    <span className="text-sm text-gray-400">{stat.label}</span>
                  </div>
                  <span className={`text-sm font-semibold ${stat.pnl ? (Number(selectedAccountData?.today_pnl || 0) >= 0 ? "text-emerald-400" : "text-rose-400") : "text-white"}`}>
                    {stat.value}
                  </span>
                </div>
              );
            })}
            
            <div className="pt-4 grid grid-cols-2 gap-2">
              <Button variant="outline" size="sm" className="border-gray-700 text-gray-300 h-9" onClick={handleReset} disabled={busy}>
                <RotateCcw className="h-3.5 w-3.5 mr-2" /> Reset
              </Button>
              <Button variant="outline" size="sm" className="border-rose-900/50 text-rose-400 hover:bg-rose-500/10 h-9" onClick={() => setDeleteDialog({ can_delete: true })} disabled={busy}>
                <Trash2 className="h-3.5 w-3.5 mr-2" /> Delete
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="bg-gray-900/50 border-gray-800">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-white text-base">Recent Executions</CardTitle>
          <Button variant="ghost" size="sm" className="text-xs text-indigo-400 hover:text-indigo-300">View History</Button>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="text-xs text-gray-500 uppercase border-b border-gray-800">
                <tr>
                  <th className="px-4 py-3 font-medium">Instrument</th>
                  <th className="px-4 py-3 font-medium">Side</th>
                  <th className="px-4 py-3 font-medium">Quantity</th>
                  <th className="px-4 py-3 font-medium text-right">Net P&L</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/50">
                {filteredTrades.length === 0 ? (
                  <tr>
                    <td colSpan="4" className="px-4 py-8 text-center text-gray-500 italic">No trade history yet.</td>
                  </tr>
                ) : (
                  filteredTrades.slice(0, 5).map((trade) => (
                    <tr key={trade.id} className="hover:bg-gray-800/20 transition-colors">
                      <td className="px-4 py-3 font-medium text-white">{trade.instrument_symbol}</td>
                      <td className="px-4 py-3">
                        <Badge className={trade.side === "BUY" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" : "bg-rose-500/10 text-rose-400 border-rose-500/20"}>
                          {trade.side}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-gray-300">{trade.quantity}</td>
                      <td className={`px-4 py-3 text-right font-bold ${Number(trade.net_pnl || 0) >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                        {Number(trade.net_pnl || 0) >= 0 ? "+" : ""}{formatCurrency(trade.net_pnl)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Account Deletion Dialog */}
      <Dialog open={!!deleteDialog} onOpenChange={() => setDeleteDialog(null)}>
        <DialogContent className="bg-gray-900 border-gray-800 text-white sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-rose-400">Delete Paper Account</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <p className="text-sm text-gray-300">
              Are you sure you want to delete <strong>{selectedAccountData?.name}</strong>? All virtual history for this account will be permanently lost.
            </p>
          </div>
          <DialogFooter className="gap-2">
            <Button variant="outline" className="border-gray-700" onClick={() => setDeleteDialog(null)}>Cancel</Button>
            <Button variant="destructive" onClick={handleConfirmDelete} disabled={busy}>Confirm Delete</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
