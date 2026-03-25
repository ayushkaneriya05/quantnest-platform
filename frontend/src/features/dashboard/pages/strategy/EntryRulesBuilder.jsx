/**
 * Entry Rules Builder - visual rule builder for entry conditions
 */
import { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import { Badge } from "@/shared/components/ui/badge";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/components/ui/select";
import { Switch } from "@/shared/components/ui/switch";
import { 
  Plus, Trash2, ChevronLeft, Save, GripVertical,
  TrendingUp, Activity, BarChart2, Zap, Target,
  Loader2, Sparkles
} from 'lucide-react';
import StrategyConfigNav from './StrategyConfigNav';
import StrategyFooter from './StrategyFooter';
import { ruleGroupApi, ruleApi } from '@/shared/services/rulesApi';
import { strategyApi, entryConfigApi } from '@/shared/services/strategyApi';
import { useNotifications } from '@/shared/hooks/useNotifications';
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
    if (!confirm('Delete this rule group and all its rules?')) return;
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

  const handleCancelAll = () => {
    if (hasPendingChanges && confirm('Discard all unsaved changes?')) {
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

              <Card className="bg-gray-900/40 border-gray-800/80">
                <CardHeader className="pb-3">
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
                        <SelectTrigger className="w-[90px] bg-gray-800/60 border-gray-700 text-sm h-8">
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
                        className="border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/10 hover:text-emerald-300 h-8"
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


                <CardContent className="space-y-3">
                  {/* Rules */}
                  {(group.rules || []).length === 0 ? (
                    <div className="text-center py-6 border border-dashed border-gray-700/60 rounded-lg">
                      <p className="text-gray-500 text-sm mb-2">No conditions in this group</p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      <div className="space-y-2">
                        {(group.rules || []).map((rule, ruleIndex) => (
                          <div key={rule.id}>
                            <div className="flex items-center gap-2.5 p-3 bg-gray-800/40 rounded-lg border border-gray-700/40 hover:border-gray-700 transition-colors">
                              <span className="text-xs font-mono text-gray-500 w-5 text-center shrink-0">
                                {ruleIndex + 1}
                              </span>
                              
                              {/* Category Select (Indicator, Price Action, Volume) */}
                               <Select 
                                 value={rule.category || 'INDICATOR'} 
                                 onValueChange={(v) => handleUpdateRule(group.id, rule.id, 'category', v)}
                               >
                                 <SelectTrigger className="w-[110px] bg-gray-800/60 border-gray-700 text-xs h-8">
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
                                  {/* Indicator Type */}
                                  <Select 
                                    value={rule.indicator_type || ''} 
                                    onValueChange={(v) => handleUpdateRule(group.id, rule.id, 'indicator_type', v)}
                                  >
                                    <SelectTrigger className="w-[130px] bg-gray-800/60 border-gray-700 text-sm h-8">
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
                              {rule.indicator_type && (
                                <div className="flex items-center gap-1.5">
                                  {(() => {
                                    // Common parameter definitions
                                    // PARAM_CONFIG is now defined at top of file

                                    const params = PARAM_CONFIG[rule.indicator_type] || [];
                                    
                                    return params.map(param => (
                                      <div key={param.key} className="flex items-center">
                                        <Input
                                          type="number"
                                          title={param.label}
                                          placeholder={param.label}
                                          value={rule.params?.[param.key] ?? param.default}
                                          onChange={(e) => {
                                            const val = parseFloat(e.target.value);
                                            const newParams = { 
                                              ...(rule.params || {}), 
                                              [param.key]: isNaN(val) ? param.default : val 
                                            };
                                            handleUpdateRule(group.id, rule.id, 'params', newParams);
                                          }}
                                          className="w-20 bg-gray-800/60 border-gray-700 text-xs h-8 text-center px-1"
                                        />
                                      </div>
                                    ));
                                  })()}
                                </div>
                              )}

                              {/* Timeframe Override */}
                              <Select 
                                value={rule.timeframe_override || 'NONE'} 
                                onValueChange={(v) => handleUpdateRule(group.id, rule.id, 'timeframe_override', v === 'NONE' ? '' : v)}
                              >
                                <SelectTrigger className="w-[90px] bg-gray-800/60 border-gray-700 text-[10px] h-8">
                                  <SelectValue placeholder="TF" />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="NONE">Default</SelectItem>
                                  {(enums.CandleTimeframe || []).map(tf => (
                                    <SelectItem key={tf.value} value={tf.value}>{tf.label}</SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>

                              {/* Comparison Logic */}
                              <Select 
                                value={rule.comparison || 'GT'} 
                                onValueChange={(v) => handleUpdateRule(group.id, rule.id, 'comparison', v)}
                              >
                                <SelectTrigger className="w-[140px] bg-gray-800/60 border-gray-700 text-sm h-8 px-2">
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

                              {/* Value OR Compare to Indicator */}
                              <div className="flex items-center gap-2">
                                {/* Toggle between Value / Indicator */}
                                <button
                                  onClick={() => handleUpdateRule(group.id, rule.id, 'compare_to_indicator', rule.compare_to_indicator ? null : 'SMA')}
                                  className={`h-6 w-6 rounded flex items-center justify-center transition-colors ${
                                    rule.compare_to_indicator 
                                      ? 'bg-indigo-500/20 text-indigo-400 hover:bg-indigo-500/30' 
                                      : 'bg-gray-700/50 text-gray-400 hover:text-gray-300'
                                  }`}
                                  title={rule.compare_to_indicator ? "Switch to fixed value" : "Compare to another indicator"}
                                >
                                  {rule.compare_to_indicator ? <Activity className="h-3 w-3" /> : <span className="text-xs font-mono">123</span>}
                                </button>

                                {rule.compare_to_indicator ? (
                                    <div className="flex items-center gap-1.5">
                                      <Select 
                                        value={rule.compare_to_indicator} 
                                        onValueChange={(v) => handleUpdateRule(group.id, rule.id, 'compare_to_indicator', v)}
                                      >
                                        <SelectTrigger className="w-[160px] bg-gray-800/60 border-gray-700 text-sm h-8">
                                          <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                          {(enums.IndicatorType || []).map(ind => (
                                            <SelectItem key={ind.value} value={ind.value}>{ind.label}</SelectItem>
                                          ))}
                                        </SelectContent>
                                      </Select>
                                      
                                      {/* Secondary Indicator Params */}
                                      {(() => {
                                        // Reusing the same PARAM_CONFIG structure for secondary indicator
                                        // PARAM_CONFIG is now defined at top of file

                                        const params = PARAM_CONFIG[rule.compare_to_indicator] || [];
                                        
                                        return params.map(param => (
                                          <Input
                                            key={param.key}
                                            type="number"
                                            title={param.label}
                                            placeholder={param.label}
                                            value={rule.compare_to_params?.[param.key] ?? param.default}
                                            onChange={(e) => {
                                              const val = parseFloat(e.target.value);
                                              const newParams = { 
                                                ...(rule.compare_to_params || {}), 
                                                [param.key]: isNaN(val) ? param.default : val 
                                              };
                                              handleUpdateRule(group.id, rule.id, 'compare_to_params', newParams);
                                            }}
                                            className="w-20 bg-gray-800/60 border-gray-700 text-xs h-8 text-center px-1"
                                          />
                                        ));
                                      })()}
                                    </div>
                                ) : (
                                  <Input
                                    type="number"
                                    value={rule.value != null ? rule.value : ''}
                                    onChange={(e) => {
                                      const val = parseFloat(e.target.value);
                                      handleUpdateRule(group.id, rule.id, 'value', isNaN(val) ? null : val);
                                    }}
                                    className="w-28 bg-gray-800/60 border-gray-700 text-sm h-8 text-center"
                                    placeholder="Value"
                                  />
                                )}
                              </div>


                            {/* Value 2 (for BETWEEN) */}
                            {rule.comparison === 'BETWEEN' && (
                              <>
                                <span className="text-gray-500 text-xs">and</span>
                                <Input
                                  type="number"
                                  value={rule.value2 != null ? rule.value2 : ''}
                                  onChange={(e) => {
                                    const val = parseFloat(e.target.value);
                                    handleUpdateRule(group.id, rule.id, 'value2', isNaN(val) ? null : val);
                                  }}
                                  className="w-28 bg-gray-800/60 border-gray-700 text-sm h-8 text-center"
                                  placeholder="Max"
                                />
                              </>
                            )}
                              </>
                            )}

                            {/* ── PRICE ACTION RULES ── */}
                            {rule.category === 'PRICE_ACTION' && (
                              <Select 
                                value={rule.price_action_type || ''} 
                                onValueChange={(v) => handleUpdateRule(group.id, rule.id, 'price_action_type', v)}
                              >
                                <SelectTrigger className="w-[240px] bg-gray-800/60 border-gray-700 text-sm h-8">
                                  <SelectValue placeholder="Select Pattern" />
                                </SelectTrigger>
                                <SelectContent>
                                  {(enums.PriceActionType || []).map(pat => (
                                    <SelectItem key={pat.value} value={pat.value}>{pat.label}</SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            )}

                            {/* ── VOLUME RULES ── */}
                            {rule.category === 'VOLUME' && (
                              <Select 
                                value={rule.volume_condition_type || ''} 
                                onValueChange={(v) => handleUpdateRule(group.id, rule.id, 'volume_condition_type', v)}
                              >
                                <SelectTrigger className="w-[200px] bg-gray-800/60 border-gray-700 text-sm h-8">
                                  <SelectValue placeholder="Select Volume Condition" />
                                </SelectTrigger>
                                <SelectContent>
                                  {(enums.VolumeConditionType || []).map(vol => (
                                    <SelectItem key={vol.value} value={vol.value}>{vol.label}</SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            )}

                              <div className="flex-1" />

                              <div className="flex items-center gap-2">
                                <Switch 
                                  checked={rule.is_active ?? true} 
                                  onCheckedChange={(v) => handleUpdateRule(group.id, rule.id, 'is_active', v)}
                                  className="scale-75"
                                  title="Enable/Disable Rule"
                                />
                                <Button 
                                  variant="ghost" 
                                  size="sm" 
                                  onClick={() => handleDeleteRule(group.id, rule.id)}
                                  className="text-gray-500 hover:text-rose-400 hover:bg-rose-500/10 h-7 w-7 p-0"
                                >
                                  <Trash2 className="h-3.5 w-3.5" />
                                </Button>
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
