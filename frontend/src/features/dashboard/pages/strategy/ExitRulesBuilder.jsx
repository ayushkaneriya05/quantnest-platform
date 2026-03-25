/**
 * Exit Rules Builder - stop loss and target configuration
 */
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import { Badge } from "@/shared/components/ui/badge";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import { Switch } from "@/shared/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/components/ui/select";
import { 
  Plus, Trash2, Save, Shield, Target, TrendingDown,
  Loader2, Sparkles, Activity
} from 'lucide-react';
import StrategyConfigNav from './StrategyConfigNav';
import StrategyFooter from './StrategyFooter';
import { ruleGroupApi, stopLossApi, targetApi } from '@/shared/services/rulesApi';
import { strategyApi, exitConfigApi } from '@/shared/services/strategyApi';
import { useNotifications } from '@/shared/hooks/useNotifications';
import { useEnums } from '@/shared/context/EnumsContext';



import { usePageActions } from '@/shared/context/PageActionsContext'; // Added import

const PARAM_CONFIG = {
  SMA: [{ key: 'period', label: 'Period', default: 14 }],
  EMA: [{ key: 'period', label: 'Period', default: 14 }],
  WMA: [{ key: 'period', label: 'Period', default: 14 }],
  RSI: [{ key: 'period', label: 'Period', default: 14 }],
  ROC: [{ key: 'period', label: 'Period', default: 9 }],
  CCI: [{ key: 'period', label: 'Period', default: 20 }],
  ADX: [{ key: 'period', label: 'Period', default: 14 }],
  PLUS_DI: [{ key: 'period', label: 'Period', default: 14 }],
  MINUS_DI: [{ key: 'period', label: 'Period', default: 14 }],
  MACD: [
    { key: 'fast_period', label: 'Fast', default: 12 },
    { key: 'slow_period', label: 'Slow', default: 26 },
    { key: 'signal_period', label: 'Sig', default: 9 }
  ],
  MACD_SIGNAL: [
    { key: 'fast_period', label: 'Fast', default: 12 },
    { key: 'slow_period', label: 'Slow', default: 26 },
    { key: 'signal_period', label: 'Sig', default: 9 }
  ],
  MACD_HISTOGRAM: [
    { key: 'fast_period', label: 'Fast', default: 12 },
    { key: 'slow_period', label: 'Slow', default: 26 },
    { key: 'signal_period', label: 'Sig', default: 9 }
  ],
  BOLLINGER_UPPER: [
    { key: 'period', label: 'Period', default: 20 },
    { key: 'std_dev', label: 'StdDev', default: 2 }
  ],
  BOLLINGER_LOWER: [
    { key: 'period', label: 'Period', default: 20 },
    { key: 'std_dev', label: 'StdDev', default: 2 }
  ],
  BOLLINGER_MID: [
    { key: 'period', label: 'Period', default: 20 },
    { key: 'std_dev', label: 'StdDev', default: 2 }
  ],
  STOCHASTIC_K: [
    { key: 'k_period', label: '%K', default: 14 },
    { key: 'd_period', label: '%D', default: 3 },
    { key: 'smooth', label: 'Smth', default: 3 }
  ],
  STOCHASTIC_D: [
    { key: 'k_period', label: '%K', default: 14 },
    { key: 'd_period', label: '%D', default: 3 },
    { key: 'smooth', label: 'Smth', default: 3 }
  ],
  SUPERTREND: [
    { key: 'period', label: 'Period', default: 7 },
    { key: 'multiplier', label: 'Mult', default: 3 }
  ],
  ATR: [{ key: 'period', label: 'Period', default: 14 }],
  MFI: [{ key: 'period', label: 'Period', default: 14 }],
  WILLIAMS_R: [{ key: 'period', label: 'Period', default: 14 }],
  OBV: [],
  VWAP: [],
  PIVOT_POINT: []
};

const getDefaultParams = (type) => {
  const config = PARAM_CONFIG[type] || [];
  return config.reduce((acc, param) => ({ ...acc, [param.key]: param.default }), {});
};

export default function ExitRulesBuilder() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { notify } = useNotifications();
  const { enums } = useEnums();
  const { setPageHeader } = usePageActions(); // Use context
  
  const [strategy, setStrategy] = useState(null);
  const [exitConfig, setExitConfig] = useState(null);
  const [stopLossRules, setStopLossRules] = useState([]);
  const [targetRules, setTargetRules] = useState([]);
  const [slGroups, setSlGroups] = useState([]);
  const [targetGroups, setTargetGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [pendingEdits, setPendingEdits] = useState({
    slRules: {}, // ruleId -> {updates}
    targetRules: {}, // ruleId -> {updates}
    groups: {}, // groupId -> {updates}
    exitConfig: null // {updates}
  });

  const hasPendingChanges = 
    Object.keys(pendingEdits.slRules).length > 0 || 
    Object.keys(pendingEdits.targetRules).length > 0 || 
    Object.keys(pendingEdits.groups).length > 0 || 
    pendingEdits.exitConfig !== null;

  useEffect(() => {
    if (id) fetchData();
  }, [id]);

  // Set Navigation in Header
  useEffect(() => {
    setPageHeader(<StrategyConfigNav strategy={strategy} />);
    return () => setPageHeader(null);
  }, [strategy, setPageHeader]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [strategyData, slRules, tgtRules, slGroupData, tgtGroupData] = await Promise.all([
        strategyApi.getById(id),
        stopLossApi.getByStrategy(id),
        targetApi.getByStrategy(id),
        ruleGroupApi.getByStrategy(id, 'STOP_LOSS'),
        ruleGroupApi.getByStrategy(id, 'TARGET')
      ]);
      setStrategy(strategyData);
      setStopLossRules(slRules);
      setTargetRules(tgtRules);
      setSlGroups(slGroupData);
      setTargetGroups(tgtGroupData);
      setPendingEdits({ slRules: {}, targetRules: {}, groups: {}, exitConfig: null });

      setTargetGroups(tgtGroupData);

      // Use exit config from strategy data
      if (strategyData?.exit_order_config) {
        setExitConfig(strategyData.exit_order_config);
      } else {
        console.warn("No exit config found for strategy");
        // Optional: Could trigger a create here if needed, but backend should handle it on creation.
      }

    } catch (error) {
      notify.error('Failed to load exit rules');
    } finally {
      setLoading(false);
    }
  };

  // ─── GROUP HANDLERS ───
  const handleAddGroup = async (type) => {
    try {
      const isSL = type === 'STOP_LOSS';
      const groups = isSL ? slGroups : targetGroups;
      const setGroups = isSL ? setSlGroups : setTargetGroups;

      const newGroup = await ruleGroupApi.create({
        strategy: id,
        name: `${isSL ? 'Stop Loss' : 'Target'} Group ${groups.length + 1}`,
        rule_type: type,
        logical_operator: 'OR', // Default to OR for exit groups usually
        priority: groups.length + 1,
      });
      
      setGroups([...groups, { ...newGroup, stop_loss_rules: [], target_rules: [] }]);
      notify.success('Group added');
    } catch (error) {
      notify.error('Failed to add group');
    }
  };

  const handleDeleteGroup = async (groupId, type) => {
    if (!confirm('Delete this group and all its rules?')) return;
    try {
      const isSL = type === 'STOP_LOSS';
      const groups = isSL ? slGroups : targetGroups;
      const setGroups = isSL ? setSlGroups : setTargetGroups;

      await ruleGroupApi.delete(groupId);
      setGroups(groups.filter(g => g.id !== groupId));
      notify.success('Group deleted');
    } catch (error) {
      notify.error('Failed to delete group');
    }
  };

  const handleUpdateGroup = async (groupId, field, value, type) => {
    const isSL = type === 'STOP_LOSS';
    const setGroups = isSL ? setSlGroups : setTargetGroups;

    // Local update
    setGroups(prev => prev.map(g => 
      g.id === groupId ? { ...g, [field]: value } : g
    ));

    // Record for manual save
    setPendingEdits(prev => ({
      ...prev,
      groups: {
        ...prev.groups,
        [groupId]: { ...(prev.groups[groupId] || {}), [field]: value }
      }
    }));
  };

  // ─── EXIT CONFIG HANDLER ───
  const handleExitConfigUpdate = async (field, value) => {
    if (!exitConfig?.id) return;
    
    // Local Update
    const newConfig = { ...exitConfig, [field]: value };
    setExitConfig(newConfig);

    // Record for manual save
    setPendingEdits(prev => ({
      ...prev,
      exitConfig: { ...(prev.exitConfig || {}), [field]: value }
    }));
  };

  // ─── NESTED RULE HANDLERS ───
  const handleAddStopLossToGroup = async (groupId) => {
    try {
      const group = slGroups.find(g => g.id === groupId);
      const outputRules = group?.stop_loss_rules || [];
      
      const newSL = await stopLossApi.create({
        rule_group: groupId,
        sl_type: 'FIXED_PERCENTAGE',
        fixed_percentage: 1.0,
        is_active: true,
        // Ensure other fields are null where allowed
        fixed_points: null,
        candle_part: null,
        // candle_offset is non-nullable, rely on default
        indicator_type: null,
        indicator_params: null,
        trailing_value: null
      });
      
      setSlGroups(slGroups.map(g => 
        g.id === groupId 
          ? { ...g, stop_loss_rules: [...(g.stop_loss_rules || []), newSL] } 
          : g
      ));
      notify.success('Stop loss rule added');
    } catch (error) {
      notify.error('Failed to add stop loss');
    }
  };

  const handleAddTargetToGroup = async (groupId) => {
    try {
      const group = targetGroups.find(g => g.id === groupId);
      const outputRules = group?.target_rules || [];

      const newTgt = await targetApi.create({
        rule_group: groupId,
        target_type: 'RISK_REWARD',
        risk_reward_ratio: 2.0,
        is_active: true,
        // Ensure other fields are null
        fixed_percentage: null,
        fixed_points: null,
        indicator_type: null,
        indicator_params: null,
        time_limit_seconds: null,
        price_target: null
      });

      setTargetGroups(targetGroups.map(g => 
        g.id === groupId 
          ? { ...g, target_rules: [...(g.target_rules || []), newTgt] } 
          : g
      ));
      notify.success('Target rule added');
    } catch (error) {
      notify.error('Failed to add target');
    }
  };

  const handleUpdateNestedRule = async (groupId, ruleId, field, value, type) => {
    let updates = { [field]: value };

    // Logic for cleanup and explicit defaults
    if (field === 'sl_type') {
      // Reset incompatible fields for Stop Loss
      updates = {
        sl_type: value,
        fixed_percentage: null,
        fixed_points: null,
        emergency_loss_pct: null,
        candle_part: null,
        // Reset non-nullable fields with defaults
        candle_offset: 0,
        trailing_value: null,
        indicator_type: null,
        indicator_params: null,
        operator: null,
        threshold_value: null,
        threshold_value2: null,
        compare_to_indicator: null,
        compare_to_params: null
      };

      // Set defaults for new type
      if (value === 'FIXED_PERCENTAGE') updates.fixed_percentage = 1.0;
      else if (value === 'FIXED_POINTS') updates.fixed_points = 10.0;
      else if (value === 'TRAILING_PERCENTAGE') updates.trailing_value = 1.0;
      else if (value === 'TRAILING_POINTS') updates.trailing_value = 10.0;
      else if (value === 'CANDLE_BASED') {
        updates.candle_part = 'LOW';
        updates.candle_offset = 0;
      }
      else if (value === 'INDICATOR_BASED') {
        const defaultType = 'SMA';
        updates.indicator_type = defaultType;
        updates.indicator_params = getDefaultParams(defaultType);
        updates.operator = 'LT'; // Default operator for SL
      }
    } 
    else if (field === 'target_type') {
      // Reset incompatible fields for Target
      updates = {
        target_type: value,
        fixed_percentage: null,
        fixed_points: null,
        risk_reward_ratio: null,
        price_target: null,
        time_limit_seconds: null,
        indicator_type: null,
        indicator_params: null,
        operator: null,
        threshold_value: null,
        threshold_value2: null,
        compare_to_indicator: null,
        compare_to_params: null
      };

      // Set defaults for new type
      if (value === 'FIXED_PERCENTAGE') updates.fixed_percentage = 2.0;
      else if (value === 'FIXED_POINTS') updates.fixed_points = 20.0;
      else if (value === 'RISK_REWARD') updates.risk_reward_ratio = 2.0;
      else if (value === 'TIME_BASED') updates.time_limit_seconds = 3600;
      else if (value === 'INDICATOR_BASED') {
        const defaultType = 'SMA';
        updates.indicator_type = defaultType;
        updates.indicator_params = getDefaultParams(defaultType);
        updates.operator = 'GT'; // Default operator for Target
      }
    }
    else if (field === 'indicator_type') {
      // Explicit defaults for indicator change
      updates.indicator_params = getDefaultParams(value);
    }
    else if (field === 'compare_to_indicator') {
        if (value) {
            updates.compare_to_params = getDefaultParams(value);
            updates.threshold_value = null; // Clear fixed value
        } else {
            updates.compare_to_params = null;
            updates.threshold_value = 0; // Set default fixed value
        }
    }
    else if (field === 'operator') {
        if (value !== 'BETWEEN') {
            updates.threshold_value2 = null;
        }
    }

    // Wrapper for multi-field update
    await handleUpdateNestedRuleFields(groupId, ruleId, updates, type);
  };

  const handleUpdateNestedRuleFields = async (groupId, ruleId, updates, type) => {
    const isSL = type === 'STOP_LOSS';
    const setGroups = isSL ? setSlGroups : setTargetGroups;
    const listKey = isSL ? 'stop_loss_rules' : 'target_rules';
    const pendingKey = isSL ? 'slRules' : 'targetRules';

    // Local update
    setGroups(prev => prev.map(g => {
      if (g.id !== groupId) return g;
      return {
        ...g,
        [listKey]: (g[listKey] || []).map(r => r.id === ruleId ? { ...r, ...updates } : r)
      };
    }));

    // Record for manual save
    setPendingEdits(prev => ({
      ...prev,
      [pendingKey]: {
        ...prev[pendingKey],
        [ruleId]: { ...(prev[pendingKey][ruleId] || {}), ...updates }
      }
    }));
  };

  const handleDeleteNestedRule = async (groupId, ruleId, type) => {
    try {
      const isSL = type === 'STOP_LOSS';
      const api = isSL ? stopLossApi : targetApi;
      const groups = isSL ? slGroups : targetGroups;
      const setGroups = isSL ? setSlGroups : setTargetGroups;
      const listKey = isSL ? 'stop_loss_rules' : 'target_rules';

      await api.delete(ruleId);
      
      setGroups(groups.map(g => {
        if (g.id !== groupId) return g;
        return {
          ...g,
          [listKey]: (g[listKey] || []).filter(r => r.id !== ruleId)
        };
      }));
      notify.success('Rule deleted');
    } catch (error) {
      notify.error('Failed to delete rule');
    }
  };

  const handleAddStopLoss = async () => {
    try {
      const newSL = await stopLossApi.create({
        strategy: id,
        name: `Stop Loss ${stopLossRules.length + 1}`,
        sl_type: 'FIXED_PERCENTAGE',
        fixed_percentage: 2.0,
        is_active: true,
        // Ensure other fields are null where allowed
        // candle_offset is non-nullable, rely on default
        fixed_points: null,
        candle_part: null,
        indicator_type: null,
        indicator_params: null,
        trailing_value: null
      });
      setStopLossRules([...stopLossRules, newSL]);
      notify.success('Stop loss rule added');
    } catch (error) {
      notify.error('Failed to add stop loss');
    }
  };

  const handleDeleteStopLoss = async (slId) => {
    try {
      await stopLossApi.delete(slId);
      setStopLossRules(stopLossRules.filter(sl => sl.id !== slId));
      notify.success('Stop loss deleted');
    } catch (error) {
      notify.error('Failed to delete stop loss');
    }
  };

  const handleUpdateStopLoss = async (slId, field, value) => {
    try {
      await stopLossApi.update(slId, { [field]: value });
      setStopLossRules(stopLossRules.map(sl => 
        sl.id === slId ? { ...sl, [field]: value } : sl
      ));
    } catch (error) {
      notify.error('Failed to update stop loss');
    }
  };

  const handleAddTarget = async () => {
    try {
      const newTgt = await targetApi.create({
        strategy: id,
        name: `Target ${targetRules.length + 1}`,
        target_type: 'FIXED_PERCENTAGE',
        fixed_percentage: 3.0,
        is_active: true,
        // Ensure other fields are null
        fixed_points: null,
        indicator_type: null,
        indicator_params: null,
        time_limit_seconds: null,
        price_target: null,
        risk_reward_ratio: null
      });
      setTargetRules([...targetRules, newTgt]);
      notify.success('Target rule added');
    } catch (error) {
      notify.error('Failed to add target');
    }
  };

  const handleDeleteTarget = async (tgtId) => {
    try {
      await targetApi.delete(tgtId);
      setTargetRules(targetRules.filter(t => t.id !== tgtId));
      notify.success('Target deleted');
    } catch (error) {
      notify.error('Failed to delete target');
    }
  };

  const handleUpdateTarget = async (tgtId, field, value) => {
    try {
      await targetApi.update(tgtId, { [field]: value });
      setTargetRules(targetRules.map(t => 
        t.id === tgtId ? { ...t, [field]: value } : t
      ));
    } catch (error) {
      notify.error('Failed to update target');
    }
  };

  const handleSaveAll = async () => {
    if (!hasPendingChanges) return;
    
    try {
      setSaving(true);
      const promises = [];

      // Save Rules
      Object.entries(pendingEdits.slRules).forEach(([id, updates]) => {
        promises.push(stopLossApi.update(id, updates));
      });
      Object.entries(pendingEdits.targetRules).forEach(([id, updates]) => {
        promises.push(targetApi.update(id, updates));
      });

      // Save Groups
      Object.entries(pendingEdits.groups).forEach(([id, updates]) => {
        promises.push(ruleGroupApi.update(id, updates));
      });

      // Save Exit Config
      if (pendingEdits.exitConfig) {
        promises.push(exitConfigApi.update(exitConfig.id, pendingEdits.exitConfig));
      }

      await Promise.all(promises);
      setPendingEdits({ slRules: {}, targetRules: {}, groups: {}, exitConfig: null });
      notify.success('All changes saved');
    } catch (error) {
      console.error(error);
      notify.error('Failed to save some changes');
    } finally {
      setSaving(false);
    }
  };

  const handleCancelAll = () => {
    if (hasPendingChanges && confirm('Discard all unsaved changes?')) {
      fetchData();
    }
  };

  // Helper to render indicator params
  const renderIndicatorParams = (type, params, onUpdate, compact = false) => {
                                  // PARAM_CONFIG is now defined at top of file
    
    // Add default if not found
    const config = PARAM_CONFIG[type] || [{ key: 'period', label: 'Period', default: 14 }];

    return (
      <div className={`flex gap-1.5 flex-wrap`}>
        {config.map(param => (
          <Input
            key={param.key}
            type="number"
            value={params?.[param.key] ?? param.default}
            onChange={(e) => {
               const val = e.target.value === '' ? '' : parseInt(e.target.value);
               const newParams = { 
                 ...(params || {}), 
                 [param.key]: isNaN(val) ? param.default : val 
               };
               onUpdate(newParams);
            }}
            className={`${compact ? 'w-20 h-7 px-1 text-[10px]' : 'w-28 h-9'} bg-gray-800/60 border-gray-700 text-sm text-center`}
            placeholder={param.label}
            title={param.label}
          />
        ))}
      </div>
    );
  };

  const renderStopLossGroup = (group) => (
    <Card key={group.id} className="bg-gray-900/40 border-gray-800/80 mb-6">
      <CardHeader className="pb-3 border-b border-gray-800/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-1.5 rounded-md bg-rose-500/10`}>
              <Target className="h-4 w-4 text-rose-400" />
            </div>
            <Input
              value={group.name}
              onChange={(e) => handleUpdateGroup(group.id, 'name', e.target.value, 'STOP_LOSS')}
              className="bg-transparent border-none text-white font-medium text-base p-0 h-auto focus:ring-0 max-w-[250px]"
            />
            {/* Logical Operator */}
            <Select
              value={group.logical_operator || 'OR'}
              onValueChange={(v) => handleUpdateGroup(group.id, 'logical_operator', v, 'STOP_LOSS')}
            >
              <SelectTrigger className="w-[70px] bg-gray-800/60 border-gray-700 text-xs h-7 mx-2">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="AND">AND</SelectItem>
                <SelectItem value="OR">OR</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center gap-2">
            <Button 
                onClick={() => handleAddStopLossToGroup(group.id)} 
                variant="outline" 
                size="sm" 
                className="border-rose-500/30 text-rose-400 hover:bg-rose-500/10 hover:text-rose-300 h-8"
              >
                <Plus className="h-3.5 w-3.5 mr-1.5" />
                Add Rule
            </Button>
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={() => handleDeleteGroup(group.id, 'STOP_LOSS')}
              className="text-gray-500 hover:text-rose-400 hover:bg-rose-500/10 h-8 w-8 p-0"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4 pt-4">
        {(!group.stop_loss_rules || group.stop_loss_rules.length === 0) ? (
          <div className="text-center py-6 border border-dashed border-gray-700/60 rounded-lg">
             <p className="text-gray-500 text-sm">No stop loss rules in this group</p>
          </div>
        ) : (
          <div className="space-y-2">
            {group.stop_loss_rules.map((sl, index) => (
              <div key={sl.id} className="flex flex-wrap items-center gap-2 p-2 bg-gray-800/40 rounded-lg border border-gray-700/40 hover:border-gray-700 transition-colors">
                <span className="text-xs font-mono text-gray-500 w-6 text-center shrink-0">{index + 1}</span>
                
                {/* Type Selection */}
                <Select 
                  value={sl.sl_type} 
                  onValueChange={(v) => handleUpdateNestedRule(group.id, sl.id, 'sl_type', v, 'STOP_LOSS')}
                >
                  <SelectTrigger className="w-[200px] bg-gray-800/60 border-gray-700 text-xs h-8">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {(enums.StopLossType || []).map(t => (
                      <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                {/* Primary Value Input (Fixed/Trailing) */}
                {['FIXED_POINTS', 'FIXED_PERCENTAGE', 'TRAILING_FIXED', 'TRAILING_PERCENTAGE'].includes(sl.sl_type) && (
                  <div className="flex items-center gap-1.5 px-1 border-l border-gray-700/50">
                    <Input
                      type="number" step="0.1"
                      value={(() => {
                        if (sl.sl_type?.includes('PERCENTAGE') && !sl.sl_type?.includes('TRAILING')) return sl.fixed_percentage;
                        if (sl.sl_type?.includes('POINTS')) return sl.fixed_points;
                        if (sl.sl_type?.includes('TRAILING')) return sl.trailing_value;
                        return '';
                      })() ?? ''}
                       onChange={(e) => {
                        let field = null;
                        if (sl.sl_type?.includes('PERCENTAGE') && !sl.sl_type?.includes('TRAILING')) field = 'fixed_percentage';
                        else if (sl.sl_type?.includes('POINTS')) field = 'fixed_points';
                        else if (sl.sl_type?.includes('TRAILING')) field = 'trailing_value';
                        
                        const val = e.target.value === '' ? '' : parseFloat(e.target.value);
                        if (field) handleUpdateNestedRule(group.id, sl.id, field, val, 'STOP_LOSS');
                      }}
                      className="w-24 bg-gray-800/60 border-gray-700 text-white h-8 text-xs text-center"
                    />
                    <span className="text-[10px] text-gray-500 uppercase">
                      {sl.sl_type?.includes('PERCENTAGE') ? '%' : 'Pts'}
                    </span>
                  </div>
                )}

                {/* Time Based */}
                {sl.sl_type === 'TIME_BASED' && (
                  <div className="flex items-center gap-1.5 px-1 border-l border-gray-700/50">
                    <span className="text-[10px] text-gray-500">Wait</span>
                    <Input
                      type="number"
                      value={sl.time_minutes ?? ''}
                      onChange={(e) => {
                        const val = e.target.value === '' ? '' : parseInt(e.target.value);
                        handleUpdateNestedRule(group.id, sl.id, 'time_minutes', val, 'STOP_LOSS');
                      }}
                      className="w-24 bg-gray-800/60 border-gray-700 text-white h-8 text-xs text-center"
                    />
                    <span className="text-[10px] text-gray-500 uppercase">Mins</span>
                  </div>
                )}

                {/* Emergency */}
                {sl.sl_type === 'EMERGENCY' && (
                  <div className="flex items-center gap-1.5 px-1 border-l border-gray-700/50">
                    <span className="text-[10px] text-gray-500">Max Loss</span>
                    <Input
                      type="number" step="0.1"
                      value={sl.emergency_loss_pct ?? ''}
                      onChange={(e) => {
                        const val = e.target.value === '' ? '' : parseFloat(e.target.value);
                        handleUpdateNestedRule(group.id, sl.id, 'emergency_loss_pct', val, 'STOP_LOSS');
                      }}
                      className="w-24 bg-gray-800/60 border-gray-700 text-white h-8 text-xs text-center"
                    />
                    <span className="text-[10px] text-gray-500 uppercase">%</span>
                  </div>
                )}

                {/* Candle Based */}
                {sl.sl_type === 'CANDLE_BASED' && (
                  <div className="flex items-center gap-1.5 px-1 border-l border-gray-700/50">
                    <Select 
                      value={sl.candle_part || 'LOW'} 
                      onValueChange={(v) => handleUpdateNestedRule(group.id, sl.id, 'candle_part', v, 'STOP_LOSS')}
                    >
                      <SelectTrigger className="w-28 bg-gray-800/60 border-gray-700 text-[10px] h-8">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {(enums.CandlePart || []).map(p => (
                          <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <span className="text-[10px] text-gray-500">of candle</span>
                    <Input
                      type="number" title="Offset"
                      value={sl.candle_offset ?? ''}
                      onChange={(e) => {
                        const val = e.target.value === '' ? '' : parseInt(e.target.value);
                        handleUpdateNestedRule(group.id, sl.id, 'candle_offset', val, 'STOP_LOSS');
                      }}
                      className="w-16 bg-gray-800/60 border-gray-700 text-white h-8 text-xs text-center"
                    />
                    <span className="text-[10px] text-gray-500">L.back</span>
                    <Input
                      type="number" title="Lookback"
                      value={sl.candle_lookback ?? ''}
                      onChange={(e) => {
                        const val = e.target.value === '' ? '' : parseInt(e.target.value);
                        handleUpdateNestedRule(group.id, sl.id, 'candle_lookback', val, 'STOP_LOSS');
                      }}
                      className="w-16 bg-gray-800/60 border-gray-700 text-white h-8 text-xs text-center"
                    />
                  </div>
                )}

                {/* Indicator Based / Trailing Indicator */}
                {['INDICATOR_BASED', 'TRAILING_INDICATOR'].includes(sl.sl_type) && (
                  <div className="flex items-center gap-1.5 bg-gray-900/40 p-1 px-2 rounded-md border border-gray-700/30 flex-wrap">
                    <Select 
                      value={sl.indicator_type || ''} 
                      onValueChange={(v) => handleUpdateNestedRule(group.id, sl.id, 'indicator_type', v, 'STOP_LOSS')}
                    >
                      <SelectTrigger className="w-[160px] bg-gray-800/60 border-gray-700 text-[10px] h-7">
                        <SelectValue placeholder="Indicator" />
                      </SelectTrigger>
                      <SelectContent>
                        {(enums.IndicatorType || []).map(ind => (
                          <SelectItem key={ind.value} value={ind.value}>{ind.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    
                    {sl.indicator_type && renderIndicatorParams(
                      sl.indicator_type, 
                      sl.indicator_params, 
                      (newParams) => handleUpdateNestedRule(group.id, sl.id, 'indicator_params', newParams, 'STOP_LOSS'),
                      true
                    )}

                    {/* Timeframe Override for indicators */}
                    <Select 
                      value={sl.timeframe_override || 'NONE'} 
                      onValueChange={(v) => handleUpdateNestedRule(group.id, sl.id, 'timeframe_override', v === 'NONE' ? '' : v, 'STOP_LOSS')}
                    >
                      <SelectTrigger className="w-[120px] bg-gray-800/60 border-gray-700 text-[10px] h-7">
                        <SelectValue placeholder="TF Override" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="NONE">Default</SelectItem>
                        {(enums.CandleTimeframe || []).map(tf => (
                          <SelectItem key={tf.value} value={tf.value}>{tf.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>

                    {sl.sl_type === 'INDICATOR_BASED' && (
                      <div className="flex items-center gap-1.5 border-l border-gray-700/50 pl-1.5">
                        <Select 
                          value={sl.operator || 'LT'} 
                          onValueChange={(v) => handleUpdateNestedRule(group.id, sl.id, 'operator', v, 'STOP_LOSS')}
                        >
                          <SelectTrigger className="w-[80px] bg-gray-800/60 border-gray-700 text-[10px] h-7">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {(enums.ComparisonOperator || []).map(op => (
                              <SelectItem key={op.value} value={op.value}>{op.label}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>

                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => {
                              if (sl.compare_to_indicator) {
                                handleUpdateNestedRuleFields(group.id, sl.id, { compare_to_indicator: null, compare_to_params: null }, 'STOP_LOSS');
                              } else {
                                handleUpdateNestedRuleFields(group.id, sl.id, { compare_to_indicator: 'SMA', threshold_value: null }, 'STOP_LOSS');
                              }
                            }}
                            className={`h-7 w-7 rounded flex items-center justify-center transition-colors border ${
                              sl.compare_to_indicator ? 'bg-indigo-500/20 border-indigo-500/30 text-indigo-400' : 'bg-gray-800/40 border-gray-700 text-gray-500'
                            }`}
                            title="Compare Indicator vs Value/Indicator"
                          >
                            {sl.compare_to_indicator ? <Activity className="h-3 w-3" /> : <span className="text-[9px] font-bold">123</span>}
                          </button>



                          {sl.compare_to_indicator ? (
                            <div className="flex items-center gap-1">
                              <Select 
                                value={sl.compare_to_indicator} 
                                onValueChange={(v) => handleUpdateNestedRule(group.id, sl.id, 'compare_to_indicator', v, 'STOP_LOSS')}
                              >
                                <SelectTrigger className="w-[120px] bg-gray-800/60 border-gray-700 text-[10px] h-7">
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  {(enums.IndicatorType || []).map(ind => (
                                    <SelectItem key={ind.value} value={ind.value}>{ind.label}</SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>

                              {/* Secondary indicator params */}
                              {sl.compare_to_indicator && renderIndicatorParams(
                                sl.compare_to_indicator,
                                sl.compare_to_params,
                                (newParams) => handleUpdateNestedRule(group.id, sl.id, 'compare_to_params', newParams, 'STOP_LOSS'),
                                true
                              )}
                            </div>
                          ) : (
                            <Input
                              type="number"
                              value={sl.threshold_value ?? ''}
                              onChange={(e) => {
                                const val = e.target.value === '' ? '' : parseFloat(e.target.value);
                                handleUpdateNestedRule(group.id, sl.id, 'threshold_value', val, 'STOP_LOSS');
                              }}
                              className="w-20 bg-gray-800/60 border-gray-700 text-white h-7 text-[10px] text-center"
                              placeholder="Min"
                            />
                          )}

                          {sl.operator === 'BETWEEN' && !sl.compare_to_indicator && (
                            <div className="flex items-center gap-1">
                               <span className="text-[10px] text-gray-400">to</span>
                               <Input
                                type="number"
                                value={sl.threshold_value2 ?? ''}
                                onChange={(e) => {
                                  const val = e.target.value === '' ? '' : parseFloat(e.target.value);
                                  handleUpdateNestedRule(group.id, sl.id, 'threshold_value2', val, 'STOP_LOSS');
                                }}
                                className="w-20 bg-gray-800/60 border-gray-700 text-white h-7 text-[10px] text-center"
                                placeholder="Max"
                              />
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                <div className="flex-1" />

                <div className="flex items-center gap-2 pr-1">
                  <Switch 
                    checked={sl.is_active} 
                    onCheckedChange={(v) => handleUpdateNestedRule(group.id, sl.id, 'is_active', v, 'STOP_LOSS')}
                    className="scale-75"
                  />
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    onClick={() => handleDeleteNestedRule(group.id, sl.id, 'STOP_LOSS')}
                    className="text-gray-500 hover:text-rose-400 h-7 w-7 p-0"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );



  const renderTargetGroup = (group) => (
    <Card key={group.id} className="bg-gray-900/40 border-gray-800/80 mb-6">
      <CardHeader className="pb-3 border-b border-gray-800/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-1.5 rounded-md bg-emerald-500/10`}>
              <Target className="h-4 w-4 text-emerald-400" />
            </div>
            <Input
              value={group.name}
              onChange={(e) => handleUpdateGroup(group.id, 'name', e.target.value, 'TARGET')}
              className="bg-transparent border-none text-white font-medium text-base p-0 h-auto focus:ring-0 max-w-[250px]"
            />
            {/* Logical Operator */}
            <Select
              value={group.logical_operator || 'OR'}
              onValueChange={(v) => handleUpdateGroup(group.id, 'logical_operator', v, 'TARGET')}
            >
              <SelectTrigger className="w-[70px] bg-gray-800/60 border-gray-700 text-xs h-7 mx-2">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="AND">AND</SelectItem>
                <SelectItem value="OR">OR</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center gap-2">
            <Button 
                onClick={() => handleAddTargetToGroup(group.id)} 
                variant="outline" 
                size="sm" 
                className="border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/10 hover:text-emerald-300 h-8"
              >
                <Plus className="h-3.5 w-3.5 mr-1.5" />
                Add Rule
            </Button>
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={() => handleDeleteGroup(group.id, 'TARGET')}
              className="text-gray-500 hover:text-emerald-400 hover:bg-emerald-500/10 h-8 w-8 p-0"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4 pt-4">
        {(!group.target_rules || group.target_rules.length === 0) ? (
          <div className="text-center py-6 border border-dashed border-gray-700/60 rounded-lg">
             <p className="text-gray-500 text-sm">No target rules in this group</p>
          </div>
        ) : (
          <div className="space-y-2">
            {group.target_rules.map((tgt, index) => (
              <div key={tgt.id} className="flex flex-wrap items-center gap-2 p-2 bg-gray-800/40 rounded-lg border border-gray-700/40 hover:border-gray-700 transition-colors">
                <span className="text-xs font-mono text-gray-500 w-6 text-center shrink-0">{index + 1}</span>
                
                {/* Type Selection */}
                <Select 
                  value={tgt.target_type} 
                  onValueChange={(v) => handleUpdateNestedRule(group.id, tgt.id, 'target_type', v, 'TARGET')}
                >
                  <SelectTrigger className="w-[200px] bg-gray-800/60 border-gray-700 text-xs h-8">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {(enums.TargetType || []).map(t => (
                      <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                {/* Primary Value Input */}
                {['FIXED_POINTS', 'FIXED_PERCENTAGE', 'RISK_REWARD', 'TRAILING_POINTS', 'TRAILING_PERCENTAGE'].includes(tgt.target_type) && (
                  <div className="flex items-center gap-1.5 px-1 border-l border-gray-700/50">
                    <Input
                      type="number" step="0.1"
                      value={(() => {
                        const field = tgt.target_type === 'RISK_REWARD' 
                          ? 'risk_reward_ratio' 
                          : tgt.target_type?.includes('PERCENTAGE') && !tgt.target_type?.includes('TRAILING')
                            ? 'fixed_percentage' 
                            : tgt.target_type?.includes('POINTS')
                              ? 'fixed_points'
                              : tgt.target_type?.includes('TRAILING')
                                ? 'trailing_value'
                                : 'fixed_points';
                        return tgt[field] != null ? tgt[field] : '';
                      })()}
                      onChange={(e) => {
                        let field = null;
                        if (tgt.target_type === 'RISK_REWARD') field = 'risk_reward_ratio';
                        else if (tgt.target_type?.includes('PERCENTAGE') && !tgt.target_type?.includes('TRAILING')) field = 'fixed_percentage';
                        else if (tgt.target_type?.includes('POINTS')) field = 'fixed_points';
                        else if (tgt.target_type?.includes('TRAILING')) field = 'trailing_value';
                        
                        const val = e.target.value === '' ? '' : parseFloat(e.target.value);
                        if (field) handleUpdateNestedRule(group.id, tgt.id, field, val, 'TARGET');
                      }}
                      className="w-24 bg-gray-800/60 border-gray-700 text-white h-8 text-xs text-center"
                    />
                    <span className="text-[10px] text-gray-500 uppercase">
                      {tgt.target_type === 'RISK_REWARD' ? 'R:R' : tgt.target_type?.includes('PERCENTAGE') ? '%' : 'Pts'}
                    </span>
                  </div>
                )}

                {/* Time Based */}
                {tgt.target_type === 'TIME_BASED' && (
                  <div className="flex items-center gap-1.5 px-1 border-l border-gray-700/50">
                    <span className="text-[10px] text-gray-500">Wait</span>
                    <Input
                      type="number"
                      value={tgt.time_exit_minutes ?? ''}
                      onChange={(e) => {
                        const val = e.target.value === '' ? '' : parseInt(e.target.value);
                        handleUpdateNestedRule(group.id, tgt.id, 'time_exit_minutes', val, 'TARGET');
                      }}
                      className="w-24 bg-gray-800/60 border-gray-700 text-white h-8 text-xs text-center"
                    />
                    <span className="text-[10px] text-gray-500 uppercase">Mins</span>
                  </div>
                )}

                {/* EOD Squareoff */}
                {tgt.target_type === 'EOD' && (
                  <div className="flex items-center gap-1.5 px-1 border-l border-gray-700/50">
                    <span className="text-[10px] text-gray-500">At</span>
                    <Input
                      type="time"
                      value={tgt.eod_squareoff_time || '15:15'}
                      onChange={(e) => handleUpdateNestedRule(group.id, tgt.id, 'eod_squareoff_time', e.target.value, 'TARGET')}
                      className="w-24 bg-gray-800/60 border-gray-700 text-white h-8 text-xs px-2"
                    />
                  </div>
                )}

                {/* Expiry */}
                {tgt.target_type === 'EXPIRY' && (
                  <div className="flex items-center gap-1.5 px-1 border-l border-gray-700/50">
                    <Input
                      type="number"
                      value={tgt.expiry_exit_minutes_before ?? ''}
                      onChange={(e) => {
                        const val = e.target.value === '' ? '' : parseInt(e.target.value);
                        handleUpdateNestedRule(group.id, tgt.id, 'expiry_exit_minutes_before', val, 'TARGET');
                      }}
                      className="w-24 bg-gray-800/60 border-gray-700 text-white h-8 text-xs text-center"
                    />
                    <span className="text-[10px] text-gray-500">mins pre-expiry</span>
                  </div>
                )}

                {/* Indicator Based */}
                {tgt.target_type === 'INDICATOR_BASED' && (
                  <div className="flex items-center gap-1.5 bg-gray-900/40 p-1 px-2 rounded-md border border-gray-700/30 flex-wrap">
                    <Select 
                      value={tgt.indicator_type || 'RSI'} 
                      onValueChange={(v) => handleUpdateNestedRule(group.id, tgt.id, 'indicator_type', v, 'TARGET')}
                    >
                      <SelectTrigger className="w-[160px] bg-gray-800/60 border-gray-700 text-[10px] h-7">
                        <SelectValue placeholder="Indicator" />
                      </SelectTrigger>
                      <SelectContent>
                        {(enums.IndicatorType || []).map(ind => (
                          <SelectItem key={ind.value} value={ind.value}>{ind.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    
                    {tgt.indicator_type && renderIndicatorParams(
                      tgt.indicator_type, 
                      tgt.indicator_params, 
                      (newParams) => handleUpdateNestedRule(group.id, tgt.id, 'indicator_params', newParams, 'TARGET'),
                      true
                    )}

                    {/* Timeframe Override for indicators */}
                    <Select 
                      value={tgt.timeframe_override || 'NONE'} 
                      onValueChange={(v) => handleUpdateNestedRule(group.id, tgt.id, 'timeframe_override', v === 'NONE' ? '' : v, 'TARGET')}
                    >
                      <SelectTrigger className="w-[120px] bg-gray-800/60 border-gray-700 text-[10px] h-7">
                        <SelectValue placeholder="TF Override" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="NONE">Default</SelectItem>
                        {(enums.CandleTimeframe || []).map(tf => (
                          <SelectItem key={tf.value} value={tf.value}>{tf.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>

                    <div className="flex items-center gap-1.5 border-l border-gray-700/50 pl-1.5">
                      <Select 
                        value={tgt.operator || 'GT'} 
                        onValueChange={(v) => handleUpdateNestedRule(group.id, tgt.id, 'operator', v, 'TARGET')}
                      >
                        <SelectTrigger className="w-[80px] bg-gray-800/60 border-gray-700 text-[10px] h-7">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {(enums.ComparisonOperator || []).map(op => (
                            <SelectItem key={op.value} value={op.value}>{op.label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>

                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => {
                            if (tgt.compare_to_indicator) {
                              handleUpdateNestedRuleFields(group.id, tgt.id, { compare_to_indicator: null, compare_to_params: null }, 'TARGET');
                            } else {
                              handleUpdateNestedRuleFields(group.id, tgt.id, { compare_to_indicator: 'SMA', threshold_value: null }, 'TARGET');
                            }
                          }}
                          className={`h-7 w-7 rounded flex items-center justify-center transition-colors border ${
                            tgt.compare_to_indicator ? 'bg-indigo-500/20 border-indigo-500/30 text-indigo-400' : 'bg-gray-800/40 border-gray-700 text-gray-500'
                          }`}
                          title="Compare Indicator vs Value/Indicator"
                        >
                          {tgt.compare_to_indicator ? <Activity className="h-3 w-3" /> : <span className="text-[9px] font-bold">123</span>}
                        </button>



                        {tgt.compare_to_indicator ? (
                          <div className="flex items-center gap-1">
                            <Select 
                              value={tgt.compare_to_indicator} 
                              onValueChange={(v) => handleUpdateNestedRule(group.id, tgt.id, 'compare_to_indicator', v, 'TARGET')}
                            >
                              <SelectTrigger className="w-[120px] bg-gray-800/60 border-gray-700 text-[10px] h-7">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                {(enums.IndicatorType || []).map(ind => (
                                  <SelectItem key={ind.value} value={ind.value}>{ind.label}</SelectItem>
                                ))}
                              </SelectContent>
                            </Select>

                            {/* Secondary indicator params */}
                            {tgt.compare_to_indicator && renderIndicatorParams(
                              tgt.compare_to_indicator,
                              tgt.compare_to_params,
                              (newParams) => handleUpdateNestedRule(group.id, tgt.id, 'compare_to_params', newParams, 'TARGET'),
                              true
                            )}
                          </div>
                        ) : (
                          <Input
                            type="number"
                            value={tgt.threshold_value ?? ''}
                            onChange={(e) => {
                              const val = e.target.value === '' ? '' : parseFloat(e.target.value);
                              handleUpdateNestedRule(group.id, tgt.id, 'threshold_value', val, 'TARGET');
                            }}
                            className="w-20 bg-gray-800/60 border-gray-700 text-white h-7 text-[10px] text-center"
                            placeholder="Min"
                          />
                        )}

                        {tgt.operator === 'BETWEEN' && !tgt.compare_to_indicator && (
                          <div className="flex items-center gap-1">
                             <span className="text-[10px] text-gray-400">to</span>
                             <Input
                              type="number"
                              value={tgt.threshold_value2 ?? ''}
                              onChange={(e) => {
                                const val = e.target.value === '' ? '' : parseFloat(e.target.value);
                                handleUpdateNestedRule(group.id, tgt.id, 'threshold_value2', val, 'TARGET');
                              }}
                              className="w-20 bg-gray-800/60 border-gray-700 text-white h-7 text-[10px] text-center"
                              placeholder="Max"
                            />
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                <div className="flex-1" />

                <div className="flex items-center gap-2 pr-1">
                  <Switch 
                    checked={tgt.is_active} 
                    onCheckedChange={(v) => handleUpdateNestedRule(group.id, tgt.id, 'is_active', v, 'TARGET')}
                    className="scale-75"
                  />
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    onClick={() => handleDeleteNestedRule(group.id, tgt.id, 'TARGET')}
                    className="text-gray-500 hover:text-emerald-400 h-7 w-7 p-0"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );

  if (loading) {
    return (
      <div className="flex flex-col justify-center items-center h-96 gap-3">
        <Loader2 className="h-8 w-8 text-rose-400 animate-spin" />
        <p className="text-sm text-gray-400">Loading exit rules...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col flex-1 min-h-0">
      <div className="flex-1 overflow-y-auto scrollbar-theme">
        <div className="container-padding py-6 lg:py-8 space-y-8">

          {/* ── Stop Loss Section ── */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-rose-500/10">
                  <TrendingDown className="h-5 w-5 text-rose-400" />
                </div>
                <div>
                  <h2 className="text-base font-semibold text-white">Stop Loss Rules</h2>
                  <p className="text-xs text-gray-500">Define stop loss groups and conditions</p>
                </div>
              </div>
              <Button 
                onClick={() => handleAddGroup('STOP_LOSS')} 
                variant="outline"
                className="border-rose-500/30 text-rose-400 hover:bg-rose-500/10 hover:text-rose-300"
                size="sm"
              >
                <Plus className="h-3.5 w-3.5 mr-1.5" />
                Add Group
              </Button>
            </div>

            {slGroups.length === 0 ? (
              <Card className="bg-gray-900/40 border-gray-800/80 border-dashed">
                <CardContent className="py-10 text-center">
                  <Shield className="h-10 w-10 text-gray-600 mx-auto mb-3" />
                  <p className="text-gray-400 text-sm font-medium">No stop loss groups defined</p>
                  <Button onClick={() => handleAddGroup('STOP_LOSS')} variant="link" className="text-rose-400">
                    Create First Group
                  </Button>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-6">
                {slGroups.map((group, index) => (
                  <div key={group.id}>
                    {index > 0 && (
                      <div className="flex items-center justify-center py-2 pb-4">
                        <div className="h-px w-12 bg-gray-700" />
                        <button
                          onClick={() => handleExitConfigUpdate('stop_loss_group_operator', (exitConfig?.stop_loss_group_operator === 'AND' ? 'OR' : 'AND'))}
                          className={`mx-3 px-3 py-1 rounded-full text-xs font-semibold border transition-all duration-200 cursor-pointer hover:scale-105 ${
                            exitConfig?.stop_loss_group_operator === 'AND'
                              ? 'bg-amber-600/20 text-amber-400 border-amber-500/30 hover:bg-amber-600/30'
                              : 'bg-indigo-600/20 text-indigo-400 border-indigo-500/30 hover:bg-indigo-600/30'
                          }`}
                          title="Click to toggle between AND / OR logic between groups"
                        >
                          {exitConfig?.stop_loss_group_operator || 'OR'}
                        </button>
                        <div className="h-px w-12 bg-gray-700" />
                      </div>
                    )}
                    {renderStopLossGroup(group)}
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="space-y-4 pt-6 border-t border-gray-800">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-emerald-500/10">
                  <Target className="h-5 w-5 text-emerald-400" />
                </div>
                <div>
                  <h2 className="text-base font-semibold text-white">Target Rules</h2>
                  <p className="text-xs text-gray-500">Define target/exit groups and conditions</p>
                </div>
              </div>
              <Button 
                onClick={() => handleAddGroup('TARGET')} 
                variant="outline"
                className="border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/10 hover:text-emerald-300"
                size="sm"
              >
                <Plus className="h-3.5 w-3.5 mr-1.5" />
                Add Group
              </Button>
            </div>

            {targetGroups.length === 0 ? (
              <Card className="bg-gray-900/40 border-gray-800/80 border-dashed">
                <CardContent className="py-10 text-center">
                  <Target className="h-10 w-10 text-gray-600 mx-auto mb-3" />
                  <p className="text-gray-400 text-sm font-medium">No target groups defined</p>
                  <Button onClick={() => handleAddGroup('TARGET')} variant="link" className="text-emerald-400">
                    Create First Group
                  </Button>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-6">
                {targetGroups.map((group, index) => (
                  <div key={group.id}>
                    {index > 0 && (
                      <div className="flex items-center justify-center py-2 pb-4">
                        <div className="h-px w-12 bg-gray-700" />
                        <button
                          onClick={() => handleExitConfigUpdate('target_group_operator', (exitConfig?.target_group_operator === 'AND' ? 'OR' : 'AND'))}
                          className={`mx-3 px-3 py-1 rounded-full text-xs font-semibold border transition-all duration-200 cursor-pointer hover:scale-105 ${
                            exitConfig?.target_group_operator === 'AND'
                              ? 'bg-amber-600/20 text-amber-400 border-amber-500/30 hover:bg-amber-600/30'
                              : 'bg-indigo-600/20 text-indigo-400 border-indigo-500/30 hover:bg-indigo-600/30'
                          }`}
                          title="Click to toggle between AND / OR logic between groups"
                        >
                          {exitConfig?.target_group_operator || 'OR'}
                        </button>
                        <div className="h-px w-12 bg-gray-700" />
                      </div>
                    )}
                    {renderTargetGroup(group)}
                  </div>
                ))}
              </div>
            )}
          </div>

        </div>
      </div>
      <StrategyFooter
        onSave={handleSaveAll}
        onCancel={handleCancelAll}
        saving={saving}
        disabled={!hasPendingChanges}
        saveLabel="Save Changes"
      />
    </div>
  );
}

