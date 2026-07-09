/**
 * Risk Settings - position sizing, execution, and re-entry configuration
 */
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/shared/components/ui/card";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import { Badge } from "@/shared/components/ui/badge";
import { Switch } from "@/shared/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/components/ui/select";
import { Slider } from "@/shared/components/ui/slider";
import { 
  DollarSign, Gauge, RefreshCw
} from 'lucide-react';
import StrategyConfigNav from './StrategyConfigNav';
import StrategyFooter from './StrategyFooter';
import { strategyApi, entryConfigApi, reentryRuleApi } from '@/shared/services/strategyApi';
import { riskApi } from '@/shared/services/portfolioApi';
import { useNotifications } from '@/shared/hooks/useNotifications';
import { useEnums } from '@/shared/context/EnumsContext';

// Risk level indicator
const getRiskLevel = (pct) => {
  if (pct <= 1) return { label: 'Conservative', color: 'text-emerald-400', bg: 'bg-emerald-500/15', border: 'border-emerald-500/30' };
  if (pct <= 2) return { label: 'Moderate', color: 'text-amber-400', bg: 'bg-amber-500/15', border: 'border-amber-500/30' };
  if (pct <= 3) return { label: 'Aggressive', color: 'text-orange-400', bg: 'bg-orange-500/15', border: 'border-orange-500/30' };
  return { label: 'Very Aggressive', color: 'text-rose-400', bg: 'bg-rose-500/15', border: 'border-rose-500/30' };
};

import { usePageActions } from '@/shared/context/PageActionsContext'; // Added import
import { GlobalLoader } from '@/shared/components/ui/global-loader';

export default function RiskSettings() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { notify } = useNotifications();
  const { enums } = useEnums();
  const { setPageHeader } = usePageActions(); // Use context
  
  const [strategy, setStrategy] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  
  const [sizingRuleId, setSizingRuleId] = useState(null);
  
  const [formData, setFormData] = useState({
    order_type: 'MARKET',
    execution_style: 'LTP',
    price_offset: 0,
    quantity_type: 'CAPITAL_BASED',
    fixed_quantity: 1,
    capital_percentage: 10,
    risk_amount: 1000,
    allow_partial_entry: false,
    entry_cooldown_seconds: 60,
    max_open_positions: 5,
    max_daily_trades: 10,
    risk_per_trade_pct: 1,
    loss_recovery_mode: false,
    loss_recovery_multiplier: 1.5,
  });

  // Re-entry Rule
  const [reentryData, setReentryData] = useState({
    allow_reentry: false,
    reentry_cooldown_seconds: 300,
    allow_reverse_entry: false,
  });

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
      const data = await strategyApi.getById(id);
      setStrategy(data);
      // Fetch entry config (order execution)
      if (data.entry_order_config) {
        const c = data.entry_order_config;
        setFormData(prev => ({
          ...prev,
          execution_style: c.execution_style || 'LTP',
          price_offset: c.price_offset ?? 0,
          allow_partial_entry: c.allow_partial_entry ?? false,
          entry_cooldown_seconds: c.entry_cooldown_seconds || 60,
        }));
      }

      // Fetch position sizing and limits
      const sizingRes = await riskApi.getSizingRules({ strategy: id });
      const sizingData = Array.isArray(sizingRes.data) ? sizingRes.data : sizingRes.data.results || [];
      if (sizingData && sizingData.length > 0) {
        const s = sizingData[0];
        setSizingRuleId(s.id);
        setFormData(prev => ({
          ...prev,
          quantity_type: s.sizing_method || 'CAPITAL_BASED',
          fixed_quantity: s.fixed_quantity || 1,
          capital_percentage: s.capital_percentage || 10,
          risk_amount: s.risk_per_trade_amount ?? 1000,
          risk_per_trade_pct: s.risk_per_trade_percentage ?? 1,
          max_daily_trades: s.max_daily_trades ?? 10,
          max_open_positions: s.max_open_positions ?? 5,
          loss_recovery_mode: s.loss_recovery_mode ?? false,
          loss_recovery_multiplier: s.loss_recovery_multiplier ?? 1.5,
        }));
      }

      // Fetch re-entry rule
      if (data.reentry_rule) {
        const r = data.reentry_rule;
        setReentryData(prev => ({
          ...prev,
          allow_reentry: r.allow_reentry ?? false,
          reentry_cooldown_seconds: r.reentry_cooldown_seconds ?? 300,
          allow_reverse_entry: r.allow_reverse_entry ?? false,
        }));
      }
    } catch (error) {
      notify.error('Failed to load risk settings');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      // Save entry order config
      if (strategy?.entry_order_config?.id) {
        const entryPayload = {
          execution_style: formData.execution_style,
          price_offset: (formData.execution_style === 'LIMIT_OFFSET' || formData.execution_style === 'STOP_BREAKOUT') ? formData.price_offset : null,
          allow_partial_entry: formData.allow_partial_entry,
          entry_cooldown_seconds: Number.isNaN(parseInt(formData.entry_cooldown_seconds)) ? 0 : formData.entry_cooldown_seconds,
        };
        await entryConfigApi.update(strategy.entry_order_config.id, entryPayload);
      }

      const rawSizingPayload = {
        strategy: id,
        sizing_method: formData.quantity_type,
        fixed_quantity: formData.quantity_type === 'FIXED' ? formData.fixed_quantity : null,
        capital_percentage: formData.quantity_type === 'CAPITAL_BASED' ? formData.capital_percentage : null,
        risk_per_trade_amount: (formData.quantity_type === 'RISK_FIXED' || formData.quantity_type === 'VOLATILITY_ADJUSTED') ? formData.risk_amount : null,
        risk_per_trade_percentage: formData.quantity_type === 'RISK_PERCENTAGE' ? formData.risk_per_trade_pct : null,
        max_daily_trades: formData.max_daily_trades,
        max_open_positions: formData.max_open_positions,
        loss_recovery_mode: formData.loss_recovery_mode,
        loss_recovery_multiplier: formData.loss_recovery_mode ? (Number.isNaN(parseFloat(formData.loss_recovery_multiplier)) ? 1.0 : formData.loss_recovery_multiplier) : 1.0,
      };

      // Sanitize: convert NaN to 0, preserve nulls (needed to clear unused fields in DB)
      const sizingPayload = {};
      for (const [key, val] of Object.entries(rawSizingPayload)) {
        sizingPayload[key] = (typeof val === 'number' && Number.isNaN(val)) ? 0 : val;
      }

      if (sizingRuleId) {
        await riskApi.updateSizingRule(sizingRuleId, sizingPayload);
      } else {
        const newSizing = await riskApi.createSizingRule(sizingPayload);
        setSizingRuleId(newSizing.id);
      }

      // Save re-entry rule
      if (strategy?.reentry_rule?.id) {
        const payload = {
          allow_reentry: reentryData.allow_reentry,
          reentry_cooldown_seconds: reentryData.allow_reentry ? (Number.isNaN(parseInt(reentryData.reentry_cooldown_seconds)) ? 0 : reentryData.reentry_cooldown_seconds) : 0,
          allow_reverse_entry: reentryData.allow_reentry ? reentryData.allow_reverse_entry : false,
        };
        await reentryRuleApi.update(strategy.reentry_rule.id, payload);
      } else {
        console.warn('No ReEntryRule found to update for strategy', strategy?.id);
      }
      notify.success('Risk settings saved');
      // navigate removed to keep user on same page
      fetchData(); // Refresh data to ensure sync
    } catch (error) {
      console.error(error);
      notify.error('Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const riskLevel = getRiskLevel(formData.risk_per_trade_pct);

  if (loading) {
    return (
      <div className="flex flex-col justify-center items-center h-96 gap-3">
        <GlobalLoader />
        <p className="text-sm text-gray-400">Loading risk settings...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col flex-1 min-h-0">
      <div className="flex-1 overflow-y-auto scrollbar-theme">
        <div className="container-padding py-6 lg:py-8 space-y-6">

      {/* Order Type & Entry Logic */}
      <Card className="bg-gray-900/40 border-gray-800/80">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2 text-base">
            <div className="p-1.5 rounded-lg bg-blue-500/10">
              <Gauge className="h-4 w-4 text-blue-400" />
            </div>
            Order Configuration
          </CardTitle>
          <CardDescription className="text-gray-500 text-xs">
            How orders are placed when entry conditions are met
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label className="text-xs text-gray-500">Execution Style</Label>
              <Select 
                value={formData.execution_style} 
                onValueChange={(v) => setFormData({ ...formData, execution_style: v })}
              >
                <SelectTrigger className="bg-gray-800/60 border-gray-700 h-9 text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(enums.ExecutionStyle || []).map(t => (
                    <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs text-gray-500">Entry Cooldown (seconds)</Label>
              <Input
                type="number"
                min="0"
                value={formData.entry_cooldown_seconds}
                onChange={(e) => setFormData({ ...formData, entry_cooldown_seconds: parseInt(e.target.value) || 0 })}
                className="bg-gray-800/60 border-gray-700 text-white h-9 text-sm"
              />
            </div>
            </div>
            
            {(formData.execution_style === 'LIMIT_OFFSET' || formData.execution_style === 'STOP_BREAKOUT') && (
            <div className="space-y-1.5">
              <Label className="text-xs text-gray-500">Price Offset</Label>
              <Input
                type="number"
                step="0.01"
                value={formData.price_offset}
                onChange={(e) => setFormData({ ...formData, price_offset: parseFloat(e.target.value) || 0 })}
                className="bg-gray-800/60 border-gray-700 text-white h-9 text-sm"
              />
            </div>
            )}
          <div className="flex items-center justify-between p-3 bg-gray-800/40 rounded-lg border border-gray-700/40">
            <div>
              <Label className="text-sm text-gray-200">Allow Partial Entry</Label>
              <p className="text-xs text-gray-500 mt-0.5">Allow partial fills on limit orders</p>
            </div>
            <Switch
              checked={formData.allow_partial_entry}
              onCheckedChange={(v) => setFormData({ ...formData, allow_partial_entry: v })}
            />
          </div>
        </CardContent>
      </Card>

      {/* Position Sizing */}
      <Card className="bg-gray-900/40 border-gray-800/80">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2 text-base">
            <div className="p-1.5 rounded-lg bg-teal-500/10">
              <DollarSign className="h-4 w-4 text-teal-400" />
            </div>
            Position Sizing
          </CardTitle>
          <CardDescription className="text-gray-500 text-xs">
            How to calculate trade quantity for each entry
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label className="text-xs text-gray-500">Sizing Method</Label>
              <Select 
                value={formData.quantity_type} 
                onValueChange={(v) => setFormData({ ...formData, quantity_type: v })}
              >
                <SelectTrigger className="bg-gray-800/60 border-gray-700 h-9 text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(enums.QuantityType || []).map(t => (
                    <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {formData.quantity_type === 'FIXED' && (
              <div className="space-y-1.5">
                <Label className="text-xs text-gray-500">Fixed Quantity</Label>
                <Input
                  type="number"
                  value={formData.fixed_quantity}
                  onChange={(e) => setFormData({ ...formData, fixed_quantity: parseInt(e.target.value) })}
                  className="bg-gray-800/60 border-gray-700 text-white h-9 text-sm"
                />
              </div>
            )}

            {formData.quantity_type === 'CAPITAL_BASED' && (
              <div className="space-y-1.5">
                <Label className="text-xs text-gray-500">Capital per Trade (%)</Label>
                <Input
                  type="number"
                  step="0.5"
                  value={formData.capital_percentage}
                  onChange={(e) => setFormData({ ...formData, capital_percentage: parseFloat(e.target.value) })}
                  className="bg-gray-800/60 border-gray-700 text-white h-9 text-sm"
                />
              </div>
            )}

            {(formData.quantity_type === 'RISK_FIXED' || formData.quantity_type === 'VOLATILITY_ADJUSTED') && (
              <div className="space-y-1.5">
                <Label className="text-xs text-gray-500">Risk per Trade (₹)</Label>
                <Input
                  type="number"
                  value={formData.risk_amount}
                  onChange={(e) => setFormData({ ...formData, risk_amount: parseFloat(e.target.value) })}
                  className="bg-gray-800/60 border-gray-700 text-white h-9 text-sm"
                />
                {formData.quantity_type === 'VOLATILITY_ADJUSTED' && (
                  <p className="text-[10px] text-gray-500">Risk amount is divided by ATR to determine size</p>
                )}
              </div>
            )}
          </div>

          {/* Risk slider with level indicator - Only show for RISK_PERCENTAGE */}
          {formData.quantity_type === 'RISK_PERCENTAGE' && (
          <div className="space-y-3 pt-2">
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-500">Risk per Trade</span>
              <div className="flex items-center gap-2">
                <span className="text-sm font-mono text-white">{formData.risk_per_trade_pct}%</span>
                <Badge variant="outline" className={`text-[10px] ${riskLevel.color} ${riskLevel.border} ${riskLevel.bg}`}>
                  {riskLevel.label}
                </Badge>
              </div>
            </div>
            <Slider
              value={[formData.risk_per_trade_pct]}
              onValueChange={(v) => setFormData({ ...formData, risk_per_trade_pct: v[0] })}
              max={5}
              step={0.25}
              className="w-full"
            />
            <div className="flex justify-between text-[10px] text-gray-600">
              <span>0%</span>
              <span>1%</span>
              <span>2%</span>
              <span>3%</span>
              <span>4%</span>
              <span>5%</span>
            </div>
          </div>
          )}

          {/* Loss Recovery */}
          <div className="flex items-center justify-between p-3 bg-gray-800/40 rounded-lg border border-gray-700/40 mt-4">
            <div>
              <Label className="text-sm text-gray-200">Loss Recovery Mode (Martingale)</Label>
              <p className="text-xs text-gray-500 mt-0.5">Increase position size after a loss to recover</p>
            </div>
            <Switch
              checked={formData.loss_recovery_mode}
              onCheckedChange={(v) => setFormData({ ...formData, loss_recovery_mode: v })}
            />
          </div>
          {formData.loss_recovery_mode && (
            <div className="space-y-1.5 max-w-xs mt-2">
              <Label className="text-xs text-gray-500">Recovery Multiplier</Label>
              <Input
                type="number"
                step="0.1"
                value={formData.loss_recovery_multiplier}
                onChange={(e) => setFormData({ ...formData, loss_recovery_multiplier: parseFloat(e.target.value) })}
                className="bg-gray-800/60 border-gray-700 text-white h-9 text-sm"
              />
              <p className="text-[10px] text-gray-600">Multiply quantity by this factor after a loss</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Re-Entry Rules */}
      <Card className="bg-gray-900/40 border-gray-800/80">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2 text-base">
            <div className="p-1.5 rounded-lg bg-purple-500/10">
              <RefreshCw className="h-4 w-4 text-purple-400" />
            </div>
            Re-Entry Rules
          </CardTitle>
          <CardDescription className="text-gray-500 text-xs">
            Configure automatic re-entry after exit
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Master toggle */}
          <div className="flex items-center justify-between p-3 bg-gray-800/40 rounded-lg border border-gray-700/40">
            <div>
              <Label className="text-sm text-gray-200">Allow Re-Entry</Label>
              <p className="text-xs text-gray-500 mt-0.5">Automatically re-enter after a stop loss or target exit</p>
            </div>
            <Switch
              checked={reentryData.allow_reentry}
              onCheckedChange={(v) => setReentryData({ ...reentryData, allow_reentry: v })}
            />
          </div>

          {reentryData.allow_reentry && (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label className="text-xs text-gray-500">Cooldown (seconds)</Label>
                  <Input
                    type="number"
                    value={reentryData.reentry_cooldown_seconds}
                    onChange={(e) => setReentryData({ ...reentryData, reentry_cooldown_seconds: parseInt(e.target.value) })}
                    className="bg-gray-800/60 border-gray-700 text-white h-9 text-sm"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="flex items-center justify-between p-3 bg-gray-800/40 rounded-lg border border-gray-700/40">
                  <div>
                    <Label className="text-sm text-gray-200">Allow Reverse Entry</Label>
                    <p className="text-xs text-gray-500 mt-0.5">Enter opposite direction on exit</p>
                  </div>
                  <Switch
                    checked={reentryData.allow_reverse_entry}
                    onCheckedChange={(v) => setReentryData({ ...reentryData, allow_reverse_entry: v })}
                  />
                </div>
              </div>

            </>
          )}
        </CardContent>
      </Card>

        </div>
      </div>
      <StrategyFooter
        onSave={handleSave}
        onCancel={() => navigate(`/dashboard/strategy/${id}/edit`)}
        saving={saving}
        saveLabel="Save Settings"
        savingLabel="Saving..."
      />
    </div>
  );
}
