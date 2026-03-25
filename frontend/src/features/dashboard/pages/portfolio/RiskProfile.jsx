/**
 * Risk Profile Settings - user risk preferences and limits
 */
import { useState, useEffect, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import { Switch } from "@/shared/components/ui/switch";
import { Slider } from "@/shared/components/ui/slider";
import { 
  Shield, AlertTriangle, Save, DollarSign, TrendingDown,
  Layers, Percent
} from 'lucide-react';
import { riskApi } from '@/shared/services/portfolioApi';
import { useNotifications } from '@/shared/hooks/useNotifications';
import { usePageActions } from '@/shared/context/PageActionsContext';
import PortfolioRiskNav from './PortfolioRiskNav';
import StrategyFooter from '@/features/dashboard/pages/strategy/StrategyFooter';

export default function RiskProfile() {
  const { notify } = useNotifications();
  const { setPageHeader } = usePageActions();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  
  useEffect(() => {
    setPageHeader(<PortfolioRiskNav />);
    return () => setPageHeader(null);
  }, [setPageHeader]);
  
  const [profile, setProfile] = useState({
    max_daily_loss_percentage: 5,
    max_daily_loss_amount: null,
    max_daily_trades: 50,
    max_open_positions: 10,
    max_exposure_percentage: 80,
    max_per_strategy_allocation: 25,
    max_per_instrument_exposure: 10,

    max_drawdown_percentage: 15,
    trailing_drawdown_reset: true,
    alert_on_breach: true,
    halt_on_breach: false,
  });

  const fetchProfile = async () => {
    try {
      setLoading(true);
      const response = await riskApi.getMyProfile();
      if (response.data) {
        setProfile({ ...profile, ...response.data });
      }
    } catch (error) {
      // Profile might not exist yet
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProfile();
  }, []);

  const handleSave = async () => {
    try {
      setSaving(true);
      const payload = { ...profile };
      // Ensure NaN does not serialize to null (except for allowable fields)
      Object.keys(payload).forEach(key => {
        if (Number.isNaN(payload[key])) {
          payload[key] = key === 'max_daily_loss_amount' ? null : 0;
        }
      });
      await riskApi.updateProfile(payload);
      notify.success('Risk profile saved');
    } catch (error) {
      console.error(error);
      const errMsg = error.response?.data ? JSON.stringify(error.response.data) : error.message;
      notify.error(`Save failed: ${errMsg}`);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-96">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500" />
      </div>
    );
  }

  return (
    <div className="flex flex-col flex-1 min-h-0">
      <div className="flex-1 overflow-y-auto scrollbar-theme">
        <div className="container-padding py-6 lg:py-8 space-y-6">
          {/* Daily Limits */}
          <Card className="bg-gray-900/50 border-gray-800">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <DollarSign className="h-5 w-5 text-red-400" />
            Daily Loss Limits
          </CardTitle>
          <CardDescription>Maximum daily loss before trading stops</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Max Daily Loss (%)</span>
              <span className="text-white font-medium">{profile.max_daily_loss_percentage}%</span>
            </div>
            <Slider
              value={[profile.max_daily_loss_percentage]}
              onValueChange={(v) => setProfile({ ...profile, max_daily_loss_percentage: v[0] })}
              max={20}
              step={0.5}
            />
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label className="text-gray-400">Max Daily Loss (₹)</Label>
              <Input
                type="number"
                value={profile.max_daily_loss_amount || ''}
                onChange={(e) => setProfile({ ...profile, max_daily_loss_amount: e.target.value ? parseFloat(e.target.value) : null })}
                placeholder="Optional: fixed amount"
                className="bg-gray-800 border-gray-700 text-white"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-gray-400">Max Daily Trades</Label>
              <Input
                type="number"
                value={profile.max_daily_trades || ''}
                onChange={(e) => setProfile({ ...profile, max_daily_trades: e.target.value ? parseInt(e.target.value) : 0 })}
                className="bg-gray-800 border-gray-700 text-white"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Position & Exposure Limits */}
      <Card className="bg-gray-900/50 border-gray-800">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <Layers className="h-5 w-5 text-indigo-400" />
            Position & Exposure Limits
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-2 gap-6">
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">Max Open Positions</span>
                <span className="text-white font-medium">{profile.max_open_positions}</span>
              </div>
              <Slider
                value={[profile.max_open_positions]}
                onValueChange={(v) => setProfile({ ...profile, max_open_positions: v[0] })}
                max={50}
                step={1}
              />
            </div>
            
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">Max Exposure (%)</span>
                <span className="text-white font-medium">{profile.max_exposure_percentage}%</span>
              </div>
              <Slider
                value={[profile.max_exposure_percentage]}
                onValueChange={(v) => setProfile({ ...profile, max_exposure_percentage: v[0] })}
                max={100}
                step={5}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">Per Strategy</span>
                <span className="text-white">{profile.max_per_strategy_allocation}%</span>
              </div>
              <Slider
                value={[profile.max_per_strategy_allocation]}
                onValueChange={(v) => setProfile({ ...profile, max_per_strategy_allocation: v[0] })}
                max={100}
                step={5}
              />
            </div>
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">Per Instrument</span>
                <span className="text-white">{profile.max_per_instrument_exposure}%</span>
              </div>
              <Slider
                value={[profile.max_per_instrument_exposure]}
                onValueChange={(v) => setProfile({ ...profile, max_per_instrument_exposure: v[0] })}
                max={50}
                step={1}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Drawdown Controls */}
      <Card className="bg-gray-900/50 border-gray-800">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <TrendingDown className="h-5 w-5 text-yellow-400" />
            Drawdown Protection
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Max Drawdown (%)</span>
              <span className="text-white font-medium">{profile.max_drawdown_percentage}%</span>
            </div>
            <Slider
              value={[profile.max_drawdown_percentage]}
              onValueChange={(v) => setProfile({ ...profile, max_drawdown_percentage: v[0] })}
              max={50}
              step={1}
            />
          </div>
          
          <div className="flex items-center justify-between">
            <div>
              <p className="text-white">Reset on New High</p>
              <p className="text-sm text-gray-500">Reset drawdown counter when portfolio hits new peak</p>
            </div>
            <Switch 
              checked={profile.trailing_drawdown_reset}
              onCheckedChange={(v) => setProfile({ ...profile, trailing_drawdown_reset: v })}
            />
          </div>
        </CardContent>
      </Card>

      {/* Breach Actions */}
      <Card className="bg-gray-900/50 border-gray-800">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-orange-400" />
            Breach Actions
          </CardTitle>
          <CardDescription>What happens when limits are breached</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-white">Send Alerts</p>
              <p className="text-sm text-gray-500">Notify when approaching or breaching limits</p>
            </div>
            <Switch 
              checked={profile.alert_on_breach}
              onCheckedChange={(v) => setProfile({ ...profile, alert_on_breach: v })}
            />
          </div>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-white">Auto-Halt Trading</p>
              <p className="text-sm text-gray-500">Automatically pause all trading on breach</p>
            </div>
            <Switch 
              checked={profile.halt_on_breach}
              onCheckedChange={(v) => setProfile({ ...profile, halt_on_breach: v })}
            />
          </div>
        </CardContent>
      </Card>
    </div>
  </div>
  <StrategyFooter
    onSave={handleSave}
    onCancel={() => fetchProfile()} // Reload data on cancel to revert
    saving={saving}
  />
</div>
  );
}
