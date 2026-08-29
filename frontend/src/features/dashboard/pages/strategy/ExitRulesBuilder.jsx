/**
 * Exit Rules Builder - unified rules configuration for Stop Loss, Target, and General Exits
 */
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader } from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import { Badge } from "@/shared/components/ui/badge";
import { Input } from "@/shared/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/components/ui/select";
import { Switch } from "@/shared/components/ui/switch";
import { Plus, Trash2, GripVertical, Shield, Target, LogOut } from 'lucide-react';
import StrategyConfigNav from './StrategyConfigNav';
import StrategyFooter from './StrategyFooter';
import { ruleGroupApi, ruleApi } from '@/shared/services/rulesApi';
import { strategyApi, exitConfigApi } from '@/shared/services/strategyApi';
import { useNotifications } from '@/shared/hooks/useNotifications';
import { customConfirm } from '@/shared/components/ui/custom-dialog';
import { useEnums } from '@/shared/context/EnumsContext';
import { usePageActions } from '@/shared/context/PageActionsContext';
import { GlobalLoader } from '@/shared/components/ui/global-loader';
import OperandSelector, { getDefaultParams } from './components/OperandSelector';

export default function ExitRulesBuilder() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { notify } = useNotifications();
  const { enums } = useEnums();
  const { setPageHeader } = usePageActions();
  
  const [strategy, setStrategy] = useState(null);
  
  const [slGroups, setSlGroups] = useState([]);
  const [targetGroups, setTargetGroups] = useState([]);
  const [exitGroups, setExitGroups] = useState([]);
  
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  
  const [pendingEdits, setPendingEdits] = useState({
    rules: {},
    groups: {},
    exitConfig: null
  });

  const hasPendingChanges = 
    Object.keys(pendingEdits.rules).length > 0 || 
    Object.keys(pendingEdits.groups).length > 0 || 
    pendingEdits.exitConfig !== null;

  useEffect(() => {
    if (id) fetchData();
  }, [id]);

  useEffect(() => {
    setPageHeader(<StrategyConfigNav strategy={strategy} />);
    return () => setPageHeader(null);
  }, [strategy, setPageHeader]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [strategyData, slGroupData, tgtGroupData, exitGroupData] = await Promise.all([
        strategyApi.getById(id),
        ruleGroupApi.getByStrategy(id, 'STOP_LOSS'),
        ruleGroupApi.getByStrategy(id, 'TARGET'),
        ruleGroupApi.getByStrategy(id, 'EXIT')
      ]);
      setStrategy(strategyData);
      
      setSlGroups(slGroupData || []);
      setTargetGroups(tgtGroupData || []);
      setExitGroups(exitGroupData || []);
      
      setPendingEdits({ rules: {}, groups: {}, exitConfig: null });

      if (!strategyData?.exit_order_config) {
        try {
          const newConfig = await exitConfigApi.create({ strategy: id });
          strategyData.exit_order_config = newConfig;
          setStrategy({ ...strategyData });
        } catch (err) {
          console.error("Failed to create missing exit config", err);
        }
      }

    } catch (error) {
      notify.error('Failed to load exit rules');
    } finally {
      setLoading(false);
    }
  };

  const getGroupState = (type) => {
    if (type === 'STOP_LOSS') return [slGroups, setSlGroups];
    if (type === 'TARGET') return [targetGroups, setTargetGroups];
    return [exitGroups, setExitGroups];
  };

  const handleAddGroup = async (type) => {
    try {
      const [groups, setGroups] = getGroupState(type);
      let namePrefix = 'Exit';
      if (type === 'STOP_LOSS') namePrefix = 'Stop Loss';
      else if (type === 'TARGET') namePrefix = 'Target';

      const newGroup = await ruleGroupApi.create({
        strategy: id,
        name: `${namePrefix} Group ${groups.length + 1}`,
        rule_type: type,
        logical_operator: 'OR',
        priority: groups.length + 1,
      });
      
      setGroups([...groups, { ...newGroup, rules: [] }]);
      notify.success('Group added');
    } catch (error) {
      notify.error('Failed to add group');
    }
  };

  const handleDeleteGroup = async (groupId, type) => {
    if (!(await customConfirm('Delete this group and all its rules?'))) return;
    try {
      const [groups, setGroups] = getGroupState(type);
      await ruleGroupApi.delete(groupId);
      setGroups(groups.filter(g => g.id !== groupId));
      notify.success('Group deleted');
    } catch (error) {
      notify.error('Failed to delete group');
    }
  };

  const handleUpdateGroup = async (groupId, field, value, type) => {
    const [groups, setGroups] = getGroupState(type);
    setGroups(groups.map(g => g.id === groupId ? { ...g, [field]: value } : g));
    setPendingEdits(prev => ({
      ...prev,
      groups: {
        ...prev.groups,
        [groupId]: { ...(prev.groups[groupId] || {}), [field]: value }
      }
    }));
  };

  const handleAddRule = async (groupId, type) => {
    try {
      const [groups, setGroups] = getGroupState(type);
      
      let defaultTypeA = 'POSITION_PNL_PERCENTAGE';
      let defaultTypeB = 'CONSTANT';
      
      const newRule = await ruleApi.create({
        rule_group: groupId,
        operand_a_type: defaultTypeA,
        operand_a_params: getDefaultParams(defaultTypeA),
        comparison: type === 'STOP_LOSS' ? 'LT' : 'GT',
        operand_b_type: defaultTypeB,
        operand_b_params: { value: type === 'STOP_LOSS' ? -1.0 : 2.0 },
        is_active: true
      });
      
      setGroups(groups.map(g => 
        g.id === groupId 
          ? { ...g, rules: [...(g.rules || []), newRule] } 
          : g
      ));
      notify.success('Rule added');
    } catch (error) {
      notify.error('Failed to add rule');
    }
  };

  const handleDeleteRule = async (groupId, ruleId, type) => {
    try {
      const [groups, setGroups] = getGroupState(type);
      await ruleApi.delete(ruleId);
      setGroups(groups.map(g => {
        if (g.id !== groupId) return g;
        return { ...g, rules: (g.rules || []).filter(r => r.id !== ruleId) };
      }));
      notify.success('Rule deleted');
    } catch (error) {
      notify.error('Failed to delete rule');
    }
  };

  const handleUpdateRule = (groupId, ruleId, field, value, type) => {
    const [groups, setGroups] = getGroupState(type);
    
    let updates = { [field]: value };
    if (field === 'operand_a_type') {
      updates.operand_a_params = getDefaultParams(value);
    }
    if (field === 'operand_b_type') {
      updates.operand_b_params = getDefaultParams(value);
    }

    setGroups(groups.map(g => {
      if (g.id !== groupId) return g;
      return {
        ...g,
        rules: (g.rules || []).map(r => r.id === ruleId ? { ...r, ...updates } : r)
      };
    }));

    setPendingEdits(prev => ({
      ...prev,
      rules: {
        ...prev.rules,
        [ruleId]: { ...(prev.rules[ruleId] || {}), ...updates }
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

      if (pendingEdits.exitConfig && strategy?.exit_order_config?.id) {
        promises.push(exitConfigApi.update(strategy.exit_order_config.id, pendingEdits.exitConfig));
      }

      await Promise.all(promises);
      setPendingEdits({ rules: {}, groups: {}, exitConfig: null });
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

  const renderGroupList = (title, type, groups, Icon, colorClass, borderClass, bgClass, switchClass) => (
    <div className="space-y-4 mb-10">
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${bgClass}`}>
            <Icon className={`h-5 w-5 ${colorClass}`} />
          </div>
          <div>
            <h2 className="text-base font-semibold text-white">{title}</h2>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button 
            onClick={() => handleAddGroup(type)} 
            variant="outline"
            className={`border-${colorClass.split('-')[1]}-500/30 ${colorClass} hover:${bgClass} hover:${colorClass.replace('400', '300')}`}
            size="sm"
          >
            <Plus className="h-3.5 w-3.5 mr-1.5" />
            Add Group
          </Button>
        </div>
      </div>
      
      {groups.length === 0 ? (
        <Card className="bg-gray-900/40 border-gray-800/80 border-dashed">
          <CardContent className="py-8 text-center">
            <p className="text-gray-500 text-sm">No {title.toLowerCase()} defined</p>
          </CardContent>
        </Card>
      ) : (
        groups.map((group, groupIndex) => (
          <div key={group.id}>
            {groupIndex > 0 && (
              <div className="flex items-center justify-center py-2">
                <div className="h-px w-12 bg-gray-700" />
                <div className={`mx-3 px-3 py-1 rounded-full text-[10px] font-bold border bg-gray-800/50 text-gray-400 border-gray-700`}>
                  OR
                </div>
                <div className="h-px w-12 bg-gray-700" />
              </div>
            )}
            
            <Card className={`bg-[#0a0e17] border-t border-t-${colorClass.split('-')[1]}-500/20 border-gray-800/80 shadow-2xl relative overflow-hidden`}>
              <div className={`absolute top-0 left-1/4 w-1/2 h-px bg-gradient-to-r from-transparent via-${colorClass.split('-')[1]}-500/20 to-transparent`} />
              <CardHeader className="pb-3 z-10 relative">
                  <div className="flex items-center justify-between w-full">
                    <div className="flex flex-col gap-2">
                      <div className="flex items-center gap-3">
                        <div className={`p-1.5 rounded-md ${bgClass}`}>
                          <GripVertical className={`h-4 w-4 ${colorClass} opacity-50 cursor-grab`} />
                        </div>
                        <Input
                          value={group.name}
                          onChange={(e) => handleUpdateGroup(group.id, 'name', e.target.value, type)}
                          className="bg-transparent border-none text-white font-medium text-sm p-0 h-auto focus:ring-0 w-[200px]"
                        />
                      </div>
                      
                      <div className="flex items-center gap-2 pl-9">
                        <span className="text-[11px] text-gray-500 font-medium uppercase tracking-wider">On Trigger:</span>
                        <Select 
                          value={group.action || 'EXIT_ALL'} 
                          onValueChange={(v) => handleUpdateGroup(group.id, 'action', v, type)}
                        >
                          <SelectTrigger className="w-auto min-w-[140px] bg-white/5 border-none hover:bg-white/10 text-xs h-7 shadow-none focus:ring-0 text-gray-300">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="EXIT_ALL">Exit Full Position</SelectItem>
                            <SelectItem value="PARTIAL_EXIT">Take Partial Profit</SelectItem>
                            <SelectItem value="MOVE_TO_BREAKEVEN">Move SL to Breakeven</SelectItem>
                          </SelectContent>
                        </Select>
                        {group.action === 'PARTIAL_EXIT' && (
                          <div className="flex items-center gap-1.5">
                            <span className="text-[11px] text-gray-500 font-medium">Exit %:</span>
                            <Input
                              type="number"
                              min="1"
                              max="99"
                              value={group.action_params?.exit_pct || ''}
                              onChange={(e) => handleUpdateGroup(group.id, 'action_params', { ...group.action_params, exit_pct: e.target.value }, type)}
                              className="bg-white/5 border-none text-white text-xs h-7 w-16 focus:ring-0"
                              placeholder="e.g. 50"
                            />
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2 self-start mt-1">
                    <Select 
                      value={group.logical_operator} 
                      onValueChange={(v) => handleUpdateGroup(group.id, 'logical_operator', v, type)}
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
                      onClick={() => handleAddRule(group.id, type)} 
                      variant="outline" 
                      size="sm" 
                      className={`${bgClass} border-none ${colorClass} hover:bg-opacity-20 h-8`}
                    >
                      <Plus className="h-3.5 w-3.5 mr-1.5" />
                      Add Rule
                    </Button>
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      onClick={() => handleDeleteGroup(group.id, type)}
                      className="text-gray-500 hover:text-rose-400 hover:bg-rose-500/10 h-8 w-8 p-0"
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
                            <div className={`absolute left-0 top-0 bottom-0 w-[2px] bg-${colorClass.split('-')[1]}-500/30 group-hover:bg-${colorClass.split('-')[1]}-500/60 transition-colors`} />

                            <div className="flex flex-wrap items-center gap-2 p-3 pl-4">
                              <Badge variant="secondary" className={`${bgClass} ${colorClass} border-none text-[10px] px-2 py-0.5 font-bold tracking-wider mr-1`}>IF</Badge>
                              
                              <OperandSelector 
                                value={rule.operand_a_type}
                                params={rule.operand_a_params}
                                timeframe={rule.operand_a_timeframe}
                                onChangeType={(v) => handleUpdateRule(group.id, rule.id, 'operand_a_type', v, type)}
                                onChangeParams={(v) => handleUpdateRule(group.id, rule.id, 'operand_a_params', v, type)}
                                onChangeTimeframe={(v) => handleUpdateRule(group.id, rule.id, 'operand_a_timeframe', v, type)}
                                placeholder="Select Data"
                                ruleType={type}
                              />

                              <div className="flex items-center bg-black/20 rounded-lg p-0.5 border border-white/[0.05]">
                                <Select 
                                  value={rule.comparison || 'GT'} 
                                  onValueChange={(v) => handleUpdateRule(group.id, rule.id, 'comparison', v, type)}
                                >
                                  <SelectTrigger className={`w-auto bg-transparent border-none hover:bg-white/5 text-xs h-7 px-2.5 shadow-none focus:ring-0 ${colorClass} font-semibold`}>
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

                              <OperandSelector 
                                value={rule.operand_b_type}
                                params={rule.operand_b_params}
                                timeframe={rule.operand_b_timeframe}
                                onChangeType={(v) => handleUpdateRule(group.id, rule.id, 'operand_b_type', v, type)}
                                onChangeParams={(v) => handleUpdateRule(group.id, rule.id, 'operand_b_params', v, type)}
                                onChangeTimeframe={(v) => handleUpdateRule(group.id, rule.id, 'operand_b_timeframe', v, type)}
                                placeholder="Compare To"
                                ruleType={type}
                              />
                            </div>

                            <div className="flex items-center justify-end gap-4 px-4 pb-2 pt-1 opacity-100">
                              <div className="flex items-center gap-1.5">
                                <Switch 
                                  checked={rule.is_active ?? true} 
                                  onCheckedChange={(v) => handleUpdateRule(group.id, rule.id, 'is_active', v, type)}
                                  className={`scale-75 ${switchClass} data-[state=unchecked]:bg-gray-600`}
                                />
                              </div>
                              <Button 
                                variant="ghost" 
                                size="sm" 
                                onClick={() => handleDeleteRule(group.id, rule.id, type)}
                                className="text-gray-500 hover:text-rose-400 hover:bg-rose-500/10 h-6 w-6 p-0 rounded-md"
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
        ))
      )}
    </div>
  );

  if (loading) {
    return (
      <div className="flex flex-col justify-center items-center h-96 gap-3">
        <GlobalLoader />
        <p className="text-sm text-gray-400">Loading exit rules...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col flex-1 min-h-0">
      <div className="flex-1 overflow-y-auto scrollbar-theme">
        <div className="container-padding py-6 lg:py-8">
          
          {renderGroupList("Stop Loss", "STOP_LOSS", slGroups, Shield, "text-rose-400", "border-rose-500/30", "bg-rose-500/10", "data-[state=checked]:bg-rose-500")}
          
          {renderGroupList("Target", "TARGET", targetGroups, Target, "text-emerald-400", "border-emerald-500/30", "bg-emerald-500/10", "data-[state=checked]:bg-emerald-500")}

          {renderGroupList("General Exits", "EXIT", exitGroups, LogOut, "text-indigo-400", "border-indigo-500/30", "bg-indigo-500/10", "data-[state=checked]:bg-indigo-500")}

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
