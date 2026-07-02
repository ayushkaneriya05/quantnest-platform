import React, { useState, useEffect, useMemo } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import { Badge } from "@/shared/components/ui/badge";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select";
import { Slider } from "@/shared/components/ui/slider";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/shared/components/ui/dialog";
import { Plus, Trash2, Edit, PieChart, Save, RefreshCw } from "lucide-react";
import { Switch } from "@/shared/components/ui/switch";
import { portfolioApi } from "@/shared/services/portfolioApi";
import { strategyApi } from "@/shared/services/strategyApi";
import { useNotifications } from "@/shared/hooks/useNotifications";

const INITIAL_FORM = {
  strategy: "",
  allocation_type: "FIXED",
  allocated_amount: 0,
  allocated_percentage: 10,
  auto_rebalance: false,
  rebalance_frequency: "WEEKLY",
  is_active: true,
};

export default function PaperAllocations() {
  const { notify } = useNotifications();
  const [portfolio, setPortfolio] = useState(null);
  const [allocations, setAllocations] = useState([]);
  const [strategies, setStrategies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState(INITIAL_FORM);
  const [deleteDialog, setDeleteDialog] = useState(null);
  const [deletingId, setDeletingId] = useState(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [portfolioData, allocData, stratData] = await Promise.all([
        portfolioApi.getMyPortfolio(),
        portfolioApi.getAllocations(),
        strategyApi.getAll(),
      ]);
      setPortfolio(portfolioData.data);
      
      const allocArr = allocData.data;
      const allAllocations = Array.isArray(allocArr) ? allocArr : allocArr?.results || [];
      
      // If selectedAccountId is provided, we might want to filter or highlight.
      // But typically allocations are global to the vault.
      setAllocations(allAllocations);
      
      const stratArr = Array.isArray(stratData)
        ? stratData
        : stratData?.results || [];
      setStrategies(stratArr);
    } catch (error) {
      notify.error("Failed to load allocation data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    
    const handleOpenAdd = () => openAddModal();
    window.addEventListener('open-new-allocation', handleOpenAdd);

    return () => {
      window.removeEventListener('open-new-allocation', handleOpenAdd);
    };
  }, []);

  const openAddModal = () => {
    setEditingId(null);
    setForm(INITIAL_FORM);
    setModalOpen(true);
  };

  const openEditModal = (alloc) => {
    setEditingId(alloc.id);
    setForm({
      strategy: String(alloc.strategy || ""),
      allocation_type: alloc.allocation_type,
      allocated_amount: parseFloat(alloc.allocated_amount || 0),
      allocated_percentage: parseFloat(alloc.allocated_percentage || 10),
      auto_rebalance: alloc.auto_rebalance || false,
      rebalance_frequency: alloc.rebalance_frequency || "WEEKLY",
      is_active: alloc.is_active !== false,
    });
    setModalOpen(true);
  };

  const closeModal = () => {
    setModalOpen(false);
    setEditingId(null);
    setForm(INITIAL_FORM);
  };

  const getEffectiveAmount = (alloc) => {
    if (alloc.allocation_type === "PERCENTAGE") {
      const portfolioEquity = parseFloat(
        portfolio?.total_value || portfolio?.current_capital || 0,
      );
      return (
        (parseFloat(alloc.allocated_percentage || 0) / 100) * portfolioEquity
      );
    }
    return parseFloat(alloc.allocated_amount || 0);
  };

  const formatCurrency = (val) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(val || 0);
  };

  const handleSave = async () => {
    const portfolioEquity = parseFloat(
      portfolio?.total_value || portfolio?.current_capital || 0,
    );

    let thisAmount;
    if (form.allocation_type === "FIXED") {
      thisAmount = parseFloat(form.allocated_amount || 0);
    } else {
      thisAmount = (parseFloat(form.allocated_percentage || 0) / 100) * portfolioEquity;
    }

    const otherAllocations = editingId
      ? allocations.filter((a) => a.id !== editingId)
      : allocations;
    const alreadyAllocated = otherAllocations.reduce(
      (sum, a) => sum + getEffectiveAmount(a),
      0,
    );

    if (alreadyAllocated + thisAmount > portfolioEquity) {
      notify.error(`Exceeds available capital. Max remaining: ${formatCurrency(portfolioEquity - alreadyAllocated)}`);
      return;
    }

    try {
      const data = {
        portfolio: portfolio.id,
        strategy: form.strategy,
        allocation_type: form.allocation_type,
        allocated_amount: form.allocation_type === "FIXED" ? parseFloat(form.allocated_amount) : 0,
        allocated_percentage: form.allocation_type === "PERCENTAGE" ? parseFloat(form.allocated_percentage) : 0,
        auto_rebalance: form.auto_rebalance,
        rebalance_frequency: form.rebalance_frequency,
        is_active: form.is_active,
      };

      if (editingId) {
        await portfolioApi.updateAllocation(editingId, data);
        notify.success("Allocation updated");
      } else {
        await portfolioApi.createAllocation(data);
        notify.success("Allocation added");
      }
      fetchData();
      closeModal();
    } catch (error) {
      notify.error(error?.response?.data?.error || "Failed to save allocation");
    }
  };

  const handleDelete = async (id) => {
    setDeletingId(id);
    try {
      const response = await portfolioApi.deleteAllocation(id);
      if (response.data.status === "has_paper_account") {
        setDeleteDialog({
          allocationId: id,
          paperAccount: response.data.paper_account,
          canDeletePaperAccount: response.data.can_delete_paper_account,
          deleteReason: response.data.delete_reason,
        });
      } else {
        notify.success("Allocation removed");
        fetchData();
      }
    } catch (error) {
      notify.error("Failed to remove allocation");
    } finally {
      setDeletingId(null);
    }
  };

  const handleConfirmDelete = async (deletePaperAccount) => {
    try {
      await portfolioApi.confirmDeleteAllocation(
        deleteDialog.allocationId,
        deletePaperAccount,
      );
      setDeleteDialog(null);
      notify.success("Allocation deleted");
      fetchData();
    } catch (error) {
      notify.error("Deletion failed");
    }
  };

  if (loading) return null;

  return (
    <div className="space-y-6 animate-in fade-in duration-300">

      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {allocations.map((alloc) => (
          <Card key={alloc.id} className="bg-gray-900/50 border-gray-800 hover:border-gray-700 transition-colors">
            <CardContent className="pt-6">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h4 className="text-white font-semibold text-base">{alloc.strategy_name}</h4>
                  <Badge variant="outline" className="mt-1 text-[10px] border-gray-800 text-gray-500">
                    {alloc.allocation_type}
                  </Badge>
                </div>
                <div className="flex gap-1">
                  <Button variant="ghost" size="icon" className="h-8 w-8 text-gray-500 hover:text-white" onClick={() => openEditModal(alloc)}>
                    <Edit className="h-4 w-4" />
                  </Button>
                  <Button variant="ghost" size="icon" className="h-8 w-8 text-gray-500 hover:text-red-400" onClick={() => handleDelete(alloc.id)}>
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              
              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Allocated</span>
                  <span className="text-white font-medium">{formatCurrency(getEffectiveAmount(alloc))}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Live P&L</span>
                  <span className={parseFloat(alloc.total_pnl) >= 0 ? "text-emerald-400" : "text-rose-400"}>
                    {formatCurrency(alloc.total_pnl)}
                  </span>
                </div>
                <div className="pt-2 border-t border-gray-800 flex justify-between items-center">
                  <Badge className={alloc.is_active ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" : "bg-gray-500/10 text-gray-400"}>
                    {alloc.is_active ? "Trading Active" : "Paused"}
                  </Badge>
                  {alloc.auto_rebalance && (
                    <span className="text-[10px] text-indigo-400 flex items-center gap-1">
                      <RefreshCw className="h-3 w-3" /> Auto-rebalancing
                    </span>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Add/Edit Modal */}
      <Dialog open={modalOpen} onOpenChange={setModalOpen}>
        <DialogContent className="bg-gray-900 border-gray-800 text-white">
          <DialogHeader>
            <DialogTitle>{editingId ? "Edit Allocation" : "New Capital Allocation"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Select Strategy</Label>
              <Select value={form.strategy} onValueChange={(v) => setForm({...form, strategy: v})}>
                <SelectTrigger className="bg-gray-800 border-gray-700"><SelectValue placeholder="Choose strategy" /></SelectTrigger>
                <SelectContent>
                  {strategies.map(s => <SelectItem key={s.id} value={String(s.id)}>{s.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
               <div className="space-y-2">
                <Label>Type</Label>
                <Select value={form.allocation_type} onValueChange={(v) => setForm({...form, allocation_type: v})}>
                  <SelectTrigger className="bg-gray-800 border-gray-700"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="FIXED">Fixed Amount</SelectItem>
                    <SelectItem value="PERCENTAGE">Percentage</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>{form.allocation_type === 'FIXED' ? 'Amount (₹)' : 'Percentage (%)'}</Label>
                <Input 
                  type="number" 
                  value={form.allocation_type === 'FIXED' ? form.allocated_amount : form.allocated_percentage} 
                  onChange={(e) => setForm({...form, [form.allocation_type === 'FIXED' ? 'allocated_amount' : 'allocated_percentage']: parseFloat(e.target.value) || 0})}
                  className="bg-gray-800 border-gray-700"
                />
              </div>
            </div>
            <div className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg">
              <div className="space-y-0.5">
                <Label>Auto-Rebalance</Label>
                <p className="text-[10px] text-gray-500">Automatically adjust capital periodically</p>
              </div>
              <Switch checked={form.auto_rebalance} onCheckedChange={(v) => setForm({...form, auto_rebalance: v})} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={closeModal}>Cancel</Button>
            <Button onClick={handleSave} className="bg-indigo-600 hover:bg-indigo-700">Save Allocation</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Dialog */}
      <Dialog open={!!deleteDialog} onOpenChange={() => setDeleteDialog(null)}>
        <DialogContent className="bg-gray-900 border-gray-800 text-white">
          <DialogHeader>
            <DialogTitle className="text-rose-400">Remove Allocation</DialogTitle>
          </DialogHeader>
          <div className="py-4 space-y-4">
            <p className="text-sm text-gray-400">This allocation has an active paper trading account. What would you like to do?</p>
            <div className="flex flex-col gap-2">
              <Button variant="outline" className="justify-start border-gray-800" onClick={() => handleConfirmDelete(false)}>
                Keep Paper Account (Detach only)
              </Button>
              <Button variant="destructive" className="justify-start" onClick={() => handleConfirmDelete(true)}>
                Delete Both (Allocation + Account)
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
