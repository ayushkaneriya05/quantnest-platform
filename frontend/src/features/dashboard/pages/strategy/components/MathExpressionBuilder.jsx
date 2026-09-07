import React, { useState, useEffect, useMemo } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/shared/components/ui/dialog";
import { Button } from "@/shared/components/ui/button";
import { X, Delete, Calculator, Check, Activity, Edit2, Play } from 'lucide-react';
import OperandSelector, { PARAM_CONFIG } from './OperandSelector';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/shared/components/ui/tooltip';

export default function MathExpressionBuilder({ value, onChange }) {
  // Parse initial value into tokens
  const initialTokens = useMemo(() => {
    if (!value || !value.expression) return [];
    const parts = value.expression.split(" ").filter(Boolean);
    return parts.map((t, idx) => {
      const id = Date.now() + idx;
      if (["+", "-", "*", "/", "(", ")"].includes(t))
        return { id, type: "op", value: t };
      if (value.variables?.[t])
        return { id, type: "var", name: t, config: value.variables[t] };
      if (!isNaN(parseFloat(t))) return { id, type: "number", value: t };
      return { id, type: "unknown", value: t };
    });
  }, [value]);

  const [tokens, setTokens] = useState(initialTokens);

  // Modal state for variable editor
  const [editorOpen, setEditorOpen] = useState(false);
  const [editingToken, setEditingToken] = useState(null); // The token being edited/created

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
      // Create new: generate next VAR_ name
      const existingVars = tokens
        .filter((t) => t.type === "var")
        .map((t) => parseInt(t.name.replace("VAR_", "")) || 0);
      const nextNum =
        existingVars.length > 0 ? Math.max(...existingVars) + 1 : 1;
      const varName = `VAR_${nextNum}`;
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
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 cursor-pointer hover:bg-indigo-500/30 transition-colors shadow-sm font-semibold tracking-wide text-xs"
                >
                  <Activity className="w-3 h-3" />
                  {token.name}
                </div>
              </TooltipTrigger>
              <TooltipContent className="bg-black/90 border border-gray-800 text-xs z-50">
                <div className="font-bold text-white">{token.config.type}</div>
                <div className="text-gray-400">Click to edit</div>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        );
      case "op":
        return (
          <div
            key={token.id}
            className="px-2 py-1.5 font-bold text-amber-400 text-sm"
          >
            {token.value}
          </div>
        );
      case "number":
        return (
          <div
            key={token.id}
            className="px-3 py-1.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-mono font-bold text-xs shadow-sm"
          >
            {token.value}
          </div>
        );
      default:
        return (
          <span key={token.id} className="text-red-400">
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

  const calcButtons = [
    '(', ')', '/', '*',
    '7', '8', '9', '-',
    '4', '5', '6', '+',
    '1', '2', '3', '.',
    '0'
  ];

  return (
    <div className="w-full space-y-3 bg-black/20 p-3 rounded-lg border border-gray-800/50">
      
      {/* Expression Display Area */}
      <div className="min-h-[60px] w-full bg-[#0a0c12] rounded-md border border-gray-800 p-3 flex flex-wrap gap-1.5 items-center cursor-text">
        {tokens.length === 0 && !numBuffer && (
          <span className="text-gray-600 text-sm italic select-none">Build expression using buttons below...</span>
        )}
        {tokens.map(renderPill)}

        {/* Live typing buffer for numbers */}
        {numBuffer && (
          <div className="px-3 py-1.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-mono font-bold text-xs animate-pulse">
            {numBuffer}
          </div>
        )}
      </div>

      {/* Controls Grid */}
      <div className="grid grid-cols-12 gap-4">
        {/* Left Side: Variables Ledger */}
        <div className="col-span-7 flex flex-col h-[310px] bg-gray-900/30 p-2.5 rounded-lg border border-gray-800/50">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              handleAddNumBuffer();
              handleOpenVarEditor();
            }}
            className="w-full bg-indigo-500/10 border-indigo-500/30 text-indigo-300 hover:bg-indigo-500/20 hover:text-indigo-200 h-9 shrink-0 shadow-sm"
          >
            <Activity className="w-4 h-4 mr-2" />
            <span className="text-xs font-semibold tracking-wide">
              + Add Indicator
            </span>
          </Button>

          <div className="flex-1 overflow-y-auto min-h-0 mt-3 pr-1 space-y-2 scrollbar-theme">
            {uniqueVars.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center px-4 py-6">
                <span className="text-[10px] text-gray-500 uppercase tracking-widest font-bold mb-1">
                  Variable Ledger
                </span>
                <p className="text-[10px] text-gray-600 leading-relaxed">
                  Variables added to your expression will appear here for quick
                  reference.
                </p>
              </div>
            ) : (
              uniqueVars.map((v) => (
                <div
                  key={v.name}
                  onClick={() => handleOpenVarEditor(v)}
                  className="group flex flex-col gap-1 p-2 rounded-md bg-black/40 border border-gray-800 hover:border-indigo-500/30 hover:bg-indigo-500/5 cursor-pointer transition-colors shrink-0"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold text-indigo-400 bg-indigo-500/10 px-1.5 py-0.5 rounded uppercase tracking-wider">
                      {v.name}
                    </span>
                    <Edit2 className="w-3 h-3 text-gray-600 group-hover:text-indigo-400 transition-colors" />
                  </div>
                  <span
                    className="text-[10px] text-gray-400 font-mono truncate"
                    title={formatVarConfig(v.config)}
                  >
                    {formatVarConfig(v.config)}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right Side: Numpad & Operators */}
        <div className="col-span-5 flex flex-col h-[310px] bg-gray-900/50 p-2 rounded-lg border border-gray-800/80">
          <div className="grid grid-cols-4 gap-1.5 flex-1">
            {calcButtons.map((btn) => {
              const isOp = ["/", "*", "-", "+"].includes(btn);
              const isParen = ["(", ")"].includes(btn);
              return (
                <Button
                  key={btn}
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    if (isOp || isParen) {
                      handleAddNumBuffer();
                      addToken({ type: "op", value: btn });
                    } else {
                      setNumBuffer((prev) => prev + btn);
                    }
                  }}
                  className={`h-9 font-mono font-bold text-sm ${
                    isOp
                      ? "bg-amber-500/10 border-amber-500/30 text-amber-400 hover:bg-amber-500/20"
                      : isParen
                        ? "bg-purple-500/10 border-purple-500/30 text-purple-400 hover:bg-purple-500/20"
                        : "bg-gray-800 border-gray-700 text-gray-200 hover:bg-gray-700"
                  } ${btn === "0" ? "col-span-4" : ""}`}
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
              className="col-span-4 h-9 bg-emerald-500/10 border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20 flex items-center justify-center gap-1"
            >
              <Check className="w-4 h-4" />{" "}
              <span className="text-xs">Enter Number</span>
            </Button>

            {/* Backspace & Clear */}
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                if (numBuffer) setNumBuffer(numBuffer.slice(0, -1));
                else removeLast();
              }}
              className="col-span-2 bg-red-500/10 border-red-500/30 text-red-400 hover:bg-red-500/20 h-8 text-[10px]"
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
              className="col-span-2 bg-gray-800 border-gray-700 text-gray-400 hover:bg-gray-700 hover:text-white h-8 text-[10px]"
            >
              Clear All
            </Button>
          </div>
        </div>
      </div>

      {/* Indicator Configuration Modal */}
      <Dialog open={editorOpen} onOpenChange={setEditorOpen}>
        <DialogContent className="bg-[#0f1423] border border-gray-800 text-gray-200 max-w-xl">
          <DialogHeader>
            <DialogTitle className="text-indigo-300 flex items-center gap-2">
              <Calculator className="w-5 h-5" />
              {editingToken
                ? `Edit ${editingToken.name}`
                : "Configure New Indicator"}
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="bg-black/30 p-4 rounded-lg border border-gray-800">
              <label className="text-xs font-bold text-gray-400 uppercase tracking-wider block mb-2">
                Select Indicator Type
              </label>
              <OperandSelector
                value={editType}
                params={editParams}
                timeframe={editTimeframe}
                onChangeType={(v) => {
                  setEditType(v);
                  // Reset params to defaults when type changes
                  const defaults = {};
                  (PARAM_CONFIG[v] || []).forEach(
                    (p) => (defaults[p.key] = p.default),
                  );
                  setEditParams(defaults);
                  setEditTimeframe(null);
                }}
                onChangeParams={setEditParams}
                onChangeTimeframe={setEditTimeframe}
                placeholder="Choose Indicator..."
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setEditorOpen(false)}
              className="border-gray-700 text-gray-300 hover:bg-gray-800"
            >
              Cancel
            </Button>
            <Button
              onClick={handleSaveVariable}
              disabled={!editType}
              className="bg-indigo-600 hover:bg-indigo-700 text-white"
            >
              Save Indicator
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
