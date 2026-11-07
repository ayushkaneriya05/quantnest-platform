import PropTypes from "prop-types";
import { useState, useEffect, useMemo } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/shared/components/ui/dialog";
import { Button } from "@/shared/components/ui/button";
import { Delete, Calculator, Check, Activity, Edit2 } from 'lucide-react';
import OperandSelector from '@/features/strategies/components/OperandSelector.jsx';
import { useStrategySpecification } from "@/shared/context/EnumsContext";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger, OverflowTooltip } from '@/shared/components/ui/tooltip';

export default function MathExpressionBuilder({
  value,
  onChange,
  allowedVariableTypes = [],
  ruleType,
}) {
  const { defaultParams, operators } = useStrategySpecification();
  // Parse initial value into tokens
  const initialTokens = useMemo(() => {
    if (!value || !value.expression) return [];
    const parts = value.expression.split(" ").filter(Boolean);
    return parts.map((t, idx) => {
      const id = Date.now() + idx;
      if (operators.text_arithmetic.operators.includes(t))
        return { id, type: "op", value: t };
      if (value.variables?.[t])
        return { id, type: "var", name: t, config: value.variables[t] };
      if (!isNaN(parseFloat(t))) return { id, type: "number", value: t };
      return { id, type: "unknown", value: t };
    });
  }, [value, operators.text_arithmetic.operators]);

  const [tokens, setTokens] = useState(initialTokens);
  useEffect(() => setTokens(initialTokens), [initialTokens]);

  // Modal state for variable editor
  const [editorOpen, setEditorOpen] = useState(false);
  const [editingToken, setEditingToken] = useState(null);

  // Internal state for the editor
  const [editType, setEditType] = useState("");
  const [editParams, setEditParams] = useState({});
  const [editTimeframe, setEditTimeframe] = useState(null);

  // Sync back to parent when tokens change
  const updateParent = (newTokens) => {
    setTokens(newTokens);
    const expression = newTokens
      .map((t) => (t.type === "var" ? t.name : t.value))
      .join(" ");
    const variables = {};
    newTokens.forEach((t) => {
      if (t.type === "var") {
        variables[t.name] = t.config;
      }
    });
    onChange({ expression, variables });
  };

  const addToken = (token) => {
    updateParent([...tokens, { ...token, id: Date.now() }]);
  };

  const removeLast = () => {
    if (tokens.length === 0) return;
    updateParent(tokens.slice(0, -1));
  };

  const clearAll = () => {
    updateParent([]);
  };

  const handleOpenVarEditor = (tokenToEdit = null) => {
    if (tokenToEdit) {
      setEditingToken(tokenToEdit);
      setEditType(tokenToEdit.config.type);
      setEditParams(tokenToEdit.config.params || {});
      setEditTimeframe(tokenToEdit.config.timeframe || null);
    } else {
      setEditingToken(null);
      setEditType("");
      setEditParams({});
      setEditTimeframe(null);
    }
    setEditorOpen(true);
  };

  const handleSaveVariable = () => {
    if (!editType) return;

    const varConfig = {
      type: editType,
      params: editParams,
      timeframe: editTimeframe,
    };

    if (editingToken) {
      // Update existing
      const newTokens = tokens.map((t) =>
        t.id === editingToken.id ? { ...t, config: varConfig } : t,
      );
      updateParent(newTokens);
    } else {
      // Variable identity follows the same grammar published to the validator.
      const existingVars = tokens
        .filter((t) => t.type === "var")
        .map((t) => parseInt(t.name.slice(operators.text_arithmetic.variable_prefix.length)) || 0);
      const nextNum =
        existingVars.length > 0 ? Math.max(...existingVars) + 1 : 1;
      const varName = `${operators.text_arithmetic.variable_prefix}${nextNum}`;
      addToken({ type: "var", name: varName, config: varConfig });
    }
    setEditorOpen(false);
  };

  // Keyboard support for numbers and basic operators
  const [numBuffer, setNumBuffer] = useState("");
  const handleAddNumBuffer = () => {
    if (numBuffer) {
      addToken({ type: "number", value: numBuffer });
      setNumBuffer("");
    }
  };

  const renderPill = (token) => {
    switch (token.type) {
      case "var":
        return (
          <TooltipProvider key={token.id}>
            <Tooltip>
              <TooltipTrigger asChild>
                <div
                  onClick={() => handleOpenVarEditor(token)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-brand/20 text-brand border border-brand/40 cursor-pointer hover:bg-brand/30 transition-colors shadow-sm font-semibold tracking-wide text-xs"
                >
                  <Activity className="w-3 h-3" />
                  {token.name}
                </div>
              </TooltipTrigger>
              <TooltipContent className="text-xs">
                <div className="font-bold text-foreground">{token.config.type}</div>
                <div className="text-muted-foreground">Click to edit</div>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        );
      case "op":
        return (
          <div
            key={token.id}
            className="px-2 py-1.5 font-bold text-warning text-sm"
          >
            {token.value}
          </div>
        );
      case "number":
        return (
          <div
            key={token.id}
            className="px-3 py-1.5 rounded-full bg-success/10 text-success border border-success/30 font-mono font-bold text-xs shadow-sm"
          >
            {token.value}
          </div>
        );
      default:
        return (
          <span key={token.id} className="text-loss">
            {token.value}
          </span>
        );
    }
  };

  const formatVarConfig = (config) => {
    if (!config) return "";
    const params = config.params || {};
    const pVals = Object.values(params)
      .filter((v) => v !== null && v !== undefined)
      .join(", ");
    const tf = config.timeframe ? ` | ${config.timeframe}` : "";
    return `${config.type} ${pVals ? `(${pVals})` : ""}${tf}`;
  };

  const uniqueVars = useMemo(() => {
    const vars = [];
    const seen = new Set();
    tokens.forEach((t) => {
      if (t.type === "var" && !seen.has(t.name)) {
        seen.add(t.name);
        vars.push(t);
      }
    });
    return vars;
  }, [tokens]);

  const keypadLayout = [
    "(", ")", "/", "*",
    "7", "8", "9", "-",
    "4", "5", "6", "+",
    "1", "2", "3", ".",
    "0",
  ];
  const arithmetic = operators.text_arithmetic.operators;
  const calcButtons = [
    ...keypadLayout.filter((value) => !Number.isNaN(Number(value)) || value === "." || arithmetic.includes(value)),
    ...arithmetic.filter((value) => !keypadLayout.includes(value)),
  ];
  return (
    <div className="w-full space-y-3 bg-muted/40 p-3 rounded-lg border border-border/50">

      {/* Expression Display Area */}
      <div className="min-h-[60px] w-full bg-card rounded-md border border-border p-3 flex flex-wrap gap-1.5 items-center cursor-text">
        {tokens.length === 0 && !numBuffer && (
          <span className="text-muted-foreground text-sm italic select-none">Build expression using buttons below...</span>
        )}
        {tokens.map(renderPill)}

        {/* Live typing buffer for numbers */}
        {numBuffer && (
          <div className="px-3 py-1.5 rounded-full bg-success/10 text-success border border-success/30 font-mono font-bold text-xs animate-pulse">
            {numBuffer}
          </div>
        )}
      </div>

      {/* Controls Grid */}
      <div className="grid grid-cols-12 gap-3">
        {/* Left Side: Variables Ledger */}
        <div className="col-span-7 flex flex-col h-[310px] bg-card/30 p-2.5 rounded-lg border border-border/50">
          <Button
            variant="selected"
            size="sm"
            onClick={() => {
              handleAddNumBuffer();
              handleOpenVarEditor();
            }}
            className="w-full shrink-0"
          >
            <Activity className="w-4 h-4 mr-2" />
            <span className="text-xs font-semibold tracking-wide">
              + Add Variable / Indicator
            </span>
          </Button>

          <div className="flex-1 overflow-y-auto min-h-0 mt-3 pr-1 space-y-2 scrollbar-theme">
            {uniqueVars.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center px-4 py-6">
                <span className="text-[10px] text-muted-foreground uppercase tracking-widest font-bold mb-1">
                  Variable Ledger
                </span>
                <p className="text-[10px] text-muted-foreground leading-relaxed">
                  Variables added to your expression will appear here for quick
                  reference.
                </p>
              </div>
            ) : (
              uniqueVars.map((v) => (
                <div
                  key={v.name}
                  onClick={() => handleOpenVarEditor(v)}
                  className="group flex flex-col gap-1 p-2 rounded-md bg-muted border border-border hover:border-brand/30 hover:bg-brand/5 cursor-pointer transition-colors shrink-0"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold text-brand bg-brand/10 px-1.5 py-0.5 rounded uppercase tracking-wider">
                      {v.name}
                    </span>
                    <Edit2 className="w-3 h-3 text-muted-foreground group-hover:text-brand transition-colors" />
                  </div>
                  <OverflowTooltip className="text-[10px] text-muted-foreground font-mono">
                    {formatVarConfig(v.config)}
                  </OverflowTooltip>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right Side: Numpad & Operators */}
        <div className="col-span-5 flex flex-col h-[310px] bg-card/50 p-2 rounded-lg border border-border/80">
          <div className="grid grid-cols-4 gap-1.5 flex-1">
            {calcButtons.map((btn) => {
              const isParen = ["(", ")"].includes(btn);
              const isOp = arithmetic.includes(btn) && !isParen;
              return (
                <Button
                  key={btn}
                  variant={isOp ? "warning" : isParen ? "selected" : "outline"}
                  size="sm"
                  onClick={() => {
                    if (isOp || isParen) {
                      handleAddNumBuffer();
                      addToken({ type: "op", value: btn });
                    } else {
                      setNumBuffer((prev) => prev + btn);
                    }
                  }}
                  className={`font-mono font-bold ${btn === "0" ? "col-span-4" : ""}`}
                >
                  {btn}
                </Button>
              );
            })}

            {/* Enter buffer button */}
            <Button
              variant="outline"
              size="sm"
              onClick={handleAddNumBuffer}
              disabled={!numBuffer}
              className="col-span-4 flex items-center justify-center gap-1"
            >
              <Check className="w-4 h-4" />{" "}
              <span className="text-xs">Enter Number</span>
            </Button>

            {/* Backspace & Clear */}
            <Button
              variant="destructive-outline"
              size="sm"
              onClick={() => {
                if (numBuffer) setNumBuffer(numBuffer.slice(0, -1));
                else removeLast();
              }}
              className="col-span-2 text-[10px]"
            >
              <Delete className="w-3 h-3 mr-1" /> Back
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setNumBuffer("");
                clearAll();
              }}
              className="col-span-2 text-[10px]"
            >
              Clear All
            </Button>
          </div>
        </div>
      </div>

      {/* Indicator Configuration Modal */}
      <Dialog open={editorOpen} onOpenChange={setEditorOpen}>
        <DialogContent className="bg-card border border-border text-foreground max-w-xl">
          <DialogHeader>
            <DialogTitle className="text-brand flex items-center gap-2">
              <Calculator className="w-5 h-5" />
              {editingToken
                ? `Edit ${editingToken.name}`
                : "Configure New Variable / Indicator"}
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-3 py-3">
            <div className="bg-muted/60 p-3 rounded-lg border border-border">
              <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider block mb-2">
                Select Variable / Indicator Type
              </label>
              <OperandSelector
                value={editType}
                params={editParams}
                timeframe={editTimeframe}
                onChangeType={(v) => {
                  setEditType(v);
                  // Reset params to defaults when type changes
                  setEditParams(defaultParams(v));
                  setEditTimeframe(null);
                }}
                ruleType={ruleType}
                allowedValues={allowedVariableTypes}
                onChangeParams={setEditParams}
                onChangeTimeframe={setEditTimeframe}
                placeholder="Choose Variable / Indicator..."
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setEditorOpen(false)}
              className=""
            >
              Cancel
            </Button>
            <Button variant="default"
              onClick={handleSaveVariable}
              disabled={!editType}

            >
              Save Variable
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

MathExpressionBuilder.propTypes = {
  ...MathExpressionBuilder.propTypes,
  allowedVariableTypes: PropTypes.array,
  onChange: PropTypes.func,
  ruleType: PropTypes.string,
  value: PropTypes.shape({ expression: PropTypes.string, variables: PropTypes.object }),
};
