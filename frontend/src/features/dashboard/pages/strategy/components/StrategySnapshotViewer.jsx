import React from 'react';
import { Badge } from "@/shared/components/ui/badge";
import { ArrowRight, CheckCircle2 } from 'lucide-react';

export default function StrategySnapshotViewer({ snapshot, previousSnapshot }) {
  if (!snapshot) return null;

  // Helper to compare values
  const getDiff = (current, prev) => {
    const changes = [];
    if (!prev) return changes;

    // Helper to compare objects
    const compareObjects = (section, currObj, prevObj, ignoreKeys = []) => {
      const allKeys = new Set([...Object.keys(currObj || {}), ...Object.keys(prevObj || {})]);
      allKeys.forEach(key => {
        if (ignoreKeys.includes(key)) return;
        if (['id', 'created_at', 'updated_at', 'strategy', 'rule_group'].includes(key)) return;
        
        const v1 = prevObj?.[key];
        const v2 = currObj?.[key];

        if (v1 != v2) { // Loose equality
           // Format strict boolean/null/object diffs better
           const fmt = (v) => {
             if (v === null || v === undefined) return 'null';
             if (typeof v === 'boolean') return v ? 'true' : 'false';
             if (typeof v === 'object') return JSON.stringify(v);
             return String(v);
           };
           
           // If values are objects, doing line-by-line diff might be better, but for now stringify
           // Check if it's a "real" change (JSON stringify comparison)
           if (typeof v1 === 'object' && typeof v2 === 'object') {
              if (JSON.stringify(v1) === JSON.stringify(v2)) return;
           }

           changes.push({ section, field: key, from: fmt(v1), to: fmt(v2) });
        }
      });
    };

    // 1. Top Level Fields
    ['strategy_type', 'market_type', 'exchange', 'instrument_type', 'name', 'description'].forEach(field => {
      if (current[field] !== prev[field]) {
        changes.push({ section: 'General', field, from: prev[field], to: current[field] });
      }
    });

    // 2. Configs
    compareObjects('Entry Configuration', current.entry_order_config, prev.entry_order_config);
    compareObjects('Exit Configuration', current.exit_order_config, prev.exit_order_config);

    compareObjects('Time/Session', current.time_rule, prev.time_rule);
    compareObjects('Special Events', current.special_event_filter, prev.special_event_filter);

    // 3. Rule Groups (Deep Diff)
    const currGroups = current.rule_groups || [];
    const prevGroups = prev.rule_groups || [];

    const maxGroups = Math.max(currGroups.length, prevGroups.length);
    for (let i = 0; i < maxGroups; i++) {
        const g1 = prevGroups[i];
        const g2 = currGroups[i];

        if (!g1 && g2) {
            changes.push({ section: 'Rule Groups', field: `Group #${i+1}`, from: 'Does not exist', to: 'Created' });
            continue;
        }
        if (g1 && !g2) {
            changes.push({ section: 'Rule Groups', field: `Group #${i+1}`, from: 'Exists', to: 'Removed' });
            continue;
        }

        // Compare Group Fields
        compareObjects(`Rule Group #${i+1}`, g2, g1, ['rules']);

        // Compare Nested Lists
        const compareList = (name, list1, list2) => {
            const max = Math.max(list1?.length || 0, list2?.length || 0);
            for (let j = 0; j < max; j++) {
                const item1 = list1?.[j];
                const item2 = list2?.[j];
                
                if (!item1 && item2) {
                    changes.push({ section: `Group #${i+1} ${name}`, field: `${name} #${j+1}`, from: 'None', to: 'Added' });
                } else if (item1 && !item2) {
                    changes.push({ section: `Group #${i+1} ${name}`, field: `${name} #${j+1}`, from: 'Exists', to: 'Removed' });
                } else {
                    compareObjects(`Group #${i+1} ${name} #${j+1}`, item2, item1);
                }
            }
        };

        compareList('Rules', g1.rules, g2.rules);
    }

    return changes;
  };

  const changes = previousSnapshot ? getDiff(snapshot, previousSnapshot) : null;
  const isFirstVersion = !previousSnapshot;

  if (isFirstVersion) {
    return (
      <div className="text-center py-8">
        <div className="inline-flex p-3 rounded-full bg-emerald-500/10 mb-3">
          <CheckCircle2 className="h-6 w-6 text-emerald-400" />
        </div>
        <h3 className="text-lg font-medium text-white">Initial Version</h3>
        <p className="text-gray-400 text-sm mt-1">This is the first snapshot of your strategy.</p>
        
        <div className="mt-6 grid grid-cols-2 gap-4 max-w-lg mx-auto text-left">
           <div className="bg-gray-800/50 p-3 rounded border border-gray-700/30">
              <span className="text-xs text-gray-500 block">Strategy Type</span>
              <span className="text-white">{snapshot.strategy_type}</span>
           </div>
           <div className="bg-gray-800/50 p-3 rounded border border-gray-700/30">
              <span className="text-xs text-gray-500 block">Market</span>
              <span className="text-white">{snapshot.market_type}</span>
           </div>
        </div>
        
        {/* Raw Data Toggle */}
        <div className="pt-6 border-t border-gray-800 mt-8 text-left">
           <details className="group">
              <summary className="flex items-center justify-center text-xs text-gray-500 cursor-pointer hover:text-gray-300 select-none">
                 <span className="mr-2">▶</span> Show Full Raw Snapshot
              </summary>
              <pre className="mt-4 bg-gray-950/50 p-4 rounded-lg overflow-auto max-h-60 text-[10px] text-gray-400 font-mono border border-gray-800 text-left">
                 {JSON.stringify(snapshot, null, 2)}
              </pre>
           </details>
        </div>
      </div>
    );
  }

  if (changes.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="inline-flex p-3 rounded-full bg-gray-800 mb-3">
          <CheckCircle2 className="h-6 w-6 text-gray-500" />
        </div>
        <p className="text-gray-400">No configuration changes detected in this snapshot.</p>

        {/* Raw Data Toggle */}
        <div className="pt-6 border-t border-gray-800 mt-8 text-left max-w-2xl mx-auto">
           <details className="group">
              <summary className="flex items-center justify-center text-xs text-gray-500 cursor-pointer hover:text-gray-300 select-none">
                 <span className="mr-2">▶</span> Show Full Raw Snapshot
              </summary>
              <pre className="mt-4 bg-gray-950/50 p-4 rounded-lg overflow-auto max-h-60 text-[10px] text-gray-400 font-mono border border-gray-800 text-left">
                 {JSON.stringify(snapshot, null, 2)}
              </pre>
           </details>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 mb-2">
         <Badge variant="outline" className="text-amber-400 border-amber-500/30 bg-amber-500/10">
            {changes.length} Changes Detected
         </Badge>
      </div>

      <div className="grid gap-2">
        {changes.map((change, i) => (
          <div key={i} className="flex items-center justify-between p-3 bg-gray-800/40 border border-gray-700/40 rounded-lg group hover:border-gray-600/50 transition-colors">
            <div className="flex flex-col">
              <span className="text-[10px] text-gray-500 uppercase tracking-wider">{change.section}</span>
              <span className="text-sm font-medium text-white capitalize">{change.field.replace(/_/g, ' ')}</span>
            </div>
            
            <div className="flex items-center gap-3">
               <div className="px-2 py-1 rounded bg-red-500/10 text-red-400 text-xs font-mono line-through opacity-70">
                  {String(change.from ?? 'null')}
               </div>
               <ArrowRight className="h-3 w-3 text-gray-500" />
               <div className="px-2 py-1 rounded bg-emerald-500/10 text-emerald-400 text-xs font-mono font-medium">
                  {String(change.to ?? 'null')}
               </div>
            </div>
          </div>
        ))}
      </div>

      {/* Raw Data Toggle */}
      <div className="pt-6 border-t border-gray-800 mt-6">
         <details className="group">
            <summary className="flex items-center text-xs text-gray-500 cursor-pointer hover:text-gray-300 select-none">
               <span className="mr-2">▶</span> Show Full Raw Snapshot
            </summary>
            <pre className="mt-4 bg-gray-950/50 p-4 rounded-lg overflow-auto max-h-60 text-[10px] text-gray-400 font-mono border border-gray-800">
               {JSON.stringify(snapshot, null, 2)}
            </pre>
         </details>
      </div>
    </div>
  );
}
