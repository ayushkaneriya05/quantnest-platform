import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select";
import { Switch } from "@/shared/components/ui/switch";
import { Trash2 } from "lucide-react";
import { useEnums } from "@/shared/context/EnumsContext";
import OperandSelector from "./OperandSelector";

export default function RuleConditionEditor({
  rule,
  logicalOperator,
  showOperator = false,
  ruleType,
  theme,
  deleteTitle,
  onChange,
  onDelete,
}) {
  const { enums } = useEnums();

  const updateOperand = (side, field, value) => {
    onChange(`operand_${side}_${field}`, value);
  };

  return (
    <div className="space-y-2">
      {showOperator && (
        <div className="flex items-center justify-center -my-1 relative z-10">
          <div className="absolute bg-[#0a0e17] px-2 py-0.5 rounded-full text-[10px] font-bold tracking-widest text-gray-500 border border-gray-800 shadow-sm">
            {logicalOperator || "AND"}
          </div>
        </div>
      )}

      <div
        className={`group relative rounded-xl bg-white/[0.02] border border-white/[0.05] hover:border-white/[0.1] hover:bg-white/[0.04] transition-all duration-300 shadow-sm overflow-hidden ${
          (rule.is_active ?? true) ? "" : "opacity-60"
        }`}
      >
        <div
          className={`absolute left-0 top-0 bottom-0 w-[2px] ${theme.accentBar} transition-colors`}
        />

        <div className="flex flex-wrap items-center gap-2 p-3 pl-4">
          <Badge
            variant="secondary"
            className={`${theme.badge} border-none text-[10px] px-2 py-0.5 font-bold tracking-wider mr-1`}
          >
            IF
          </Badge>

          <OperandSelector
            value={rule.operand_a_type}
            params={rule.operand_a_params}
            timeframe={rule.operand_a_timeframe}
            onChangeType={(value) => updateOperand("a", "type", value)}
            onChangeParams={(value) => updateOperand("a", "params", value)}
            onChangeTimeframe={(value) => updateOperand("a", "timeframe", value)}
            placeholder="Select Data"
            ruleType={ruleType}
          />

          <div className="flex items-center bg-black/20 rounded-lg p-0.5 border border-white/[0.05]">
            <Select
              value={rule.comparison || "GT"}
              onValueChange={(value) => onChange("comparison", value)}
            >
              <SelectTrigger
                className={`w-auto bg-transparent border-none hover:bg-white/5 text-xs h-7 px-2.5 shadow-none focus:ring-0 ${theme.comparison} font-semibold`}
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(enums.ComparisonOperator || []).map((operator) => (
                  <SelectItem key={operator.value} value={operator.value}>
                    {operator.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <OperandSelector
            value={rule.operand_b_type}
            params={rule.operand_b_params}
            timeframe={rule.operand_b_timeframe}
            onChangeType={(value) => updateOperand("b", "type", value)}
            onChangeParams={(value) => updateOperand("b", "params", value)}
            onChangeTimeframe={(value) => updateOperand("b", "timeframe", value)}
            placeholder="Compare To"
            ruleType={ruleType}
          />
        </div>

        <div className="flex items-center justify-end gap-4 px-4 pb-2 pt-1 opacity-100">
          <Switch
            checked={rule.is_active ?? true}
            onCheckedChange={(value) => onChange("is_active", value)}
            className={`scale-75 ${theme.switch} data-[state=unchecked]:bg-gray-600`}
          />
          <Button
            variant="ghost"
            size="sm"
            onClick={onDelete}
            className="text-gray-500 hover:text-rose-400 hover:bg-rose-500/10 h-6 w-6 p-0 rounded-md"
            title={deleteTitle}
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>
    </div>
  );
}
