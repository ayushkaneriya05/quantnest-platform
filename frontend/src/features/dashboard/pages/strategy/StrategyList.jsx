/**
 * Strategy List Page - displays all user strategies with CRUD actions
 */
import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Card, CardContent, CardDescription, CardHeader, CardTitle 
} from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import { Badge } from "@/shared/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/shared/components/ui/dialog";
import { Label } from "@/shared/components/ui/label";
import { Input } from "@/shared/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select";
import { 
  Plus, Play, Pause, Archive, Copy, 
  TrendingUp, Clock, Zap, Target, Edit, Trash2, TestTube,
  Loader2, Sparkles, RotateCcw, FlaskConical, Rocket
} from 'lucide-react';
import { strategyApi } from '@/shared/services/strategyApi';
import { brokersApi } from '@/shared/services/brokersApi';
import { useNotifications } from '@/shared/hooks/useNotifications';
import { useSetPageActions } from '@/shared/hooks/useSetPageActions';
import { customConfirm } from '@/shared/components/ui/custom-dialog';
import { GlobalLoader } from '@/shared/components/ui/global-loader';

const STATUS_CONFIG = {
  DRAFT: { label: 'Draft', className: 'bg-gray-500/15 text-gray-400 border-gray-500/30' },
  ACTIVE: { label: 'Active', className: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30' },
  PAUSED: { label: 'Paused', className: 'bg-amber-500/15 text-amber-400 border-amber-500/30' },
  ARCHIVED: { label: 'Archived', className: 'bg-rose-500/15 text-rose-400 border-rose-500/30' },
};

const STRATEGY_TYPE_ICONS = {
  INTRADAY: Clock,
  POSITIONAL: TrendingUp,
  SWING: Target,
  SCALPING: Zap,
};

const TYPE_COLORS = {
  INTRADAY: 'text-blue-400 bg-blue-500/10',
  POSITIONAL: 'text-emerald-400 bg-emerald-500/10',
  SWING: 'text-amber-400 bg-amber-500/10',
  SCALPING: 'text-purple-400 bg-purple-500/10',
};

export default function StrategyList() {
  const navigate = useNavigate();
  const { notify } = useNotifications();
  const [strategies, setStrategies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [deployingId, setDeployingId] = useState(null);
  const [liveDeployOpen, setLiveDeployOpen] = useState(false);
  const [liveDeployStrategy, setLiveDeployStrategy] = useState(null);
  const [brokerOptions, setBrokerOptions] = useState([]);
  const [selectedBroker, setSelectedBroker] = useState("");
  const [allocationMode, setAllocationMode] = useState("FIXED");
  const [allocationAmount, setAllocationAmount] = useState("");
  const [allocationPercentage, setAllocationPercentage] = useState("");

  const fetchStrategies = async () => {
    try {
      setLoading(true);
      const data = await strategyApi.getAll();
      setStrategies(Array.isArray(data) ? data : (data?.results || []));
    } catch (error) {
      notify.error("Failed to load strategies");
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStrategies();
  }, []);

  const handleCreate = () => {
    navigate("/dashboard/strategy/create");
  };

  // Set page actions in header
  const pageActions = useMemo(() => (
    <Button onClick={handleCreate} className="bg-indigo-600 hover:bg-indigo-500 text-white" size="sm">
      <Plus className="h-4 w-4 mr-2" />
      New Strategy
    </Button>
  ), []);

  useSetPageActions(pageActions);

  const handleEdit = (id) => {
    navigate(`/dashboard/strategy/${id}/edit`);
  };

  const handleBacktest = (id) => {
    navigate(`/dashboard/backtest/setup?strategy=${id}`);
  };

  const loadBrokerOptions = async () => {
    const catalog = await brokersApi.getCatalog();
    const rows = Array.isArray(catalog.data) ? catalog.data : [];
    const connected = rows.filter((item) => item.enabled && item.is_verified);
    setBrokerOptions(connected);
    const active = connected.find((item) => item.is_active) || connected[0];
    setSelectedBroker(active?.credential_id ? String(active.credential_id) : "");
    return connected;
  };

  const handleDeployPaper = async (strategy) => {
    try {
      setDeployingId(strategy.id);
      const result = await strategyApi.deployPaper(strategy.id);
      notify.success(result.message || 'Strategy deployed to paper trading');
      await fetchStrategies();
      navigate('/dashboard/paper');
    } catch (error) {
      notify.error(error?.response?.data?.error || 'Failed to deploy to paper trading');
    } finally {
      setDeployingId(null);
    }
  };

  const openLiveDeploy = async (strategy) => {
    try {
      setDeployingId(strategy.id);
      const brokers = await loadBrokerOptions();
      if (!brokers.length) {
        notify.error('Connect and verify a broker account before deploying live');
        return;
      }
      setLiveDeployStrategy(strategy);
      setAllocationMode("FIXED");
      setAllocationAmount("");
      setAllocationPercentage("");
      setLiveDeployOpen(true);
    } catch (error) {
      notify.error('Failed to load connected broker accounts');
    } finally {
      setDeployingId(null);
    }
  };

  const handleConfirmLiveDeploy = async () => {
    if (!liveDeployStrategy) return;
    try {
      setDeployingId(liveDeployStrategy.id);
      const result = await strategyApi.deployLive(
        liveDeployStrategy.id,
        {
          brokerCredential: selectedBroker ? Number(selectedBroker) : null,
          allocationAmount: allocationMode === "FIXED" && allocationAmount ? Number(allocationAmount) : null,
          allocationPercentage: allocationMode === "PERCENTAGE" && allocationPercentage ? Number(allocationPercentage) : null,
        },
      );
      notify.success(result.message || 'Strategy deployed to live trading');
      setLiveDeployOpen(false);
      setLiveDeployStrategy(null);
      await fetchStrategies();
      navigate('/dashboard/live/strategies');
    } catch (error) {
      notify.error(error?.response?.data?.error || 'Failed to deploy to live trading');
    } finally {
      setDeployingId(null);
    }
  };

  const handleClone = async (id) => {
    try {
      await strategyApi.clone(id);
      notify.success('Strategy cloned successfully');
      fetchStrategies();
    } catch (error) {
      notify.error('Failed to clone strategy');
    }
  };

  const handleActivate = async (id) => {
    try {
      await strategyApi.activate(id);
      notify.success('Strategy activated');
      fetchStrategies();
    } catch (error) {
      notify.error('Failed to activate strategy');
    }
  };

  const handleArchive = async (id) => {
    try {
      await strategyApi.archive(id);
      notify.success('Strategy archived');
      fetchStrategies();
    } catch (error) {
      notify.error('Failed to archive strategy');
    }
  };

  const handlePause = async (id) => {
    try {
      await strategyApi.pause(id);
      notify.success('Strategy paused');
      fetchStrategies();
    } catch (error) {
      notify.error('Failed to pause strategy');
    }
  };

  const handleUnarchive = async (id) => {
    try {
      await strategyApi.unarchive(id);
      notify.success('Strategy unarchived');
      fetchStrategies();
    } catch (error) {
      notify.error('Failed to unarchive strategy');
    }
  };

  const handleDelete = async (id) => {
    const confirmed = await customConfirm('Are you sure you want to delete this strategy? This cannot be undone.');
    if (!confirmed) return;
    try {
      await strategyApi.delete(id);
      notify.success('Strategy deleted');
      fetchStrategies();
    } catch (error) {
      notify.error('Failed to delete strategy');
    }
  };

  const filteredStrategies = strategies.filter(s => {
    if (filter === 'all') return true;
    return s.status.toLowerCase() === filter;
  });

  const filterCounts = {
    all: strategies.length,
    draft: strategies.filter(s => s.status === 'DRAFT').length,
    active: strategies.filter(s => s.status === 'ACTIVE').length,
    paused: strategies.filter(s => s.status === 'PAUSED').length,
    archived: strategies.filter(s => s.status === 'ARCHIVED').length,
  };

  return (
    <div className="container-padding py-6 lg:py-8 space-y-6">
      {/* Filters */}
      <div className="flex gap-2 flex-wrap">
        {['all', 'draft', 'active', 'paused', 'archived'].map((f) => (
          <Button
            key={f}
            variant={filter === f ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilter(f)}
            className={filter === f 
              ? 'bg-indigo-600 hover:bg-indigo-500 text-white' 
              : 'border-gray-700 text-gray-400 hover:text-white hover:border-gray-600 bg-transparent'
            }
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
            {filterCounts[f] > 0 && (
              <span className={`ml-1.5 text-xs ${filter === f ? 'text-indigo-200' : 'text-gray-500'}`}>
                {filterCounts[f]}
              </span>
            )}
          </Button>
        ))}
      </div>

      {/* Strategy Grid */}
      {loading ? (
        <div className="flex flex-col justify-center items-center py-16 gap-3">
          <GlobalLoader />
          <p className="text-sm text-gray-400">Loading strategies...</p>
        </div>
      ) : filteredStrategies.length === 0 ? (
        <Card className="bg-gray-900/40 border-gray-800/80">
          <CardContent className="py-16 text-center">
            <div className="p-4 rounded-2xl bg-indigo-500/10 w-fit mx-auto mb-4">
              <Sparkles className="h-10 w-10 text-indigo-400" />
            </div>
            <h3 className="text-lg font-semibold text-white mb-1">
              {filter === 'all' ? 'No strategies yet' : `No ${filter} strategies`}
            </h3>
            <p className="text-gray-400 text-sm max-w-sm mx-auto">
              {filter === 'all' 
                ? 'Create your first algorithmic trading strategy to get started. Define entry rules, exit conditions, and risk parameters.'
                : `You don't have any ${filter} strategies. Try changing the filter.`}
            </p>
            {filter === 'all' && (
              <Button onClick={handleCreate} className="mt-6 bg-indigo-600 hover:bg-indigo-500 text-white">
                <Plus className="h-4 w-4 mr-2" />
                Create Your First Strategy
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredStrategies.map((strategy) => {
            const TypeIcon = STRATEGY_TYPE_ICONS[strategy.strategy_type] || TrendingUp;
            const typeColor = TYPE_COLORS[strategy.strategy_type] || 'text-gray-400 bg-gray-500/10';
            const statusConfig = STATUS_CONFIG[strategy.status] || STATUS_CONFIG.DRAFT;
            
            return (
              <Card 
                key={strategy.id} 
                className="bg-gray-900/40 border-gray-800/80 hover:border-gray-700 hover:bg-gray-900/60 transition-all duration-200 cursor-pointer group"
                onClick={() => handleEdit(strategy.id)}
              >
                <CardHeader className="pb-3">
                  <div className="flex justify-between items-start">
                    <div className="flex items-center gap-3 min-w-0">
                      <div className={`p-2 rounded-lg shrink-0 ${typeColor}`}>
                        <TypeIcon className="h-5 w-5" />
                      </div>
                      <div className="min-w-0">
                        <CardTitle className="text-white text-base truncate group-hover:text-indigo-300 transition-colors">
                          {strategy.name}
                        </CardTitle>
                        <CardDescription className="text-xs text-gray-500">
                          {strategy.market_type} • {strategy.exchange}
                        </CardDescription>
                      </div>
                    </div>
                    <Badge variant="outline" className={`${statusConfig.className} text-xs shrink-0 ml-2`}>
                      {statusConfig.label}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="pt-0">
                  <p className="text-sm text-gray-400 line-clamp-2 mb-4 min-h-[2.5rem]">
                    {strategy.description || 'No description added'}
                  </p>
                  
                  {/* Tags */}
                  {strategy.tags?.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-4">
                      {strategy.tags.slice(0, 3).map(tag => (
                        <Badge key={tag.id} variant="outline" className="text-xs border-gray-700/80 text-gray-400 bg-gray-800/30">
                          {tag.name}
                        </Badge>
                      ))}
                      {strategy.tags.length > 3 && (
                        <Badge variant="outline" className="text-xs border-gray-700/80 text-gray-500">
                          +{strategy.tags.length - 3}
                        </Badge>
                      )}
                    </div>
                  )}
                  
                  {/* Actions */}
                  <div className="flex gap-1 pt-3 border-t border-gray-800/80" onClick={e => e.stopPropagation()}>
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      onClick={() => handleEdit(strategy.id)}
                      className="text-gray-500 hover:text-white hover:bg-gray-800/60 h-8 w-8 p-0"
                      title="Edit strategy"
                    >
                      <Edit className="h-3.5 w-3.5" />
                    </Button>
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      onClick={() => handleClone(strategy.id)}
                      className="text-gray-500 hover:text-white hover:bg-gray-800/60 h-8 w-8 p-0"
                      title="Clone strategy"
                    >
                      <Copy className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleBacktest(strategy.id)}
                      className="text-gray-500 hover:text-indigo-400 hover:bg-indigo-500/10 h-8 w-8 p-0"
                      title="Backtest strategy"
                    >
                      <TestTube className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDeployPaper(strategy)}
                      className="text-gray-500 hover:text-cyan-400 hover:bg-cyan-500/10 h-8 w-8 p-0"
                      title="Deploy to paper trading"
                      disabled={deployingId === strategy.id}
                    >
                      {deployingId === strategy.id ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <FlaskConical className="h-3.5 w-3.5" />
                      )}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => openLiveDeploy(strategy)}
                      className="text-gray-500 hover:text-emerald-400 hover:bg-emerald-500/10 h-8 w-8 p-0"
                      title="Deploy to connected broker"
                      disabled={deployingId === strategy.id}
                    >
                      <Rocket className="h-3.5 w-3.5" />
                    </Button>
                    {strategy.status === 'DRAFT' && (
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        onClick={() => handleActivate(strategy.id)}
                        className="text-gray-500 hover:text-emerald-400 hover:bg-emerald-500/10 h-8 w-8 p-0"
                        title="Activate strategy"
                      >
                        <Play className="h-3.5 w-3.5" />
                      </Button>
                    )}
                    {strategy.status === 'ACTIVE' && (
                      <>
                        <Button 
                          variant="ghost" 
                          size="sm" 
                          onClick={() => handlePause(strategy.id)}
                          className="text-gray-500 hover:text-amber-400 hover:bg-amber-500/10 h-8 w-8 p-0"
                          title="Pause strategy"
                        >
                          <Pause className="h-3.5 w-3.5" />
                        </Button>
                        <Button 
                          variant="ghost" 
                          size="sm" 
                          onClick={() => handleArchive(strategy.id)}
                          className="text-gray-500 hover:text-gray-400 hover:bg-gray-800/60 h-8 w-8 p-0"
                          title="Archive strategy"
                        >
                          <Archive className="h-3.5 w-3.5" />
                        </Button>
                      </>
                    )}
                    {strategy.status === 'PAUSED' && (
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        onClick={() => handleActivate(strategy.id)}
                        className="text-gray-500 hover:text-emerald-400 hover:bg-emerald-500/10 h-8 w-8 p-0"
                        title="Resume strategy"
                      >
                        <Play className="h-3.5 w-3.5" />
                      </Button>
                    )}
                    {strategy.status === 'ARCHIVED' && (
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        onClick={() => handleUnarchive(strategy.id)}
                        className="text-gray-500 hover:text-blue-400 hover:bg-blue-500/10 h-8 w-8 p-0"
                        title="Unarchive strategy"
                      >
                        <RotateCcw className="h-3.5 w-3.5" />
                      </Button>
                    )}
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      onClick={() => handleDelete(strategy.id)}
                      className="text-gray-500 hover:text-rose-400 hover:bg-rose-500/10 h-8 w-8 p-0 ml-auto"
                      title="Delete strategy"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      <Dialog open={liveDeployOpen} onOpenChange={setLiveDeployOpen}>
        <DialogContent className="bg-gray-950 border-gray-800 text-white">
          <DialogHeader>
            <DialogTitle>Deploy Strategy Live</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="text-sm text-gray-400">
              {liveDeployStrategy
                ? `Choose the connected broker account for ${liveDeployStrategy.name}.`
                : "Choose a broker account."}
            </div>
            <div className="space-y-2">
              <Label className="text-gray-300">Connected Broker</Label>
              <Select value={selectedBroker} onValueChange={setSelectedBroker}>
                <SelectTrigger className="bg-gray-900 border-gray-700 text-white">
                  <SelectValue placeholder="Select broker account" />
                </SelectTrigger>
                <SelectContent className="bg-gray-900 border-gray-800 text-white">
                  {brokerOptions.map((broker) => (
                    <SelectItem key={broker.credential_id} value={String(broker.credential_id)}>
                      {broker.display_name} - {broker.account_name || broker.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="text-gray-300">Allocation Mode</Label>
                <Select value={allocationMode} onValueChange={setAllocationMode}>
                  <SelectTrigger className="bg-gray-900 border-gray-700 text-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-gray-900 border-gray-800 text-white">
                    <SelectItem value="FIXED">Fixed Capital</SelectItem>
                    <SelectItem value="PERCENTAGE">Percentage of Broker Equity</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label className="text-gray-300">
                  {allocationMode === "FIXED" ? "Allocated Capital (Rs)" : "Allocated Percentage (%)"}
                </Label>
                <Input
                  type="number"
                  min="0"
                  step={allocationMode === "FIXED" ? "1" : "0.5"}
                  value={allocationMode === "FIXED" ? allocationAmount : allocationPercentage}
                  onChange={(e) => {
                    if (allocationMode === "FIXED") {
                      setAllocationAmount(e.target.value);
                    } else {
                      setAllocationPercentage(e.target.value);
                    }
                  }}
                  className="bg-gray-900 border-gray-700 text-white"
                  placeholder={allocationMode === "FIXED" ? "50000" : "10"}
                />
              </div>
            </div>
            <p className="text-xs text-gray-500">
              This live allocation acts as the strategy wallet on the broker account. New entries are blocked once the strategy wallet or broker margin is exhausted.
            </p>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              className="border-gray-700 text-gray-100"
              onClick={() => setLiveDeployOpen(false)}
            >
              Cancel
            </Button>
            <Button
              className="bg-emerald-600 hover:bg-emerald-500"
              onClick={handleConfirmLiveDeploy}
              disabled={
                !selectedBroker
                || deployingId === liveDeployStrategy?.id
                || (allocationMode === "FIXED" && !allocationAmount)
                || (allocationMode === "PERCENTAGE" && !allocationPercentage)
              }
            >
              {deployingId === liveDeployStrategy?.id ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Rocket className="h-4 w-4 mr-2" />
              )}
              Deploy Live
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
