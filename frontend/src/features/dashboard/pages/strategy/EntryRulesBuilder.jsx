/**
 * Entry Rules Builder - visual rule builder for entry conditions
 */
import { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import { Badge } from "@/shared/components/ui/badge";
import { Input } from "@/shared/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/components/ui/select";
import { Switch } from "@/shared/components/ui/switch";
import { Plus, Trash2, GripVertical, Activity, Target, Loader2} from 'lucide-react';
import StrategyConfigNav from './StrategyConfigNav';
import StrategyFooter from './StrategyFooter';
import { ruleGroupApi, ruleApi } from '@/shared/services/rulesApi';
import { strategyApi, entryConfigApi } from '@/shared/services/strategyApi';
import { useNotifications } from '@/shared/hooks/useNotifications';
import { customConfirm } from '@/shared/components/ui/custom-dialog';
import { usePageActions } from '@/shared/context/PageActionsContext'; // Changed import
import { useEnums } from '@/shared/context/EnumsContext';


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

export default function EntryRulesBuilder() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { notify } = useNotifications();
  const { enums } = useEnums();
  const { setPageHeader, setPageActions } = usePageActions(); // Use context directly
  
  const [strategy, setStrategy] = useState(null);
  const [ruleGroups, setRuleGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [interGroupOperator, setInterGroupOperator] = useState('OR');
  const [entrySide, setEntrySide] = useState('BUY');
  
  const [pendingEdits, setPendingEdits] = useState({
    rules: {}, // ruleId -> {updates}
    groups: {}, // groupId -> {updates}
    entryConfig: null // {updates}
  });

  const hasPendingChanges = 
    Object.keys(pendingEdits.rules).length > 0 || 
    Object.keys(pendingEdits.groups).length > 0 || 
    pendingEdits.entryConfig !== null;

  useEffect(() => {
    if (id) {
      fetchData();
    }
  }, [id]);

  // Set Navigation in Header
  useEffect(() => {
    setPageHeader(<StrategyConfigNav strategy={strategy} />);
    return () => setPageHeader(null);
  }, [strategy, setPageHeader]);

  // Clear actions on mount/unmount since we moved the button to content
  useEffect(() => {
    setPageActions(null);
    return () => setPageActions(null);
  }, [setPageActions]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [strategyData, groups] = await Promise.all([
        strategyApi.getById(id),
        ruleGroupApi.getByStrategy(id, 'ENTRY')
      ]);
      setStrategy(strategyData);
      setRuleGroups(groups);
      setPendingEdits({ rules: {}, groups: {}, entryConfig: null });
      // Set initial operator from config
      if (strategyData?.entry_order_config) {
        if (strategyData.entry_order_config.entry_group_operator) {
          setInterGroupOperator(strategyData.entry_order_config.entry_group_operator);
        }
        if (strategyData.entry_order_config.entry_side) {
          setEntrySide(strategyData.entry_order_config.entry_side);
        }
      } else {
        // Missing config? Create it now.
        try {
          const newConfig = await entryConfigApi.create({ strategy: id });
          // Mutate strategy object to include new config so subsequent saves work
          strategyData.entry_order_config = newConfig;
          setStrategy({ ...strategyData });
        } catch (err) {
          console.error("Failed to create missing entry config", err);
        }
      }
    } catch (error) {
      notify.error('Failed to load entry rules');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateInterGroupOperator = async () => {
    const newOp = interGroupOperator === 'OR' ? 'AND' : 'OR';
    // Local update
    setInterGroupOperator(newOp);
    
    // Record for manual save
    setPendingEdits(prev => ({
      ...prev,
      entryConfig: { ...(prev.entryConfig || {}), entry_group_operator: newOp }
    }));
  };

  const handleUpdateEntrySide = (v) => {
    setEntrySide(v);
    setPendingEdits(prev => ({
      ...prev,
      entryConfig: { ...(prev.entryConfig || {}), entry_side: v }
    }));
  };

  const handleAddGroup = async () => {
    try {
      const newGroup = await ruleGroupApi.create({
        strategy: id,
        name: `Entry Group ${ruleGroups.length + 1}`,
        rule_type: 'ENTRY',
        logical_operator: 'AND',
        priority: ruleGroups.length + 1,
      });
      setRuleGroups([...ruleGroups, { ...newGroup, rules: [] }]);
      notify.success('Rule group added');
    } catch (error) {
      notify.error('Failed to add rule group');
    }
  };
  
  const handleDeleteGroup = async (groupId) => {
    if (!(await customConfirm('Delete this rule group and all its rules?'))) return;
    try {
      await ruleGroupApi.delete(groupId);
      setRuleGroups(ruleGroups.filter(g => g.id !== groupId));
      notify.success('Rule group deleted');
    } catch (error) {
      notify.error('Failed to delete rule group');
    }
  };

  const handleAddRule = async (groupId) => {
    try {
      const defaultType = 'RSI';
      const defaultParams = getDefaultParams(defaultType); // Explicit defaults

      const newRule = await ruleApi.create({
        rule_group: groupId,
        category: 'INDICATOR',
        indicator_type: defaultType,
        params: defaultParams,
        comparison: 'GT',
        value: 30,
        compare_to_indicator: null,
      });
      setRuleGroups(ruleGroups.map(g => 
        g.id === groupId 
          ? { ...g, rules: [...(g.rules || []), newRule] }
          : g
      ));
      notify.success('Rule added');
    } catch (error) {
      notify.error('Failed to add rule');
    }
  };

  const handleDeleteRule = async (groupId, ruleId) => {
    try {
      await ruleApi.delete(ruleId);
      setRuleGroups(ruleGroups.map(g => 
        g.id === groupId 
          ? { ...g, rules: g.rules.filter(r => r.id !== ruleId) }
          : g
      ));
      notify.success('Rule deleted');
    } catch (error) {
      notify.error('Failed to delete rule');
    }
  };

  const handleUpdateRuleFields = (groupId, ruleId, updates) => {
    // Local update
    setRuleGroups(ruleGroups.map(g => 
      g.id === groupId 
        ? { 
            ...g, 
            rules: g.rules.map(r => r.id === ruleId ? { ...r, ...updates } : r) 
          }
        : g
    ));

    // Record for manual save
    setPendingEdits(prev => ({
      ...prev,
      rules: {
        ...prev.rules,
        [ruleId]: { ...(prev.rules[ruleId] || {}), ...updates }
      }
    }));
  };

  const handleUpdateRule = (groupId, ruleId, field, value) => {
    let updates = { [field]: value };

    // Logic for cleanup and explicit defaults
    if (field === 'category') {
      // Reset incompatible fields
      updates = {
        category: value,
        indicator_type: null,
        params: null,
        price_action_type: null,
        volume_condition_type: null,
        // comparison is non-nullable in model, relying on default
        comparison: 'GT',
        value: null,
        compare_to_indicator: null,
        compare_to_params: null
      };

      if (value === 'INDICATOR') {
        const defaultType = 'SMA';
        updates.indicator_type = defaultType;
        updates.params = getDefaultParams(defaultType);
        updates.comparison = 'GT';
        updates.value = 0;
      }
    } else if (field === 'indicator_type') {
      // Set new defaults and clear old value
      updates.params = getDefaultParams(value);
      updates.value = null; // Clear threshold value as it likely doesn't apply to new indicator
      updates.compare_to_indicator = null; // Reset comparison target
      updates.compare_to_params = null;
    } else if (field === 'compare_to_indicator') {
        if (value) {
            // If switching TO an indicator comparison
            updates.compare_to_params = getDefaultParams(value);
            updates.value = null; // Clear fixed value
        } else {
            // Switching back to fixed value
            updates.compare_to_params = null;
            updates.value = 0; // Set a default fixed value
        }
    } else if (field === 'comparison') {
        if (value !== 'BETWEEN') {
            updates.value2 = null;
        }
    }

    handleUpdateRuleFields(groupId, ruleId, updates);
  };

  const handleUpdateGroup = async (groupId, field, value) => {
    // Local Update
    setRuleGroups(ruleGroups.map(g => 
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

  const handleSaveAll = async () => {
    if (!hasPendingChanges) return;
    
    try {
      setSaving(true);
      const promises = [];

      // Save Rules
      Object.entries(pendingEdits.rules).forEach(([id, updates]) => {
        promises.push(ruleApi.update(id, updates));
      });

      // Save Groups
      Object.entries(pendingEdits.groups).forEach(([id, updates]) => {
        promises.push(ruleGroupApi.update(id, updates));
      });

      // Save Entry Config
      if (pendingEdits.entryConfig && strategy?.entry_order_config?.id) {
        promises.push(entryConfigApi.update(strategy.entry_order_config.id, pendingEdits.entryConfig));
      }

      await Promise.all(promises);
      setPendingEdits({ rules: {}, groups: {}, entryConfig: null });
      notify.success('All changes saved');
    } catch (error) {
      console.error(error);
      notify.error('Failed to save some changes');
    } finally {
      setSaving(false);
    }
  };

  const handleCancelAll = async () => {
    if (hasPendingChanges && (await customConfirm('Discard all unsaved changes?'))) {
      fetchData();
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col justify-center items-center h-96 gap-3">
        <Loader2 className="h-8 w-8 text-emerald-400 animate-spin" />
        <p className="text-sm text-gray-400">Loading entry rules...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col flex-1 min-h-0">
      <div className="flex-1 overflow-y-auto scrollbar-theme">
      <div className="container-padding py-6 lg:py-8 space-y-6">

      {/* Rule Groups */}
      {ruleGroups.length === 0 ? (
        <Card className="bg-gray-900/40 border-gray-800/80 border-dashed">
          <CardContent className="py-10 text-center">
            <Target className="h-10 w-10 text-gray-600 mx-auto mb-3" />
            <p className="text-gray-400 text-sm font-medium">No entry rules defined</p>
            <Button onClick={handleAddGroup} variant="link" className="text-emerald-400">
              Create First Group
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-emerald-500/10">
                <Target className="h-5 w-5 text-emerald-400" />
              </div>
              <div>
                <h2 className="text-base font-semibold text-white">Entry Rules</h2>
                <p className="text-xs text-gray-500">Define entry conditions for the strategy</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Select
                value={entrySide}
                onValueChange={handleUpdateEntrySide}
              >
                <SelectTrigger className={`w-[110px] border text-sm h-9 font-semibold ${
                  entrySide === 'BUY'
                    ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                    : 'bg-rose-500/10 border-rose-500/30 text-rose-400'
                }`}>
                  <span className="flex items-center">
                    <span className={`inline-block h-2 w-2 rounded-full shrink-0 mr-2 ${
                      entrySide === 'BUY' ? 'bg-emerald-400' : 'bg-rose-400'
                    }`} />
                    {entrySide === 'BUY' ? 'Long' : 'Short'}
                  </span>
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="BUY">
                    <span className="flex items-center gap-2">
                      <span className="inline-block h-2 w-2 rounded-full bg-emerald-400" />
                      Long (Buy)
                    </span>
                  </SelectItem>
                  <SelectItem value="SELL">
                    <span className="flex items-center gap-2">
                      <span className="inline-block h-2 w-2 rounded-full bg-rose-400" />
                      Short (Sell)
                    </span>
                  </SelectItem>
                </SelectContent>
              </Select>
              <Button 
                onClick={handleAddGroup} 
                variant="outline"
                className="border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/10 hover:text-emerald-300"
                size="sm"
              >
                <Plus className="h-3.5 w-3.5 mr-1.5" />
                Add Group
              </Button>
            </div>
          </div>
          {ruleGroups.map((group, groupIndex) => (
            <div key={group.id}>
              {/* AND/OR connector between groups */}
              {groupIndex > 0 && (
                <div className="flex items-center justify-center py-2">
                  <div className="h-px w-12 bg-gray-700" />
                  <button
                    onClick={handleUpdateInterGroupOperator}
                    className={`mx-3 px-3 py-1 rounded-full text-xs font-semibold border transition-all duration-200 cursor-pointer hover:scale-105 ${
                      interGroupOperator === 'AND'
                        ? 'bg-amber-600/20 text-amber-400 border-amber-500/30 hover:bg-amber-600/30'
                        : 'bg-indigo-600/20 text-indigo-400 border-indigo-500/30 hover:bg-indigo-600/30'
                    }`}
                    title="Click to toggle between AND / OR logic between groups"
                  >
                    {interGroupOperator}
                  </button>
                  <div className="h-px w-12 bg-gray-700" />
                </div>
              )}

              <Card className="bg-[#0a0e17] border-t border-t-emerald-500/20 border-gray-800/80 shadow-2xl relative overflow-hidden">
                {/* Subtle gradient blob inside card */}
                <div className="absolute top-0 left-1/4 w-1/2 h-px bg-gradient-to-r from-transparent via-emerald-500/20 to-transparent" />
                <CardHeader className="pb-3 z-10 relative">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="p-1.5 rounded-md bg-emerald-500/10">
                        <GripVertical className="h-4 w-4 text-emerald-500/50 cursor-grab" />
                      </div>
                      <Input
                        value={group.name}
                        onChange={(e) => handleUpdateGroup(group.id, 'name', e.target.value)}
                        className="bg-transparent border-none text-white font-medium text-sm p-0 h-auto focus:ring-0 w-[200px]"
                      />
                    </div>
                    <div className="flex items-center gap-2">
                      <Select 
                        value={group.logical_operator} 
                        onValueChange={(v) => handleUpdateGroup(group.id, 'logical_operator', v)}
                      >
                        <SelectTrigger className="w-[90px] bg-white/5 border-none hover:bg-white/10 text-sm h-8 shadow-none focus:ring-0">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {(enums.LogicalOperator || []).map(op => (
                            <SelectItem key={op.value} value={op.value}>{op.label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <Button 
                        onClick={() => handleAddRule(group.id)} 
                        variant="outline" 
                        size="sm" 
                        className="bg-emerald-500/10 border-none text-emerald-400 hover:bg-emerald-500/20 hover:text-emerald-300 h-8"
                      >
                        <Plus className="h-3.5 w-3.5 mr-1.5" />
                        Add Rule
                      </Button>
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        onClick={() => handleDeleteGroup(group.id)}
                        className="text-gray-500 hover:text-rose-400 hover:bg-rose-500/10 h-8 w-8 p-0"
                        title="Delete group"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                
                {/* Advanced group settings */}


                <CardContent className="space-y-3 z-10 relative">
                  {/* Rules */}
                  {(group.rules || []).length === 0 ? (
                    <div className="text-center py-6 border border-dashed border-gray-700/60 rounded-lg">
                      <p className="text-gray-500 text-sm mb-2">No conditions in this group</p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      <div className="space-y-2">
                        {(group.rules || []).map((rule, ruleIndex) => (
                          <div key={rule.id} className="space-y-2">
                            {/* AND/OR connector between rules within group */}
                            {ruleIndex > 0 && (
                              <div className="flex items-center justify-center -my-1 relative z-10">
                                <div className="absolute bg-[#0a0e17] px-2 py-0.5 rounded-full text-[10px] font-bold tracking-widest text-gray-500 border border-gray-800 shadow-sm">
                                  {group.logical_operator || 'AND'}
                                </div>
                              </div>
                            )}

                            {/* Rule Card */}
                            <div className={`group relative rounded-xl bg-white/[0.02] border border-white/[0.05] hover:border-white/[0.1] hover:bg-white/[0.04] transition-all duration-300 shadow-sm overflow-hidden ${(rule.is_active ?? true) ? '' : 'opacity-60'}`}>
                              
                              {/* Soft glowing left edge */}
                              <div className="absolute left-0 top-0 bottom-0 w-[2px] bg-emerald-500/30 group-hover:bg-emerald-500/60 transition-colors" />

                              {/* Row 1: Main rule sentence */}
                              <div className="flex flex-wrap items-center gap-1.5 p-3 pl-4">
                                <Badge variant="secondary" className="bg-emerald-500/10 text-emerald-400 border-none text-[10px] px-2 py-0.5 font-bold tracking-wider mr-1">IF</Badge>
                                
                                {/* Category Select */}
                                <Select 
                                  value={rule.category || 'INDICATOR'} 
                                  onValueChange={(v) => handleUpdateRule(group.id, rule.id, 'category', v)}
                                >
                                  <SelectTrigger className="w-auto bg-transparent border-none hover:bg-white/5 data-[state=open]:bg-white/10 text-xs h-7 px-2 shadow-none focus:ring-0 text-gray-300 font-medium">
                                    <SelectValue />
                                  </SelectTrigger>
                                  <SelectContent>
                                    {(enums.RuleCategory || []).map(cat => (
                                      <SelectItem key={cat.value} value={cat.value}>{cat.label}</SelectItem>
                                    ))}
                                  </SelectContent>
                                </Select>

                                {/* ── INDICATOR RULES ── */}
                                {rule.category === 'INDICATOR' && (
                                  <>
                                    <div className="flex items-center bg-black/20 rounded-lg p-0.5 border border-white/[0.05]">
                                      <Select 
                                        value={rule.indicator_type || ''} 
                                        onValueChange={(v) => handleUpdateRule(group.id, rule.id, 'indicator_type', v)}
                                      >
                                        <SelectTrigger className="w-auto min-w-[120px] bg-transparent border-none hover:bg-white/5 text-xs h-7 px-2.5 shadow-none focus:ring-0 text-indigo-300 font-semibold">
                                          <SelectValue placeholder="Indicator" />
                                        </SelectTrigger>
                                        <SelectContent>
                                          {(enums.IndicatorType || []).map(ind => (
                                            <SelectItem key={ind.value} value={ind.value}>
                                              {ind.label}
                                            </SelectItem>
                                          ))}
                                        </SelectContent>
                                      </Select>

                                      {/* Dynamic Indicator Params */}
                                      {rule.indicator_type && (() => {
                                        const params = PARAM_CONFIG[rule.indicator_type] || [];
                                        if (params.length === 0) return null;
                                        return (
                                          <div className="flex items-center gap-1 px-2 border-l border-white/[0.05]">
                                            {params.map(param => (
                                              <div key={param.key} className="flex items-center gap-1">
                                                <span className="text-[9px] text-gray-500 uppercase font-medium">{param.label}:</span>
                                                <Input
                                                  type="number"
                                                  value={rule.params?.[param.key] ?? param.default}
                                                  onChange={(e) => {
                                                    const val = parseFloat(e.target.value);
                                                    const newParams = { 
                                                      ...(rule.params || {}), 
                                                      [param.key]: isNaN(val) ? '' : val 
                                                    };
                                                    handleUpdateRule(group.id, rule.id, 'params', newParams);
                                                  }}
                                                  className="w-10 bg-transparent border-none text-xs h-5 text-center px-0 shadow-none focus-visible:ring-1 focus-visible:ring-indigo-500/50 p-0 m-0 text-gray-300 font-medium"
                                                />
                                              </div>
                                            ))}
                                          </div>
                                        );
                                      })()}
                                    </div>

                                    <Badge variant="secondary" className="bg-gray-500/10 text-gray-400 border-none text-[10px] px-2 py-0.5 font-bold tracking-wider mx-1">IS</Badge>

                                    <div className="flex items-center bg-black/20 rounded-lg p-0.5 border border-white/[0.05]">
                                      <Select 
                                        value={rule.comparison || 'GT'} 
                                        onValueChange={(v) => handleUpdateRule(group.id, rule.id, 'comparison', v)}
                                      >
                                        <SelectTrigger className="w-auto bg-transparent border-none hover:bg-white/5 text-xs h-7 px-2.5 shadow-none focus:ring-0 text-emerald-300 font-semibold">
                                          <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                          {(enums.ComparisonOperator || []).map(comp => (
                                            <SelectItem key={comp.value} value={comp.value}>
                                              {comp.label}
                                            </SelectItem>
                                          ))}
                                        </SelectContent>
                                      </Select>
                                    </div>

                                    {/* Toggle between Value / Indicator */}
                                    <div className="flex items-center ml-1">
                                      <div className="inline-flex rounded-full border border-white/[0.05] bg-black/20 p-0.5 shadow-inner">
                                        <button
                                          onClick={() => {
                                            if (rule.compare_to_indicator) {
                                              handleUpdateRule(group.id, rule.id, 'compare_to_indicator', null);
                                            }
                                          }}
                                          title="Compare to Value"
                                          className={`px-2.5 py-1 text-[10px] uppercase tracking-wide font-bold rounded-full transition-all duration-200 ${
                                            !rule.compare_to_indicator
                                              ? 'bg-gray-700/80 text-white shadow-sm'
                                              : 'text-gray-500 hover:text-gray-300 hover:bg-white/5'
                                          }`}
                                        >
                                          Val
                                        </button>
                                        <button
                                          onClick={() => {
                                            if (!rule.compare_to_indicator) {
                                              handleUpdateRule(group.id, rule.id, 'compare_to_indicator', 'SMA');
                                            }
                                          }}
                                          title="Compare to Indicator"
                                          className={`px-2.5 py-1 text-[10px] uppercase tracking-wide font-bold rounded-full transition-all duration-200 flex items-center gap-1 ${
                                            rule.compare_to_indicator
                                              ? 'bg-indigo-500/20 text-indigo-300 shadow-sm'
                                              : 'text-gray-500 hover:text-gray-300 hover:bg-white/5'
                                          }`}
                                        >
                                          <Activity className="h-3 w-3" /> Ind
                                        </button>
                                      </div>
                                    </div>

                                    {rule.compare_to_indicator ? (
                                      <div className="flex items-center bg-black/20 rounded-lg p-0.5 border border-white/[0.05] ml-1">
                                        <Select 
                                          value={rule.compare_to_indicator} 
                                          onValueChange={(v) => handleUpdateRule(group.id, rule.id, 'compare_to_indicator', v)}
                                        >
                                          <SelectTrigger className="w-auto min-w-[120px] bg-transparent border-none hover:bg-white/5 text-xs h-7 px-2.5 shadow-none focus:ring-0 text-indigo-300 font-semibold">
                                            <SelectValue />
                                          </SelectTrigger>
                                          <SelectContent>
                                            {(enums.IndicatorType || []).map(ind => (
                                              <SelectItem key={ind.value} value={ind.value}>{ind.label}</SelectItem>
                                            ))}
                                          </SelectContent>
                                        </Select>
                                        
                                        {(() => {
                                          const params = PARAM_CONFIG[rule.compare_to_indicator] || [];
                                          if (params.length === 0) return null;
                                          return (
                                            <div className="flex items-center gap-1 px-2 border-l border-white/[0.05]">
                                              {params.map(param => (
                                                <div key={param.key} className="flex items-center gap-1">
                                                  <span className="text-[9px] text-gray-500 uppercase font-medium">{param.label}:</span>
                                                  <Input
                                                    type="number"
                                                    value={rule.compare_to_params?.[param.key] ?? param.default}
                                                    onChange={(e) => {
                                                      const val = parseFloat(e.target.value);
                                                      const newParams = { 
                                                        ...(rule.compare_to_params || {}), 
                                                        [param.key]: isNaN(val) ? '' : val 
                                                      };
                                                      handleUpdateRule(group.id, rule.id, 'compare_to_params', newParams);
                                                    }}
                                                    className="w-10 bg-transparent border-none text-xs h-5 text-center px-0 shadow-none focus-visible:ring-1 focus-visible:ring-indigo-500/50 p-0 m-0 text-gray-300 font-medium"
                                                  />
                                                </div>
                                              ))}
                                            </div>
                                          );
                                        })()}
                                      </div>
                                    ) : (
                                      <div className="flex items-center bg-black/20 rounded-lg p-0.5 border border-white/[0.05] ml-1 px-2">
                                        <Input
                                          type="number"
                                          value={rule.value != null ? rule.value : ''}
                                          onChange={(e) => {
                                            const val = parseFloat(e.target.value);
                                            handleUpdateRule(group.id, rule.id, 'value', isNaN(val) ? null : val);
                                          }}
                                          className="w-16 bg-transparent border-none text-sm h-7 text-center shadow-none focus-visible:ring-0 p-0 m-0 text-white font-semibold placeholder-gray-600"
                                          placeholder="Value"
                                        />
                                      </div>
                                    )}

                                    {rule.comparison === 'BETWEEN' && (
                                      <>
                                        <span className="text-gray-500 text-[10px] uppercase font-bold tracking-wider mx-1">and</span>
                                        <div className="flex items-center bg-black/20 rounded-lg p-0.5 border border-white/[0.05] px-2">
                                          <Input
                                            type="number"
                                            value={rule.value2 != null ? rule.value2 : ''}
                                            onChange={(e) => {
                                              const val = parseFloat(e.target.value);
                                              handleUpdateRule(group.id, rule.id, 'value2', isNaN(val) ? null : val);
                                            }}
                                            className="w-16 bg-transparent border-none text-sm h-7 text-center shadow-none focus-visible:ring-0 p-0 m-0 text-white font-semibold placeholder-gray-600"
                                            placeholder="Max"
                                          />
                                        </div>
                                      </>
                                    )}
                                  </>
                                )}

                                {/* ── PRICE ACTION RULES ── */}
                                {rule.category === 'PRICE_ACTION' && (
                                  <div className="flex items-center bg-black/20 rounded-lg p-0.5 border border-white/[0.05]">
                                    <Select 
                                      value={rule.price_action_type || ''} 
                                      onValueChange={(v) => handleUpdateRule(group.id, rule.id, 'price_action_type', v)}
                                    >
                                      <SelectTrigger className="w-auto bg-transparent border-none hover:bg-white/5 text-xs h-7 px-3 shadow-none focus:ring-0 text-indigo-300 font-semibold">
                                        <SelectValue placeholder="Select Pattern" />
                                      </SelectTrigger>
                                      <SelectContent>
                                        {(enums.PriceActionType || []).map(pat => (
                                          <SelectItem key={pat.value} value={pat.value}>{pat.label}</SelectItem>
                                        ))}
                                      </SelectContent>
                                    </Select>
                                  </div>
                                )}

                                {/* ── VOLUME RULES ── */}
                                {rule.category === 'VOLUME' && (
                                  <div className="flex items-center bg-black/20 rounded-lg p-0.5 border border-white/[0.05]">
                                    <Select 
                                      value={rule.volume_condition_type || ''} 
                                      onValueChange={(v) => handleUpdateRule(group.id, rule.id, 'volume_condition_type', v)}
                                    >
                                      <SelectTrigger className="w-auto bg-transparent border-none hover:bg-white/5 text-xs h-7 px-3 shadow-none focus:ring-0 text-indigo-300 font-semibold">
                                        <SelectValue placeholder="Select Volume Condition" />
                                      </SelectTrigger>
                                      <SelectContent>
                                        {(enums.VolumeConditionType || []).map(vol => (
                                          <SelectItem key={vol.value} value={vol.value}>{vol.label}</SelectItem>
                                        ))}
                                      </SelectContent>
                                    </Select>
                                  </div>
                                )}

                                </div>

                                {/* Row 2: Metadata (Timeframe + Actions) */}
                                <div className="flex items-center gap-3 px-4 pb-2 pt-1 opacity-100">
                                  {rule.category === 'INDICATOR' && (
                                    <div className="flex items-center gap-1.5 bg-black/10 rounded-md px-2 py-0.5 border border-white/[0.02]">
                                      <span className="text-[9px] text-gray-500 font-bold tracking-widest uppercase">TF:</span>
                                      <Select 
                                        value={rule.timeframe_override || 'NONE'} 
                                        onValueChange={(v) => handleUpdateRule(group.id, rule.id, 'timeframe_override', v === 'NONE' ? '' : v)}
                                      >
                                        <SelectTrigger className="w-auto bg-transparent border-none hover:bg-white/5 text-[10px] h-5 px-1 shadow-none focus:ring-0 text-gray-400 p-0">
                                          <SelectValue placeholder="Default" />
                                        </SelectTrigger>
                                        <SelectContent>
                                          <SelectItem value="NONE">Default</SelectItem>
                                          {(enums.CandleTimeframe || []).map(tf => (
                                            <SelectItem key={tf.value} value={tf.value}>{tf.label}</SelectItem>
                                          ))}
                                        </SelectContent>
                                      </Select>
                                    </div>
                                  )}
                                  
                                  <div className="flex-1" />

                                  <div className="flex items-center gap-4">
                                    <div className="flex items-center gap-1.5">
                                      <Switch 
                                        checked={rule.is_active ?? true} 
                                        onCheckedChange={(v) => handleUpdateRule(group.id, rule.id, 'is_active', v)}
                                        className="scale-75 data-[state=checked]:bg-emerald-500"
                                      />
                                    </div>
                                    <Button 
                                      variant="ghost" 
                                      size="sm" 
                                      onClick={() => handleDeleteRule(group.id, rule.id)}
                                      className="text-gray-500 hover:text-rose-400 hover:bg-rose-500/10 h-6 w-6 p-0 rounded-md"
                                      title="Delete Rule"
                                    >
                                      <Trash2 className="h-3.5 w-3.5" />
                                    </Button>
                                  </div>
                                </div>
                              </div>
                            </div>
                          ))}
                      </div>


                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          ))}
        </div>
      )}
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
