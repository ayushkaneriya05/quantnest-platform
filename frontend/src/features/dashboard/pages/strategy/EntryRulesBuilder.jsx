/**
 * Entry Rules Builder - visual rule builder for entry conditions
 */
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader } from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import { Badge } from "@/shared/components/ui/badge";
import { Input } from "@/shared/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/components/ui/select";
import { Switch } from "@/shared/components/ui/switch";
import { Plus, Trash2, GripVertical, Target } from 'lucide-react';
import StrategyConfigNav from './StrategyConfigNav';
import StrategyFooter from './StrategyFooter';
import { ruleGroupApi, ruleApi } from '@/shared/services/rulesApi';
import { strategyApi, entryConfigApi } from '@/shared/services/strategyApi';
import { useNotifications } from '@/shared/hooks/useNotifications';
import { customConfirm } from '@/shared/components/ui/custom-dialog';
import { usePageActions } from '@/shared/context/PageActionsContext';
import { useEnums } from '@/shared/context/EnumsContext';
import { GlobalLoader } from '@/shared/components/ui/global-loader';
import OperandSelector, { getDefaultParams } from './components/OperandSelector';

export default function EntryRulesBuilder() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { notify } = useNotifications();
  const { enums } = useEnums();
  const { setPageHeader, setPageActions } = usePageActions();
  
  const [strategy, setStrategy] = useState(null);
  const [ruleGroups, setRuleGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [interGroupOperator, setInterGroupOperator] = useState('OR');
  const [entrySide, setEntrySide] = useState('BUY');
  
  const [pendingEdits, setPendingEdits] = useState({
    rules: {},
    groups: {},
    entryConfig: null
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

  useEffect(() => {
    setPageHeader(<StrategyConfigNav strategy={strategy} />);
    return () => setPageHeader(null);
  }, [strategy, setPageHeader]);

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
      setRuleGroups(groups || []);
      setPendingEdits({ rules: {}, groups: {}, entryConfig: null });
      if (strategyData?.entry_order_config) {
        if (strategyData.entry_order_config.entry_group_operator) {
          setInterGroupOperator(strategyData.entry_order_config.entry_group_operator);
        }
        if (strategyData.entry_order_config.entry_side) {
          setEntrySide(strategyData.entry_order_config.entry_side);
        }
      } else {
        try {
          const newConfig = await entryConfigApi.create({ strategy: id });
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
    setInterGroupOperator(newOp);
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
      const defaultTypeA = 'RSI';
      const defaultParamsA = getDefaultParams(defaultTypeA);
      
      const defaultTypeB = 'CONSTANT';
      const defaultParamsB = { value: 30 };

      const newRule = await ruleApi.create({
        rule_group: groupId,
        operand_a_type: defaultTypeA,
        operand_a_params: defaultParamsA,
        comparison: 'GT',
        operand_b_type: defaultTypeB,
        operand_b_params: defaultParamsB,
        is_active: true
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
    setRuleGroups(ruleGroups.map(g => 
      g.id === groupId 
        ? { 
            ...g, 
            rules: g.rules.map(r => r.id === ruleId ? { ...r, ...updates } : r) 
          }
        : g
    ));

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
    
    // When changing operand type, reset its params
    if (field === 'operand_a_type') {
      updates.operand_a_params = getDefaultParams(value);
    }
    if (field === 'operand_b_type') {
      updates.operand_b_params = getDefaultParams(value);
    }

    handleUpdateRuleFields(groupId, ruleId, updates);
  };

  const handleUpdateGroup = async (groupId, field, value) => {
    setRuleGroups(ruleGroups.map(g => 
      g.id === groupId ? { ...g, [field]: value } : g
    ));

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

      Object.entries(pendingEdits.rules).forEach(([id, updates]) => {
        promises.push(ruleApi.update(id, updates));
      });

      Object.entries(pendingEdits.groups).forEach(([id, updates]) => {
        promises.push(ruleGroupApi.update(id, updates));
      });

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
        <GlobalLoader />
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
                
                <CardContent className="space-y-3 z-10 relative">
                  {(group.rules || []).length === 0 ? (
                    <div className="text-center py-6 border border-dashed border-gray-700/60 rounded-lg">
                      <p className="text-gray-500 text-sm mb-2">No conditions in this group</p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      <div className="space-y-2">
                        {(group.rules || []).map((rule, ruleIndex) => (
                          <div key={rule.id} className="space-y-2">
                            {ruleIndex > 0 && (
                              <div className="flex items-center justify-center -my-1 relative z-10">
                                <div className="absolute bg-[#0a0e17] px-2 py-0.5 rounded-full text-[10px] font-bold tracking-widest text-gray-500 border border-gray-800 shadow-sm">
                                  {group.logical_operator || 'AND'}
                                </div>
                              </div>
                            )}

                            <div className={`group relative rounded-xl bg-white/[0.02] border border-white/[0.05] hover:border-white/[0.1] hover:bg-white/[0.04] transition-all duration-300 shadow-sm overflow-hidden ${(rule.is_active ?? true) ? '' : 'opacity-60'}`}>
                              <div className="absolute left-0 top-0 bottom-0 w-[2px] bg-emerald-500/30 group-hover:bg-emerald-500/60 transition-colors" />

                              {/* Rule Sentence Builder */}
                              <div className="flex flex-wrap items-center gap-2 p-3 pl-4">
                                <Badge variant="secondary" className="bg-emerald-500/10 text-emerald-400 border-none text-[10px] px-2 py-0.5 font-bold tracking-wider mr-1">IF</Badge>
                                
                                {/* Operand A */}
                                <OperandSelector 
                                  value={rule.operand_a_type}
                                  params={rule.operand_a_params}
                                  timeframe={rule.operand_a_timeframe}
                                  onChangeType={(v) => handleUpdateRule(group.id, rule.id, 'operand_a_type', v)}
                                  onChangeParams={(v) => handleUpdateRule(group.id, rule.id, 'operand_a_params', v)}
                                  onChangeTimeframe={(v) => handleUpdateRule(group.id, rule.id, 'operand_a_timeframe', v)}
                                  placeholder="Select Data"
                                />

                                {/* Comparison */}
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

                                {/* Operand B */}
                                <OperandSelector 
                                  value={rule.operand_b_type}
                                  params={rule.operand_b_params}
                                  timeframe={rule.operand_b_timeframe}
                                  onChangeType={(v) => handleUpdateRule(group.id, rule.id, 'operand_b_type', v)}
                                  onChangeParams={(v) => handleUpdateRule(group.id, rule.id, 'operand_b_params', v)}
                                  onChangeTimeframe={(v) => handleUpdateRule(group.id, rule.id, 'operand_b_timeframe', v)}
                                  placeholder="Compare To"
                                />
                                
                              </div>

                              <div className="flex items-center justify-end gap-4 px-4 pb-2 pt-1 opacity-100">
                                <div className="flex items-center gap-1.5">
                                  <Switch 
                                    checked={rule.is_active ?? true} 
                                    onCheckedChange={(v) => handleUpdateRule(group.id, rule.id, 'is_active', v)}
                                    className="scale-75 data-[state=checked]:bg-emerald-500 data-[state=unchecked]:bg-gray-600"
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
