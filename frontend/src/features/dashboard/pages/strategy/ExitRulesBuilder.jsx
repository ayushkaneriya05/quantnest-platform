/**
 * Exit Rules Builder - unified rules configuration for Stop Loss, Target, and General Exits
 */
import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader } from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select";
import {
  Plus,
  Trash2,
  GripVertical,
  Shield,
  Target,
  LogOut,
} from "lucide-react";
import StrategyConfigNav from "./StrategyConfigNav";
import StrategyFooter from "./StrategyFooter";
import { ruleGroupApi, ruleApi } from "@/shared/services/rulesApi";
import { strategyApi } from "@/shared/services/strategyApi";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { customConfirm } from "@/shared/components/ui/custom-dialog";
import { useEnums } from "@/shared/context/EnumsContext";
import { usePageActions } from "@/shared/context/PageActionsContext";
import { GlobalLoader } from "@/shared/components/ui/global-loader";
import { getDefaultParams } from "./components/operandUtils";
import RuleConditionEditor from "./components/RuleConditionEditor";

const getSaveErrorMessage = (error) => {
  const responseData = error?.response?.data;
  if (typeof responseData === "string") return responseData;
  if (responseData && typeof responseData === "object") {
    const messages = Object.values(responseData)
      .flat(Infinity)
      .filter((value) => typeof value === "string" && value.trim());
    if (messages.length) return messages.join(" ");
  }
  return error?.message || "Failed to save some changes";
};

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
  });

  const hasPendingChanges =
    Object.keys(pendingEdits.rules).length > 0 ||
    Object.keys(pendingEdits.groups).length > 0;

  useEffect(() => {
    setPageHeader(<StrategyConfigNav strategy={strategy} />);
    return () => setPageHeader(null);
  }, [strategy, setPageHeader]);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [strategyData, slGroupData, tgtGroupData, exitGroupData] =
        await Promise.all([
          strategyApi.getById(id),
          ruleGroupApi.getByStrategy(id, "STOP_LOSS"),
          ruleGroupApi.getByStrategy(id, "TARGET"),
          ruleGroupApi.getByStrategy(id, "EXIT"),
        ]);
      setStrategy(strategyData);

      setSlGroups(slGroupData || []);
      setTargetGroups(tgtGroupData || []);
      setExitGroups(exitGroupData || []);

      setPendingEdits({ rules: {}, groups: {} });
    } catch (error) {
      notify.error("Failed to load exit rules");
    } finally {
      setLoading(false);
    }
  }, [id, notify]);

  useEffect(() => {
    if (id) fetchData();
  }, [id, fetchData]);

  const getGroupState = (type) => {
    if (type === "STOP_LOSS") return [slGroups, setSlGroups];
    if (type === "TARGET") return [targetGroups, setTargetGroups];
    return [exitGroups, setExitGroups];
  };

  const handleAddGroup = async (type) => {
    try {
      const [groups, setGroups] = getGroupState(type);
      const namePrefix = {
        STOP_LOSS: "Stop Loss",
        TARGET: "Target",
        EXIT: "Exit",
      }[type];

      const newGroup = await ruleGroupApi.create({
        strategy: id,
        name: `${namePrefix} Group ${groups.length + 1}`,
        rule_type: type,
        logical_operator: "OR",
        priority: groups.length + 1,
      });

      setGroups((currentGroups) => [...currentGroups, { ...newGroup, rules: [] }]);
      notify.success("Group added");
    } catch (error) {
      notify.error("Failed to add group");
    }
  };

  const handleDeleteGroup = async (groupId, type) => {
    if (!(await customConfirm("Delete this group and all its rules?"))) return;
    try {
      const [, setGroups] = getGroupState(type);
      await ruleGroupApi.delete(groupId);
      setGroups((groups) => groups.filter((group) => group.id !== groupId));
      notify.success("Group deleted");
    } catch (error) {
      notify.error("Failed to delete group");
    }
  };

  const handleUpdateGroup = (groupId, field, value, type) => {
    const [, setGroups] = getGroupState(type);
    setGroups((groups) =>
      groups.map((group) =>
        group.id === groupId ? { ...group, [field]: value } : group,
      ),
    );
    setPendingEdits((prev) => ({
      ...prev,
      groups: {
        ...prev.groups,
        [groupId]: { ...(prev.groups[groupId] || {}), [field]: value },
      },
    }));
  };

  const handleAddRule = async (groupId, type) => {
    try {
      const [, setGroups] = getGroupState(type);

      const defaultTypeA = "POSITION_PNL_PERCENTAGE";
      const defaultTypeB = "CONSTANT";

      const newRule = await ruleApi.create({
        rule_group: groupId,
        operand_a_type: defaultTypeA,
        operand_a_params: getDefaultParams(defaultTypeA, enums.OperandParameterConfig),
        comparison: type === "STOP_LOSS" ? "LT" : "GT",
        operand_b_type: defaultTypeB,
        operand_b_params: getDefaultParams(defaultTypeB, enums.OperandParameterConfig),
        is_active: true,
      });

      setGroups(
        (groups) => groups.map((group) =>
          group.id === groupId
            ? { ...group, rules: [...(group.rules || []), newRule] }
            : group,
        ),
      );
      notify.success("Rule added");
    } catch (error) {
      notify.error("Failed to add rule");
    }
  };

  const handleDeleteRule = async (groupId, ruleId, type) => {
    try {
      const [, setGroups] = getGroupState(type);
      await ruleApi.delete(ruleId);
      setGroups(
        (groups) => groups.map((group) => {
          if (group.id !== groupId) return group;
          return {
            ...group,
            rules: (group.rules || []).filter((rule) => rule.id !== ruleId),
          };
        }),
      );
      notify.success("Rule deleted");
    } catch (error) {
      notify.error("Failed to delete rule");
    }
  };

  const handleUpdateRule = (groupId, ruleId, field, value, type) => {
    const [, setGroups] = getGroupState(type);

    const updates = { [field]: value };
    if (field === "operand_a_type") {
      updates.operand_a_params = getDefaultParams(value, enums.OperandParameterConfig);
    }
    if (field === "operand_b_type") {
      updates.operand_b_params = getDefaultParams(value, enums.OperandParameterConfig);
    }

    setGroups(
      (groups) => groups.map((group) => {
        if (group.id !== groupId) return group;
        return {
          ...group,
          rules: (group.rules || []).map((rule) =>
            rule.id === ruleId ? { ...rule, ...updates } : rule,
          ),
        };
      }),
    );

    setPendingEdits((prev) => ({
      ...prev,
      rules: {
        ...prev.rules,
        [ruleId]: { ...(prev.rules[ruleId] || {}), ...updates },
      },
    }));
  };

  const handleSaveAll = async () => {
    if (!hasPendingChanges) return;

    try {
      setSaving(true);
      const updates = [
        ...Object.entries(pendingEdits.rules).map(([ruleId, fields]) =>
          ruleApi.update(ruleId, fields),
        ),
        ...Object.entries(pendingEdits.groups).map(([groupId, fields]) =>
          ruleGroupApi.update(groupId, fields),
        ),
      ];

      await Promise.all(updates);
      setPendingEdits({ rules: {}, groups: {} });
      notify.success("All changes saved");
    } catch (error) {
      console.error(error);
      notify.error(getSaveErrorMessage(error));
    } finally {
      setSaving(false);
    }
  };

  const handleCancelAll = async () => {
    if (
      hasPendingChanges &&
      !(await customConfirm("Discard all unsaved changes?"))
    ) {
      return;
    }
    navigate("/dashboard/strategy/list");
  };

  const renderGroupList = (
    title,
    type,
    groups,
    Icon,
    colorClass,
    bgClass,
    switchClass,
  ) => (
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
            className={`border-${colorClass.split("-")[1]}-500/30 ${colorClass} hover:${bgClass} hover:${colorClass.replace("400", "300")}`}
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
            <p className="text-gray-500 text-sm">
              No {title.toLowerCase()} defined
            </p>
          </CardContent>
        </Card>
      ) : (
        groups.map((group, groupIndex) => (
          <div key={group.id}>
            {groupIndex > 0 && (
              <div className="flex items-center justify-center py-2">
                <div className="h-px w-12 bg-gray-700" />
                <div
                  className={`mx-3 px-3 py-1 rounded-full text-[10px] font-bold border bg-gray-800/50 text-gray-400 border-gray-700`}
                >
                  OR
                </div>
                <div className="h-px w-12 bg-gray-700" />
              </div>
            )}

            <Card
              className={`bg-[#0a0e17] border-t border-t-${colorClass.split("-")[1]}-500/20 border-gray-800/80 shadow-2xl relative overflow-hidden`}
            >
              <div
                className={`absolute top-0 left-1/4 w-1/2 h-px bg-gradient-to-r from-transparent via-${colorClass.split("-")[1]}-500/20 to-transparent`}
              />
              <CardHeader className="pb-3 z-10 relative">
                <div className="flex items-center justify-between w-full">
                  <div className="flex flex-col gap-2">
                    <div className="flex items-center gap-3">
                      <div className={`p-1.5 rounded-md ${bgClass}`}>
                        <GripVertical
                          className={`h-4 w-4 ${colorClass} opacity-50 cursor-grab`}
                        />
                      </div>
                      <Input
                        value={group.name}
                        onChange={(e) =>
                          handleUpdateGroup(
                            group.id,
                            "name",
                            e.target.value,
                            type,
                          )
                        }
                        className="bg-transparent border-none text-white font-medium text-sm p-0 h-auto focus:ring-0 w-[200px]"
                      />
                    </div>

                    <div className="flex items-center gap-2 pl-9">
                      <span className="text-[11px] text-gray-500 font-medium uppercase tracking-wider">
                        On Trigger:
                      </span>
                      <Select
                        value={group.action || "EXIT_ALL"}
                        onValueChange={(v) =>
                          handleUpdateGroup(group.id, "action", v, type)
                        }
                      >
                        <SelectTrigger className="w-auto min-w-[140px] bg-white/5 border-none hover:bg-white/10 text-xs h-7 shadow-none focus:ring-0 text-gray-300">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                        {(enums.RuleGroupAction || []).map((action) => (
                          <SelectItem key={action.value} value={action.value}>
                            {action.label}
                          </SelectItem>
                        ))}
                        </SelectContent>
                      </Select>
                      {group.action === "PARTIAL_EXIT" && (
                        <div className="flex items-center gap-1.5">
                          <span className="text-[11px] text-gray-500 font-medium">
                            Exit %:
                          </span>
                          <Input
                            type="number"
                            min="1"
                            max="99"
                            value={group.action_params?.exit_pct || ""}
                            onChange={(e) =>
                              handleUpdateGroup(
                                group.id,
                                "action_params",
                                {
                                  ...group.action_params,
                                  exit_pct: e.target.value,
                                },
                                type,
                              )
                            }
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
                      onValueChange={(v) =>
                        handleUpdateGroup(group.id, "logical_operator", v, type)
                      }
                    >
                      <SelectTrigger className="w-[90px] bg-white/5 border-none hover:bg-white/10 text-sm h-8 shadow-none focus:ring-0">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {(enums.LogicalOperator || []).map((op) => (
                          <SelectItem key={op.value} value={op.value}>
                            {op.label}
                          </SelectItem>
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
                    <p className="text-gray-500 text-sm mb-2">
                      No conditions in this group
                    </p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="space-y-2">
                      {(group.rules || []).map((rule, ruleIndex) => (
                        <RuleConditionEditor
                          key={rule.id}
                          rule={rule}
                          logicalOperator={group.logical_operator}
                          ruleType={type}
                          showOperator={ruleIndex > 0}
                          theme={{
                            accentBar: {
                              STOP_LOSS:
                                "bg-rose-500/30 group-hover:bg-rose-500/60",
                              TARGET:
                                "bg-emerald-500/30 group-hover:bg-emerald-500/60",
                              EXIT:
                                "bg-indigo-500/30 group-hover:bg-indigo-500/60",
                            }[type],
                            badge: `${bgClass} ${colorClass}`,
                            comparison: colorClass,
                            switch: switchClass,
                          }}
                          onChange={(field, value) =>
                            handleUpdateRule(
                              group.id,
                              rule.id,
                              field,
                              value,
                              type,
                            )
                          }
                          onDelete={() =>
                            handleDeleteRule(group.id, rule.id, type)
                          }
                        />
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
          {renderGroupList(
            "Stop Loss",
            "STOP_LOSS",
            slGroups,
            Shield,
            "text-rose-400",
            "bg-rose-500/10",
            "data-[state=checked]:bg-rose-500",
          )}

          {renderGroupList(
            "Target",
            "TARGET",
            targetGroups,
            Target,
            "text-emerald-400",
            "bg-emerald-500/10",
            "data-[state=checked]:bg-emerald-500",
          )}

          {renderGroupList(
            "General Exits",
            "EXIT",
            exitGroups,
            LogOut,
            "text-indigo-400",
            "bg-indigo-500/10",
            "data-[state=checked]:bg-indigo-500",
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
