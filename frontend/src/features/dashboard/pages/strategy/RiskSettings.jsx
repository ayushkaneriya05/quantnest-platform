/**
 * Risk Settings - position sizing, execution, and re-entry configuration
 */
import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/shared/components/ui/card";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/components/ui/select";
import { 
  DollarSign, Gauge
} from 'lucide-react';
import StrategyConfigNav from './StrategyConfigNav';
import StrategyFooter from './StrategyFooter';
import { strategyApi, entryConfigApi } from '@/shared/services/strategyApi';
import { riskApi } from '@/shared/services/portfolioApi';
import { useNotifications } from '@/shared/hooks/useNotifications';
import { useEnums } from '@/shared/context/EnumsContext';
import { getApiErrorMessage } from "@/shared/utils/apiErrors";

import { usePageActions } from '@/shared/context/pageActions'; // Added import
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
    price_offset: 0,
    quantity_type: 'CAPITAL_BASED',
    fixed_quantity: 1,
    capital_percentage: 10,
    cooldown_seconds: 0,
  });


  // Set Navigation in Header
  useEffect(() => {
    setPageHeader(<StrategyConfigNav strategy={strategy} />);
    return () => setPageHeader(null);
  }, [strategy, setPageHeader]);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const data = await strategyApi.getById(id);
      setStrategy(data);
      // Fetch entry config (order execution)
      if (data.entry_order_config) {
        const c = data.entry_order_config;
        setFormData(prev => ({
          ...prev,
          order_type: c.order_type || 'MARKET',
          price_offset: c.price_offset ?? 0,
          cooldown_seconds: c.cooldown_seconds ?? 0,
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
        }));
      }

    } catch (error) {
      notify.error(getApiErrorMessage(error, 'Failed to load risk settings'));
    } finally {
      setLoading(false);
    }
  }, [id, notify]);

  useEffect(() => { if (id) fetchData(); }, [id, fetchData]);

  const handleSave = async () => {
    try {
      setSaving(true);
      // Save entry order config
      if (strategy?.entry_order_config?.id) {
        const entryPayload = {
          order_type: formData.order_type,
          price_offset: formData.order_type === 'LIMIT' ? formData.price_offset : null,
          cooldown_seconds: Number.isNaN(parseInt(formData.cooldown_seconds)) ? 0 : formData.cooldown_seconds,
        };
        await entryConfigApi.update(strategy.entry_order_config.id, entryPayload);
      }

      const rawSizingPayload = {
        strategy: id,
        sizing_method: formData.quantity_type,
        fixed_quantity: formData.quantity_type === 'FIXED' ? formData.fixed_quantity : null,
        capital_percentage: formData.quantity_type === 'CAPITAL_BASED' ? formData.capital_percentage : null,
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
        setSizingRuleId(newSizing.data.id);
      }
      notify.success('Risk settings saved');
      // navigate removed to keep user on same page
      fetchData(); // Refresh data to ensure sync
    } catch (error) {
      console.error(error);
      notify.error(getApiErrorMessage(error, 'Failed to save settings'));
    } finally {
      setSaving(false);
    }
  };


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
              <Label className="text-xs text-gray-500">Order Type</Label>
              <Select 
                value={formData.order_type} 
                onValueChange={(v) => setFormData({ ...formData, order_type: v })}
              >
                <SelectTrigger className="bg-gray-800/60 border-gray-700 h-9 text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="MARKET">Market</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs text-gray-500">Trade Cooldown (seconds)</Label>
              <Input
                type="number"
                min="0"
                value={formData.cooldown_seconds}
                onChange={(e) => setFormData({ ...formData, cooldown_seconds: parseInt(e.target.value) || 0 })}
                className="bg-gray-800/60 border-gray-700 text-white h-9 text-sm"
              />
            </div>
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
          </div>


        </CardContent>
      </Card>


        </div>
      </div>
      <StrategyFooter
        onSave={handleSave}
        onCancel={() => navigate('/dashboard/strategy/list')}
        saving={saving}
        saveLabel="Save Settings"
        savingLabel="Saving..."
      />
    </div>
  );
}
