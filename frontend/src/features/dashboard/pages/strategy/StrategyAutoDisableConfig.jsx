import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import { Switch } from "@/shared/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/shared/components/ui/dialog";
import { PowerOff, Plus, Edit2, Play, Pause, Trash2 } from 'lucide-react';
import { riskApi } from '@/shared/services/portfolioApi';
import { strategyApi } from '@/shared/services/strategyApi';
import { useNotifications } from '@/shared/hooks/useNotifications';
import StrategyConfigNav from './StrategyConfigNav';
import { usePageActions } from '@/shared/context/PageActionsContext';
import { useEnums } from '@/shared/context/EnumsContext';
import { customConfirm } from "@/shared/components/ui/custom-dialog";
import { GlobalLoader } from '@/shared/components/ui/global-loader';


export default function StrategyAutoDisableConfig() {
  const { id } = useParams();
  const { notify } = useNotifications();
  const { setPageHeader } = usePageActions();
  const { enums } = useEnums();
  const TRIGGER_TYPES = enums.AutoDisableTriggerType || [];

  const [loading, setLoading] = useState(true);
  const [rules, setRules] = useState([]);
  const [strategy, setStrategy] = useState(null);
  
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingRule, setEditingRule] = useState(null);

  const [formData, setFormData] = useState({
    name: '',
    trigger_type: 'CONSECUTIVE_LOSSES',
    threshold_value: 0,
    threshold_count: 5,
    auto_reenable: false,
    cooldown_hours: 24,
    is_active: true
  });

  useEffect(() => {
    if (strategy) {
      setPageHeader(<StrategyConfigNav strategy={strategy} />);
    } else {
      setPageHeader(<StrategyConfigNav strategy={{ id, name: "Strategy Configuration" }} />);
    }
    return () => setPageHeader(null);
  }, [id, strategy, setPageHeader]);

  useEffect(() => {
    if (id) fetchData();
  }, [id]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [res, stratData] = await Promise.all([
        riskApi.getAutoDisableRules({ strategy: id }),
        strategyApi.getById(id)
      ]);
      setRules(res.data || []);
      setStrategy(stratData);
    } catch (error) {
      notify.error('Failed to load auto-disable configuration');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenModal = (rule = null) => {
    if (rule) {
      setEditingRule(rule);
      setFormData({
        name: rule.name,
        trigger_type: rule.trigger_type,
        threshold_value: rule.threshold_value,
        threshold_count: rule.threshold_count,
        auto_reenable: rule.auto_reenable ?? false,
        cooldown_hours: rule.cooldown_hours ?? 24,
        is_active: rule.is_active ?? true
      });
    } else {
      setEditingRule(null);
      setFormData({
        name: '',
        trigger_type: 'CONSECUTIVE_LOSSES',
        threshold_value: 0,
        threshold_count: 5,
        auto_reenable: false,
        cooldown_hours: 24,
        is_active: true
      });
    }
    setIsModalOpen(true);
  };

  const handleSave = async () => {
    if (!formData.name) {
      notify.error('Rule name is required');
      return;
    }
    
    try {
      const payload = {
        strategy: id,
        ...formData
      };

      // Explicitly nullify unused fields based on trigger type
      const type = formData.trigger_type;
      if (type === 'CONSECUTIVE_LOSSES') {
          payload.threshold_value = null;
      } else {
          payload.threshold_count = null;
      }

      if (editingRule) {
        await riskApi.updateAutoDisableRule(editingRule.id, payload);
        notify.success('Auto-disable rule updated');
      } else {
        await riskApi.createAutoDisableRule(payload);
        notify.success('Auto-disable rule created');
      }
      setIsModalOpen(false);
      fetchData();
    } catch (error) {
      notify.error('Failed to save configuration');
    }
  };

  const handleDelete = async (ruleId) => {
    const confirmed = await customConfirm('Are you sure you want to delete this guardian rule?');
    if (confirmed) {
      try {
        await riskApi.deleteAutoDisableRule(ruleId);
        notify.success('Rule deleted');
        fetchData();
      } catch (error) {
        notify.error('Failed to delete rule');
      }
    }
  };

  const toggleStatus = async (rule) => {
    try {
      await riskApi.updateAutoDisableRule(rule.id, { is_active: !rule.is_active });
      notify.success(`Rule ${rule.is_active ? 'paused' : 'activated'}`);
      fetchData();
    } catch (error) {
      notify.error('Failed to update status');
    }
  };

  const getTriggerLabel = (val) => {
    const found = TRIGGER_TYPES.find(c => c.value === val);
    return found ? found.label : val;
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-96 gap-3 flex-col">
        <GlobalLoader />
        <p className="text-gray-400 text-sm">Loading auto-disable settings...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col flex-1 min-h-0">
      <div className="flex-1 overflow-y-auto scrollbar-theme">
        <div className="container-padding py-6 lg:py-8 space-y-6">
          
          <div className="flex items-center justify-between mb-2">
            <div>
              <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                <PowerOff className="h-6 w-6 text-orange-400" />
                Strategy Guardians
              </h2>
              <p className="text-gray-400 mt-1 text-sm">Create rules to automatically pause this strategy when performance degrades.</p>
            </div>
            <Button onClick={() => handleOpenModal()} className="bg-orange-600 hover:bg-orange-700">
              <Plus className="h-4 w-4 mr-1" /> Add Guardian Rule
            </Button>
          </div>

          {rules.length === 0 ? (
            <Card className="bg-gray-900 border-gray-800">
              <CardContent className="h-64 flex flex-col items-center justify-center text-center">
                <PowerOff className="h-12 w-12 text-gray-700 mb-4" />
                <h3 className="text-lg font-medium text-white mb-1">No Guardian Rules Active</h3>
                <p className="text-sm text-gray-400 max-w-sm mb-4">
                  Add a rule to automatically shut down this strategy if it experiences severe drawdowns or loss streaks.
                </p>
                <Button onClick={() => handleOpenModal()} variant="outline" className="border-gray-700">
                  Create First Rule
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {rules.map(rule => (
                <Card key={rule.id} className={`bg-gray-900 border-gray-800 ${!rule.is_active ? 'opacity-60' : ''}`}>
                  <CardHeader className="pb-3 flex flex-row items-center justify-between">
                    <div>
                      <CardTitle className="text-white text-base">{rule.name}</CardTitle>
                      <CardDescription className="text-xs">{getTriggerLabel(rule.trigger_type)}</CardDescription>
                    </div>
                    <div className={`px-2 py-1 rounded-full text-xs font-semibold ${
                      rule.is_active ? 'bg-emerald-500/10 text-emerald-400' : 'bg-gray-500/10 text-gray-400'
                    }`}>
                      {rule.is_active ? 'Monitoring Active' : 'Disabled'}
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      
                      <div className="bg-gray-800/50 p-3 rounded-md">
                        <p className="text-xs text-gray-400 uppercase tracking-wider mb-1">Trigger Thresholds</p>
                        <div className="flex gap-4 text-sm text-gray-300">
                          {rule.threshold_value > 0 && <span>Value: <strong className="text-white">{rule.threshold_value}</strong></span>}
                          {rule.threshold_count > 0 && <span>Count: <strong className="text-white">{rule.threshold_count}</strong></span>}
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-2 text-xs text-gray-400">
                        <div className="bg-gray-800/30 p-2 rounded border border-gray-800/50">
                          Cooldown: <span className="text-gray-200">{rule.cooldown_hours}h</span>
                        </div>
                        <div className="bg-gray-800/30 p-2 rounded border border-gray-800/50">
                          Auto-Restore: <span className={rule.auto_reenable ? "text-emerald-400" : "text-rose-400"}>{rule.auto_reenable ? 'Yes' : 'No'}</span>
                        </div>
                      </div>

                      <div className="flex gap-2 pt-2 border-t border-gray-800">
                        <Button variant="ghost" size="sm" onClick={() => handleOpenModal(rule)} className="flex-1 hover:bg-gray-800 text-blue-400">
                          <Edit2 className="h-3.5 w-3.5 mr-1" /> Edit
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => toggleStatus(rule)} className="flex-1 hover:bg-gray-800">
                          {rule.is_active ? <Pause className="h-3.5 w-3.5 mr-1 text-amber-500" /> : <Play className="h-3.5 w-3.5 mr-1 text-emerald-500" />}
                          {rule.is_active ? 'Pause' : 'Activate'}
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => handleDelete(rule.id)} className="flex-1 hover:bg-gray-800 text-red-400">
                          <Trash2 className="h-3.5 w-3.5 mr-1" /> Delete
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>

      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="bg-gray-900 border-gray-800 text-white max-w-md max-h-[85vh] overflow-y-auto scrollbar-theme">
          <DialogHeader>
            <DialogTitle>{editingRule ? 'Edit Guardian Rule' : 'Create Guardian Rule'}</DialogTitle>
            <DialogDescription>
              A strategy will be automatically paused if these parameters are triggered.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Rule Name</Label>
              <Input 
                value={formData.name} 
                onChange={(e) => setFormData({...formData, name: e.target.value})}
                placeholder="e.g., Drawdown Protector"
                className="bg-gray-800 border-gray-700"
              />
            </div>

            <div className="space-y-2">
              <Label>Trigger Condition</Label>
              <Select value={formData.trigger_type} onValueChange={(v) => setFormData({...formData, trigger_type: v})}>
                <SelectTrigger className="bg-gray-800 border-gray-700">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {TRIGGER_TYPES.map(t => (
                    <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-1 gap-4">
              {['CONSECUTIVE_LOSSES', 'CONSECUTIVE_WINS'].includes(formData.trigger_type) ? (
                <div className="space-y-2">
                  <Label>{formData.trigger_type === 'CONSECUTIVE_LOSSES' ? 'Number of Losing Trades' : 'Number of Winning Trades'}</Label>
                  <Input 
                    type="number"
                    value={formData.threshold_count} 
                    onChange={(e) => setFormData({...formData, threshold_count: parseInt(e.target.value) || 0})}
                    className="bg-gray-800 border-gray-700"
                    placeholder={formData.trigger_type === 'CONSECUTIVE_LOSSES' ? "Min Losses" : "Min Wins"}
                  />
                </div>
              ) : (
                <div className="space-y-2">
                  <Label>
                    {formData.trigger_type === 'WIN_RATE_DROP' ? 'Win Rate Threshold (%)' : 'Loss/Drawdown Threshold (₹ or %)'}
                  </Label>
                  <Input 
                    type="number" step="0.01"
                    value={formData.threshold_value} 
                    onChange={(e) => setFormData({...formData, threshold_value: parseFloat(e.target.value) || 0})}
                    className="bg-gray-800 border-gray-700"
                    placeholder="E.g. 10.0 for 10%"
                  />
                </div>
              )}
            </div>

            <div className="flex flex-col justify-between bg-gray-800/50 p-3 rounded-lg border border-gray-700 gap-2">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label className="text-[13px]">Auto Re-Enable</Label>
                  <p className="text-[10px] text-gray-500 leading-tight">Unpause strategy automatically after cooldown</p>
                </div>
                <Switch checked={formData.auto_reenable} onCheckedChange={(v) => setFormData({...formData, auto_reenable: v})} />
              </div>
            </div>

            {formData.auto_reenable && (
              <div className="space-y-2">
                <Label>Cooldown Hours</Label>
                <Input 
                  type="number"
                  value={formData.cooldown_hours} 
                  onChange={(e) => setFormData({...formData, cooldown_hours: parseInt(e.target.value) || 0})}
                  className="bg-gray-800 border-gray-700"
                  placeholder="24"
                />
                <p className="text-xs text-gray-500">Wait time before rule expires/resets.</p>
              </div>
            )}

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
