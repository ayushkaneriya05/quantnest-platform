/**
 * Strategy Review - summary and validation before deployment
 */
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import { Badge } from "@/shared/components/ui/badge";
import { 
  Check, AlertTriangle, 
  Target, Shield, Clock, Layers, Settings, CheckCircle2, XCircle,
  Loader2, TrendingUp
} from 'lucide-react';
import StrategyConfigNav from './StrategyConfigNav';
import { strategyApi } from '@/shared/services/strategyApi';
import { ruleGroupApi, stopLossApi, targetApi } from '@/shared/services/rulesApi';
import { useNotifications } from '@/shared/hooks/useNotifications';
import { usePageActions } from '@/shared/context/PageActionsContext'; // Added import
import { GlobalLoader } from '@/shared/components/ui/global-loader';

export default function StrategyReview() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { notify } = useNotifications();
  const { setPageHeader } = usePageActions(); // Use context
  
  const [strategy, setStrategy] = useState(null);
  const [entryRules, setEntryRules] = useState([]);
  const [stopLossRules, setStopLossRules] = useState([]);
  const [targetRules, setTargetRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [validations, setValidations] = useState([]);

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
      const [strategyData, entryData, slData, tgtData] = await Promise.all([
        strategyApi.getById(id),
        ruleGroupApi.getByStrategy(id, 'ENTRY'),
        stopLossApi.getByStrategy(id),
        targetApi.getByStrategy(id)
      ]);
      setStrategy(strategyData);
      setEntryRules(entryData);
      setStopLossRules(slData);
      setTargetRules(tgtData);
      runValidations(strategyData, entryData, slData, tgtData);
    } catch (error) {
      notify.error('Failed to load strategy');
    } finally {
      setLoading(false);
    }
  };

  const runValidations = (strategy, entries, sls, targets) => {
    const checks = [];
    
    checks.push({
      name: 'Strategy name defined',
      passed: Boolean(strategy.name),
      category: 'Basic',
      icon: Settings,
    });
    
    const hasEntryRules = entries.length > 0 && entries.some(g => g.rules?.length > 0);
    checks.push({
      name: 'Entry rules configured',
      passed: hasEntryRules,
      category: 'Entry',
      icon: Target,
    });
    
    const hasStopLoss = sls.length > 0 && sls.some(sl => sl.is_active);
    checks.push({
      name: 'Stop loss defined',
      passed: hasStopLoss,
      category: 'Risk',
      warning: !hasStopLoss,
      icon: Shield,
    });
    
    const hasTarget = targets.length > 0 && targets.some(t => t.is_active);
    checks.push({
      name: 'Profit target defined',
      passed: hasTarget,
      category: 'Exit',
      icon: TrendingUp,
    });
    
    checks.push({
      name: 'Position sizing configured',
      passed: Boolean(strategy.entry_order_config),
      category: 'Risk',
      icon: Settings,
    });
    
    setValidations(checks);
  };

  const allPassed = validations.every(v => v.passed);
  const passedCount = validations.filter(v => v.passed).length;
  const warnings = validations.filter(v => v.warning);

  const handleActivate = async () => {
    try {
      await strategyApi.activate(id);
      notify.success('Strategy activated');
      navigate('/dashboard/strategy/list');
    } catch (error) {
      notify.error('Failed to activate strategy');
    }
  };

  const handlePaperTrade = () => {
    navigate(`/dashboard/paper/dashboard?strategy=${id}`);
  };

  if (loading) {
    return (
      <div className="flex flex-col justify-center items-center h-96 gap-3">
        <GlobalLoader />
        <p className="text-sm text-gray-400">Reviewing strategy...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col flex-1 min-h-0">
      <div className="flex-1 overflow-y-auto scrollbar-theme">
        <div className="container-padding py-6 lg:py-8 space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { icon: Target, label: 'Entry Conditions', value: entryRules.reduce((acc, g) => acc + (g.rules?.length || 0), 0), color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
          { icon: Shield, label: 'Stop Losses', value: stopLossRules.length, color: 'text-rose-400', bg: 'bg-rose-500/10' },
          { icon: Layers, label: 'Targets', value: targetRules.length, color: 'text-blue-400', bg: 'bg-blue-500/10' },
          { icon: Clock, label: 'Type', value: strategy?.strategy_type, color: 'text-amber-400', bg: 'bg-amber-500/10', isText: true },
        ].map((item, i) => {
          const Icon = item.icon;
          return (
            <Card key={i} className="bg-gray-900/40 border-gray-800/80">
              <CardContent className="py-4 px-4">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${item.bg} shrink-0`}>
                    <Icon className={`h-4 w-4 ${item.color}`} />
                  </div>
                  <div>
                    <p className={`font-bold ${item.isText ? 'text-sm' : 'text-xl'} text-white`}>
                      {item.value}
                    </p>
                    <p className="text-[10px] text-gray-500 uppercase tracking-wider">{item.label}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Validation Checklist */}
      <Card className="bg-gray-900/40 border-gray-800/80">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className={`p-1.5 rounded-lg ${allPassed ? 'bg-emerald-500/10' : 'bg-amber-500/10'}`}>
                {allPassed 
                  ? <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                  : <AlertTriangle className="h-4 w-4 text-amber-400" />
                }
              </div>
              <CardTitle className="text-white text-base">Readiness Check</CardTitle>
            </div>
            <Badge variant="outline" className={`text-xs font-mono ${
              allPassed 
                ? 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10' 
                : 'text-amber-400 border-amber-500/30 bg-amber-500/10'
            }`}>
              {passedCount}/{validations.length} passed
            </Badge>
          </div>
          <CardDescription className="text-gray-500 text-xs">
            {allPassed 
              ? 'All checks passed — your strategy is ready for deployment!' 
              : 'Some checks need attention before deployment'}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {validations.map((check, index) => (
            <div 
              key={index}
              className={`flex items-center justify-between p-3 rounded-lg border transition-colors ${
                check.passed 
                  ? 'bg-emerald-500/5 border-emerald-500/15' 
                  : check.warning 
                    ? 'bg-amber-500/5 border-amber-500/15'
                    : 'bg-rose-500/5 border-rose-500/15'
              }`}
            >
              <div className="flex items-center gap-3">
                {check.passed ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                ) : check.warning ? (
                  <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0" />
                ) : (
                  <XCircle className="h-4 w-4 text-rose-400 shrink-0" />
                )}
                <span className="text-sm text-white">{check.name}</span>
              </div>
              <Badge 
                variant="outline" 
                className={`text-[10px] ${
                  check.passed 
                    ? 'border-emerald-500/30 text-emerald-400' 
                    : 'border-gray-700/80 text-gray-500'
                }`}
              >
                {check.category}
              </Badge>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Warnings */}
      {warnings.length > 0 && (
        <Card className="bg-amber-500/5 border-amber-500/20">
          <CardContent className="py-4">
            <div className="flex items-start gap-3">
              <div className="p-2 rounded-lg bg-amber-500/10 shrink-0">
                <AlertTriangle className="h-4 w-4 text-amber-400" />
              </div>
              <div>
                <h4 className="text-sm font-medium text-amber-400">Risk Warning</h4>
                <p className="text-xs text-gray-400 mt-1 leading-relaxed">
                  Trading without a stop loss is not recommended. It exposes your capital to unlimited risk. Consider adding at least one stop loss rule before going live.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

        </div>
      </div>
    </div>
  );
}
