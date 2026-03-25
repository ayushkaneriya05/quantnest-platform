/**
 * Portfolio Allocations - capital allocation to strategies
 */
import { useState, useEffect, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import { Badge } from "@/shared/components/ui/badge";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/components/ui/select";
import { Slider } from "@/shared/components/ui/slider";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter
} from "@/shared/components/ui/dialog";
import { 
  Plus, Trash2, Edit, PieChart, Save, RefreshCw
} from 'lucide-react';
import { Switch } from "@/shared/components/ui/switch";
import { portfolioApi } from '@/shared/services/portfolioApi';
import { strategyApi } from '@/shared/services/strategyApi';
import { useNotifications } from '@/shared/hooks/useNotifications';
import { useSetPageActions } from '@/shared/hooks/useSetPageActions';

const INITIAL_FORM = {
  strategy: '', allocation_type: 'FIXED', allocated_amount: 0, allocated_percentage: 10,
  auto_rebalance: false, rebalance_frequency: 'WEEKLY', is_active: true
};

export default function PortfolioAllocations() {
  const { notify } = useNotifications();
  const [portfolio, setPortfolio] = useState(null);
  const [allocations, setAllocations] = useState([]);
  const [strategies, setStrategies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState(INITIAL_FORM);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [portfolioData, allocData, stratData] = await Promise.all([
        portfolioApi.getMyPortfolio(),
        portfolioApi.getAllocations(),
        strategyApi.getAll()
      ]);
      setPortfolio(portfolioData.data);
      const allocArr = allocData.data;
      setAllocations(Array.isArray(allocArr) ? allocArr : (allocArr?.results || []));
      const stratArr = Array.isArray(stratData) ? stratData : (stratData?.results || []);
      setStrategies(stratArr);
    } catch (error) {
      notify.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  // Set page actions in header
  const pageActions = useMemo(() => (
    <Button 
      onClick={() => openAddModal()}
      className="bg-indigo-600 hover:bg-indigo-700"
      size="sm"
    >
      <Plus className="h-4 w-4 mr-1" />
      Add Allocation
    </Button>
  ), []);

  useSetPageActions(pageActions);

  const openAddModal = () => {
    setEditingId(null);
    setForm(INITIAL_FORM);
    setModalOpen(true);
  };

  const openEditModal = (alloc) => {
    setEditingId(alloc.id);
    setForm({
      strategy: String(alloc.strategy || ''),
      allocation_type: alloc.allocation_type,
      allocated_amount: parseFloat(alloc.allocated_amount || 0),
      allocated_percentage: parseFloat(alloc.allocated_percentage || 10),
      auto_rebalance: alloc.auto_rebalance || false,
      rebalance_frequency: alloc.rebalance_frequency || 'WEEKLY',
      is_active: alloc.is_active !== false,
    });
    setModalOpen(true);
  };

  const closeModal = () => {
    setModalOpen(false);
    setEditingId(null);
    setForm(INITIAL_FORM);
  };

  // Compute effective allocated amount based on type
  const getEffectiveAmount = (alloc) => {
    if (alloc.allocation_type === 'PERCENTAGE') {
      return (parseFloat(alloc.allocated_percentage || 0) / 100) * parseFloat(portfolio?.current_capital || 0);
    }
    return parseFloat(alloc.allocated_amount || 0);
  };

  const formatCurrency = (val) => {
    return new Intl.NumberFormat('en-IN', { 
      style: 'currency', currency: 'INR', maximumFractionDigits: 0 
    }).format(val || 0);
  };

  const handleSave = async () => {
    const capital = parseFloat(portfolio?.current_capital || 0);

    // Compute this allocation's effective amount
    let thisAmount;
    if (form.allocation_type === 'FIXED') {
      thisAmount = parseFloat(form.allocated_amount || 0);
    } else {
      thisAmount = (parseFloat(form.allocated_percentage || 0) / 100) * capital;
    }

    // Compute already-allocated total (exclude current item if editing)
    const otherAllocations = editingId
      ? allocations.filter(a => a.id !== editingId)
      : allocations;
    const alreadyAllocated = otherAllocations.reduce((sum, a) => sum + getEffectiveAmount(a), 0);
    const remaining = capital - alreadyAllocated;
    const remainingPct = capital > 0 ? ((remaining / capital) * 100).toFixed(1) : 0;

    if (alreadyAllocated + thisAmount > capital) {
      notify.error(
        `Exceeds available capital. Max remaining: ${formatCurrency(remaining)} (${remainingPct}% of capital)`
      );
      return;
    }

    // Validate percentage total doesn't exceed 100%
    if (form.allocation_type === 'PERCENTAGE') {
      const otherPct = otherAllocations
        .filter(a => a.allocation_type === 'PERCENTAGE')
        .reduce((s, a) => s + parseFloat(a.allocated_percentage || 0), 0);
      const thisPct = parseFloat(form.allocated_percentage || 0);
      if (otherPct + thisPct > 100) {
        notify.error(
          `Total percentage cannot exceed 100%. Already used: ${otherPct}%, remaining: ${(100 - otherPct).toFixed(1)}%`
        );
        return;
      }
    }

    try {
      const data = {
        portfolio: portfolio.id,
        strategy: form.strategy,
        allocation_type: form.allocation_type,
        allocated_amount: form.allocation_type === 'FIXED' ? form.allocated_amount : 0,
        allocated_percentage: form.allocation_type === 'PERCENTAGE' ? form.allocated_percentage : 0,
        auto_rebalance: form.auto_rebalance,
        rebalance_frequency: form.rebalance_frequency,
        is_active: form.is_active,
      };

      if (editingId) {
        const response = await portfolioApi.updateAllocation(editingId, data);
        setAllocations(allocations.map(a => a.id === editingId ? response.data : a));
        notify.success('Allocation updated');
      } else {
        const response = await portfolioApi.createAllocation(data);
        setAllocations([...allocations, response.data]);
        notify.success('Allocation added');
      }

      closeModal();
    } catch (error) {
      const msg = error?.response?.data;
      notify.error(typeof msg === 'object' ? JSON.stringify(msg) : 'Failed to save allocation');
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Remove this allocation?')) return;
    try {
      await portfolioApi.deleteAllocation(id);
      setAllocations(allocations.filter(a => a.id !== id));
      notify.success('Allocation removed');
    } catch (error) {
      notify.error('Failed to remove');
    }
  };

  const totalAllocated = allocations.reduce((sum, a) => sum + getEffectiveAmount(a), 0);
  const unallocated = parseFloat(portfolio?.current_capital || 0) - totalAllocated;

  // Strategy options: when adding, exclude already-allocated. When editing, include the current one.
  const strategyOptions = strategies.filter(s => {
    if (editingId) {
      const editAlloc = allocations.find(a => a.id === editingId);
      if (editAlloc && String(editAlloc.strategy) === String(s.id)) return true;
    }
    return !allocations.some(a => String(a.strategy) === String(s.id));
  });

  if (loading) {
    return (
      <div className="flex justify-center items-center h-96">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500" />
      </div>
    );
  }

  return (
    <div className="container-padding py-6 lg:py-8 space-y-6">
      {/* Summary */}
      <div className="grid grid-cols-3 gap-4">
        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-4 text-center">
            <p className="text-2xl font-bold text-white">{formatCurrency(portfolio?.current_capital)}</p>
            <p className="text-xs text-gray-400">Total Capital</p>
          </CardContent>
        </Card>
        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-4 text-center">
            <p className="text-2xl font-bold text-indigo-400">{formatCurrency(totalAllocated)}</p>
            <p className="text-xs text-gray-400">Allocated</p>
          </CardContent>
        </Card>
        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-4 text-center">
            <p className={`text-2xl font-bold ${unallocated >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {formatCurrency(unallocated)}
            </p>
            <p className="text-xs text-gray-400">Unallocated</p>
          </CardContent>
        </Card>
      </div>

      {/* Allocations List */}
      {allocations.length === 0 ? (
        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-12 text-center">
            <PieChart className="h-12 w-12 text-gray-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-300">No allocations</h3>
            <p className="text-gray-500">Add capital allocations to your strategies</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid md:grid-cols-2 gap-4">
          {allocations.map((alloc) => (
            <Card key={alloc.id} className="bg-gray-900/50 border-gray-800">
              <CardContent className="py-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div>
                      <h4 className="text-white font-medium">{alloc.strategy_name}</h4>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge variant="outline" className="text-xs border-gray-700">
                          {alloc.allocation_type}
                        </Badge>
                        <Badge className={`text-[10px] ${alloc.is_active ? 'bg-emerald-600/20 text-emerald-400' : 'bg-gray-600/20 text-gray-400'}`}>
                          {alloc.is_active ? 'Active' : 'Paused'}
                        </Badge>
                        {alloc.auto_rebalance && (
                          <Badge className="text-[10px] bg-blue-600/20 text-blue-400">
                            <RefreshCw className="h-2.5 w-2.5 mr-1" />{alloc.rebalance_frequency}
                          </Badge>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex gap-1">
                    <Button
                      variant="ghost" size="sm"
                      onClick={() => openEditModal(alloc)}
                      className="text-gray-400 hover:text-indigo-400"
                    >
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost" size="sm"
                      onClick={() => handleDelete(alloc.id)}
                      className="text-gray-400 hover:text-red-400"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 text-sm">
                  <div>
                    <p className="text-gray-500">Allocated</p>
                    <p className="text-white font-medium">
                      {formatCurrency(getEffectiveAmount(alloc))}
                      {alloc.allocation_type === 'PERCENTAGE' && (
                        <span className="text-gray-500 text-xs ml-1">({alloc.allocated_percentage}%)</span>
                      )}
                    </p>
                  </div>
                  <div>
                    <p className="text-gray-500">Utilized</p>
                    <p className="text-indigo-400 font-medium">{formatCurrency(alloc.utilized_amount)}</p>
                  </div>
                  <div>
                    <p className="text-gray-500">Available</p>
                    <p className="text-cyan-400 font-medium">{formatCurrency(alloc.available_amount)}</p>
                  </div>
                  <div>
                    <p className="text-gray-500">Total P&L</p>
                    <p className={`font-medium ${parseFloat(alloc.total_pnl) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {parseFloat(alloc.total_pnl) >= 0 ? '+' : ''}{formatCurrency(alloc.total_pnl)}
                    </p>
                  </div>
                  <div>
                    <p className="text-gray-500">Today P&L</p>
                    <p className={`font-medium ${parseFloat(alloc.today_pnl) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {parseFloat(alloc.today_pnl) >= 0 ? '+' : ''}{formatCurrency(alloc.today_pnl)}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Add / Edit Modal */}
      <Dialog open={modalOpen} onOpenChange={(open) => { if (!open) closeModal(); }}>
        <DialogContent className="bg-gray-900 border-gray-800 text-white sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{editingId ? 'Edit Allocation' : 'New Allocation'}</DialogTitle>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label className="text-gray-400">Strategy</Label>
              <Select 
                value={form.strategy} 
                onValueChange={(v) => setForm({ ...form, strategy: v })}
              >
                <SelectTrigger className="bg-gray-800 border-gray-700">
                  <SelectValue placeholder="Select strategy" />
                </SelectTrigger>
                <SelectContent>
                  {strategyOptions.map(s => (
                    <SelectItem key={s.id} value={String(s.id)}>{s.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label className="text-gray-400">Type</Label>
              <Select 
                value={form.allocation_type} 
                onValueChange={(v) => setForm({ ...form, allocation_type: v })}
              >
                <SelectTrigger className="bg-gray-800 border-gray-700">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="FIXED">Fixed Amount</SelectItem>
                  <SelectItem value="PERCENTAGE">Percentage</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            {form.allocation_type === 'FIXED' ? (
              <div className="space-y-2">
                <Label className="text-gray-400">Amount (₹)</Label>
                <Input
                  type="number"
                  value={form.allocated_amount}
                  onChange={(e) => setForm({ ...form, allocated_amount: parseFloat(e.target.value) || 0 })}
                  className="bg-gray-800 border-gray-700 text-white"
                />
              </div>
            ) : (
              <div className="space-y-2">
                <div className="flex justify-between">
                  <Label className="text-gray-400">Percentage</Label>
                  <span className="text-white text-sm">{form.allocated_percentage}%</span>
                </div>
                <Slider
                  value={[form.allocated_percentage]}
                  onValueChange={(v) => setForm({ ...form, allocated_percentage: v[0] })}
                  max={100}
                  step={1}
                />
                <p className="text-xs text-gray-500">
                  ≈ {formatCurrency((form.allocated_percentage / 100) * parseFloat(portfolio?.current_capital || 0))}
                </p>
              </div>
            )}

            {/* Auto-Rebalance */}
            <div className="flex items-center justify-between">
              <Label className="text-gray-400">Auto Rebalance</Label>
              <Switch
                checked={form.auto_rebalance}
                onCheckedChange={(v) => setForm({ ...form, auto_rebalance: v })}
              />
            </div>

            {form.auto_rebalance && (
              <div className="space-y-2">
                <Label className="text-gray-400">Rebalance Frequency</Label>
                <Select
                  value={form.rebalance_frequency}
                  onValueChange={(v) => setForm({ ...form, rebalance_frequency: v })}
                >
                  <SelectTrigger className="bg-gray-800 border-gray-700">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="DAILY">Daily</SelectItem>
                    <SelectItem value="WEEKLY">Weekly</SelectItem>
                    <SelectItem value="MONTHLY">Monthly</SelectItem>
                    <SelectItem value="QUARTERLY">Quarterly</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}

            {/* Active Toggle */}
            <div className="flex items-center justify-between">
              <Label className="text-gray-400">Active</Label>
              <Switch
                checked={form.is_active}
                onCheckedChange={(v) => setForm({ ...form, is_active: v })}
              />
            </div>
          </div>

          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={closeModal} className="border-gray-700">
              Cancel
            </Button>
            <Button onClick={handleSave} className="bg-indigo-600 hover:bg-indigo-700">
              <Save className="h-4 w-4 mr-1" />
              {editingId ? 'Update' : 'Save'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
