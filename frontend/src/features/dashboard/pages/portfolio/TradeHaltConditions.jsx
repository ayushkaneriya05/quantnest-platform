import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/components/ui/select";
import { Input } from "@/shared/components/ui/input";
import { Switch } from "@/shared/components/ui/switch";
import { Label } from "@/shared/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/shared/components/ui/dialog";
import { Plus, Pause, Play, Trash2, Edit2, ShieldAlert } from 'lucide-react';
import { riskApi } from '@/shared/services/portfolioApi';
import { useNotifications } from '@/shared/hooks/useNotifications';
import { useEnums } from '@/shared/context/EnumsContext';
import { usePageActions } from '@/shared/context/PageActionsContext';
import { formatDistanceToNow } from 'date-fns';
import PortfolioRiskNav from './PortfolioRiskNav';


export default function TradeHaltConditions() {
  const { notify } = useNotifications();
  const { setPageHeader } = usePageActions();
  const { enums } = useEnums();
  const CONDITION_TYPES = enums.HaltConditionType || [];
  const [conditions, setConditions] = useState([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    setPageHeader(<PortfolioRiskNav />);
    return () => setPageHeader(null);
  }, [setPageHeader]);
  
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingCondition, setEditingCondition] = useState(null);
  
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    condition_type: 'CONSECUTIVE_LOSSES',
    threshold_value: 0,
    threshold_count: 3,
    halt_duration_minutes: 60,
    close_open_positions: false,
    send_notification: true,
    is_active: true
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const condRes = await riskApi.getHaltConditions();
      setConditions(condRes.data || []);
    } catch (error) {
      notify.error('Failed to load halt conditions');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenModal = (condition = null) => {
    if (condition) {
      setEditingCondition(condition);
      setFormData({
        name: condition.name,
        description: condition.description || '',
        condition_type: condition.condition_type,
        threshold_value: condition.threshold_value,
        threshold_count: condition.threshold_count,
        halt_duration_minutes: condition.halt_duration_minutes,
        close_open_positions: condition.close_open_positions ?? false,
        send_notification: condition.send_notification ?? true,
        is_active: condition.is_active
      });
    } else {
      setEditingCondition(null);
      setFormData({
        name: '',
        description: '',
        condition_type: 'CONSECUTIVE_LOSSES',
        threshold_value: 0,
        threshold_count: 3,
        halt_duration_minutes: 60,
        close_open_positions: false,
        send_notification: true,
        is_active: true
      });
    }
    setIsModalOpen(true);
  };

  const handleSave = async () => {
    if (!formData.name) {
      notify.error('Name is required');
      return;
    }
    
    try {
      const payload = {
        ...formData,
      };

      // Explicitly nullify unused fields based on condition type
      const type = formData.condition_type;
      if (['LOSS_AMOUNT', 'LOSS_PERCENTAGE', 'DRAWDOWN', 'VOLATILITY', 'CUSTOM'].includes(type)) {
         payload.threshold_count = null;
      } else if (['CONSECUTIVE_LOSSES', 'MAX_TRADES'].includes(type)) {
         payload.threshold_value = null;
      } else if (type === 'TIME_BASED') {
         payload.threshold_value = null;
         payload.threshold_count = null;
      }

      if (editingCondition) {
        await riskApi.updateHaltCondition(editingCondition.id, payload);
        notify.success('Halt condition updated');
      } else {
        await riskApi.createHaltCondition(payload);
        notify.success('Halt condition created');
      }
      setIsModalOpen(false);
      fetchData();
    } catch (error) {
      notify.error('Failed to save halt condition');
    }
  };

  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this halt condition?')) {
      try {
        await riskApi.deleteHaltCondition(id);
        notify.success('Halt condition deleted');
        fetchData();
      } catch (error) {
        notify.error('Failed to delete halt condition');
      }
    }
  };

  const toggleStatus = async (condition) => {
    try {
      await riskApi.updateHaltCondition(condition.id, { is_active: !condition.is_active });
      notify.success(`Condition ${condition.is_active ? 'paused' : 'activated'}`);
      fetchData();
    } catch (error) {
      notify.error('Failed to update status');
    }
  };


  const getConditionLabel = (val) => {
    const found = CONDITION_TYPES.find(c => c.value === val);
    return found ? found.label : val;
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-96">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500"></div>
      </div>
    );
  }

  return (
    <div className="container-padding py-6 lg:py-8 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <ShieldAlert className="h-6 w-6 text-orange-400" />
            Trade Halt Conditions
          </h1>
          <p className="text-gray-400 mt-1 text-sm">Configure system-wide or strategy-specific risk limits that trigger an immediate trading halt.</p>
        </div>
        <Button onClick={() => handleOpenModal()} className="bg-orange-600 hover:bg-orange-700">
          <Plus className="h-4 w-4 mr-1" /> Add Halt Rule
        </Button>
      </div>

      {conditions.length === 0 ? (
        <Card className="bg-gray-900 border-gray-800">
          <CardContent className="h-64 flex flex-col items-center justify-center text-center">
            <ShieldAlert className="h-12 w-12 text-gray-700 mb-4" />
            <h3 className="text-lg font-medium text-white mb-1">No Halt Conditions Found</h3>
            <p className="text-sm text-gray-400 max-w-sm mb-4">
              Add a halt condition to automatically stop trading during dangerous market conditions or severe drawdowns.
            </p>
            <Button onClick={() => handleOpenModal()} variant="outline" className="border-gray-700">
              Create First Halt Condition
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {conditions.map(cond => (
            <Card key={cond.id} className={`bg-gray-900 border-gray-800 ${!cond.is_active ? 'opacity-60' : ''}`}>
              <CardHeader className="pb-3 flex flex-row items-center justify-between">
                <div>
                  <CardTitle className="text-white text-base">{cond.name}</CardTitle>
                  <CardDescription className="text-xs">Portfolio Level (All Strategies)</CardDescription>
                </div>
                <div className={`px-2 py-1 rounded-full text-xs font-semibold ${
                  cond.is_active ? 'bg-emerald-500/10 text-emerald-400' : 'bg-gray-500/10 text-gray-400'
                }`}>
                  {cond.is_active ? 'Active' : 'Paused'}
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="bg-gray-800/50 p-3 rounded-md">
                    <p className="text-xs text-gray-400 uppercase tracking-wider mb-1">Trigger Condition</p>
                    <p className="text-sm text-gray-200 font-medium">
                      {getConditionLabel(cond.condition_type)}
                    </p>
                    <div className="mt-2 flex gap-4 text-xs text-gray-400">
                      {cond.threshold_value > 0 && <span>Value: <strong className="text-gray-200">{cond.threshold_value}</strong></span>}
                      {cond.threshold_count > 0 && <span>Count: <strong className="text-gray-200">{cond.threshold_count}</strong></span>}
                    </div>
                  </div>
                  
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Action</p>
                    <p className="text-sm text-gray-300">
                      Halt trading for {cond.halt_duration_minutes === 0 ? 'remainder of day' : `${cond.halt_duration_minutes} minutes`}
                      {cond.close_open_positions && <span className="block text-rose-400 mt-1">Closes all open positions</span>}
                    </p>
                  </div>

                  <div className="flex gap-2 pt-2 border-t border-gray-800">
                    <Button variant="ghost" size="sm" onClick={() => handleOpenModal(cond)} className="flex-1 hover:bg-gray-800 text-blue-400">
                      <Edit2 className="h-3.5 w-3.5 mr-1" /> Edit
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => toggleStatus(cond)} className="flex-1 hover:bg-gray-800">
                      {cond.is_active ? <Pause className="h-3.5 w-3.5 mr-1 text-amber-500" /> : <Play className="h-3.5 w-3.5 mr-1 text-emerald-500" />}
                      {cond.is_active ? 'Pause' : 'Activate'}
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => handleDelete(cond.id)} className="flex-1 hover:bg-gray-800 text-red-400">
                      <Trash2 className="h-3.5 w-3.5 mr-1" /> Delete
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="bg-gray-900 border-gray-800 text-white max-w-md max-h-[85vh] overflow-y-auto scrollbar-theme">
          <DialogHeader>
            <DialogTitle>{editingCondition ? 'Edit Halt Condition' : 'Create Halt Condition'}</DialogTitle>
            <DialogDescription>
              Set limits that will instantly stop trading to protect capital.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Rule Name</Label>
              <Input 
                value={formData.name} 
                onChange={(e) => setFormData({...formData, name: e.target.value})}
                placeholder="e.g., Catastrophic Loss Halt"
                className="bg-gray-800 border-gray-700"
              />
            </div>


            <div className="space-y-2">
              <Label>Condition Type</Label>
              <Select value={formData.condition_type} onValueChange={(v) => setFormData({...formData, condition_type: v})}>
                <SelectTrigger className="bg-gray-800 border-gray-700">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CONDITION_TYPES.map(t => (
                    <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Threshold Value</Label>
                <Input 
                  type="number" step="0.01"
                  value={formData.threshold_value} 
                  onChange={(e) => setFormData({...formData, threshold_value: parseFloat(e.target.value) || 0})}
                  className="bg-gray-800 border-gray-700"
                />
              </div>
              <div className="space-y-2">
                <Label>Count Trigger</Label>
                <Input 
                  type="number"
                  value={formData.threshold_count} 
                  onChange={(e) => setFormData({...formData, threshold_count: parseInt(e.target.value) || 0})}
                  className="bg-gray-800 border-gray-700"
                  disabled={formData.condition_type !== 'CONSECUTIVE_LOSSES' && formData.condition_type !== 'MAX_TRADES'}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label>Halt Duration (minutes)</Label>
              <Input 
                type="number"
                value={formData.halt_duration_minutes} 
                onChange={(e) => setFormData({...formData, halt_duration_minutes: parseInt(e.target.value) || 0})}
                className="bg-gray-800 border-gray-700"
              />
              <p className="text-xs text-gray-500">Set to 0 to halt for the remainder of the trading day.</p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="flex items-center justify-between bg-gray-800/50 p-3 rounded-lg border border-gray-700">
                <div className="space-y-0.5">
                  <Label>Close Positions</Label>
                  <p className="text-[10px] text-gray-500">Close open positions on halt</p>
                </div>
                <Switch checked={formData.close_open_positions} onCheckedChange={(v) => setFormData({...formData, close_open_positions: v})} />
              </div>
              <div className="flex items-center justify-between bg-gray-800/50 p-3 rounded-lg border border-gray-700">
                <div className="space-y-0.5">
                  <Label>Notify Admin</Label>
                  <p className="text-[10px] text-gray-500">Send alert on halt</p>
                </div>
                <Switch checked={formData.send_notification} onCheckedChange={(v) => setFormData({...formData, send_notification: v})} />
              </div>
            </div>

            <div className="flex items-center justify-between bg-gray-800/50 p-3 rounded-lg border border-gray-700">
              <Label>Active Status</Label>
              <Switch checked={formData.is_active} onCheckedChange={(v) => setFormData({...formData, is_active: v})} />
            </div>
          </div>

          <DialogFooter>
            <Button variant="ghost" onClick={() => setIsModalOpen(false)}>Cancel</Button>
            <Button onClick={handleSave} className="bg-orange-600 hover:bg-orange-700">Save Rule</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
