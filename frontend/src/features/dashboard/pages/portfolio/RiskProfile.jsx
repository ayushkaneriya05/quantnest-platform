import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/shared/components/ui/card";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import { Switch } from "@/shared/components/ui/switch";
import { Slider } from "@/shared/components/ui/slider";
import { AlertTriangle, DollarSign, Shield, TrendingDown } from 'lucide-react';
import { riskApi } from '@/shared/services/portfolioApi';
import { useNotifications } from '@/shared/hooks/useNotifications';
import { usePageActions } from '@/shared/context/PageActionsContext';
import PortfolioRiskNav from './PortfolioRiskNav';
import StrategyFooter from '@/features/dashboard/pages/strategy/StrategyFooter';
import { GlobalLoader } from '@/shared/components/ui/global-loader';

const DEFAULT_PROFILE = {
  max_daily_loss_percentage: 5,
  max_daily_loss_amount: null,
  max_exposure_percentage: 80,
  max_per_instrument_exposure: 10,
  max_drawdown_percentage: 15,
  alert_on_breach: true,
};

export default function RiskProfile() {
  const { notify } = useNotifications();
  const { setPageHeader } = usePageActions();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [profile, setProfile] = useState(DEFAULT_PROFILE);

  useEffect(() => {
    setPageHeader(<PortfolioRiskNav />);
    return () => setPageHeader(null);
  }, [setPageHeader]);

  const fetchProfile = async () => {
    try {
      setLoading(true);
      const response = await riskApi.getMyProfile();
      if (response.data) {
        setProfile({ ...DEFAULT_PROFILE, ...response.data });
      }
    } catch (error) {
      setProfile(DEFAULT_PROFILE);
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
      Object.keys(payload).forEach((key) => {
        if (Number.isNaN(payload[key])) {
          payload[key] = key === 'max_daily_loss_amount' ? null : 0;
        }
      });
      await riskApi.updateProfile(payload);
      notify.success('Portfolio risk profile saved');
    } catch (error) {
      const errMsg = error.response?.data ? JSON.stringify(error.response.data) : error.message;
      notify.error(`Save failed: ${errMsg}`);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-96">
        <GlobalLoader />
      </div>
    );
  }

  return (
    <div className="flex flex-col flex-1 min-h-0 bg-black/20">
      <div className="flex-1 overflow-y-auto scrollbar-theme">
        <div className="container-padding py-6 lg:py-8 space-y-8">
          
          <div className="mb-2">
            <h2 className="text-2xl font-bold text-white">Portfolio Risk Controls</h2>
            <p className="text-gray-400 mt-1">Configure global safety nets, maximum exposures, and drawdown limits across all your strategies.</p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card className="bg-gray-900/60 border-gray-800 shadow-lg hover:border-gray-700 transition-colors">
              <CardHeader className="pb-4">
                <CardTitle className="text-white flex items-center gap-3">
                  <div className="p-2 bg-red-500/10 rounded-lg">
                    <DollarSign className="h-5 w-5 text-red-400" />
                  </div>
                  Daily Loss Protection
                </CardTitle>
                <CardDescription>Halt trading if daily losses exceed these thresholds.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-8">
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <Label className="text-gray-300 font-medium">Max Daily Loss (%)</Label>
                    <div className="flex items-center gap-2">
                      <Input
                        type="number"
                        className="w-20 bg-gray-950 border-gray-700 text-right h-8"
                        value={profile.max_daily_loss_percentage}
                        onChange={(e) => setProfile({ ...profile, max_daily_loss_percentage: Number(e.target.value) })}
                        max={100}
                        min={0}
                      />
                      <span className="text-gray-500 font-medium">%</span>
                    </div>
                  </div>
                  <Slider
                    value={[profile.max_daily_loss_percentage]}
                    onValueChange={(v) => setProfile({ ...profile, max_daily_loss_percentage: v[0] })}
                    max={100}
                    step={0.5}
                    className="py-2 cursor-pointer"
                  />
                </div>

                <div className="space-y-3">
                  <Label className="text-gray-300 font-medium">Absolute Max Daily Loss (₹)</Label>
                  <Input
                    type="number"
                    value={profile.max_daily_loss_amount || ''}
                    onChange={(e) => setProfile({ ...profile, max_daily_loss_amount: e.target.value ? parseFloat(e.target.value) : null })}
                    placeholder="e.g. 50000 (Optional)"
                    className="bg-gray-950 border-gray-700 text-white"
                  />
                  <p className="text-xs text-gray-500">Optional fixed currency cap. Leaves empty for % based only.</p>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-gray-900/60 border-gray-800 shadow-lg hover:border-gray-700 transition-colors">
              <CardHeader className="pb-4">
                <CardTitle className="text-white flex items-center gap-3">
                  <div className="p-2 bg-indigo-500/10 rounded-lg">
                    <Shield className="h-5 w-5 text-indigo-400" />
                  </div>
                  Exposure Limits
                </CardTitle>
                <CardDescription>Control maximum capital deployment and leverage.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-8">
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <Label className="text-gray-300 font-medium">Max Portfolio Exposure</Label>
                    <div className="flex items-center gap-2">
                      <Input
                        type="number"
                        className="w-20 bg-gray-950 border-gray-700 text-right h-8"
                        value={profile.max_exposure_percentage}
                        onChange={(e) => setProfile({ ...profile, max_exposure_percentage: Number(e.target.value) })}
                        max={500}
                        min={0}
                      />
                      <span className="text-gray-500 font-medium">%</span>
                    </div>
                  </div>
                  <Slider
                    value={[profile.max_exposure_percentage]}
                    onValueChange={(v) => setProfile({ ...profile, max_exposure_percentage: v[0] })}
                    max={500}
                    step={5}
                    className="py-2 cursor-pointer"
                  />
                  <p className="text-[10px] text-gray-500">Allows &gt; 100% for margin/leverage trading.</p>
                </div>

                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <Label className="text-gray-300 font-medium">Per Instrument Exposure</Label>
                    <div className="flex items-center gap-2">
                      <Input
                        type="number"
                        className="w-20 bg-gray-950 border-gray-700 text-right h-8"
                        value={profile.max_per_instrument_exposure}
                        onChange={(e) => setProfile({ ...profile, max_per_instrument_exposure: Number(e.target.value) })}
                        max={200}
                        min={0}
                      />
                      <span className="text-gray-500 font-medium">%</span>
                    </div>
                  </div>
                  <Slider
                    value={[profile.max_per_instrument_exposure]}
                    onValueChange={(v) => setProfile({ ...profile, max_per_instrument_exposure: v[0] })}
                    max={200}
                    step={1}
                    className="py-2 cursor-pointer"
                  />
                </div>
              </CardContent>
            </Card>

            <Card className="bg-gray-900/60 border-gray-800 shadow-lg hover:border-gray-700 transition-colors">
              <CardHeader className="pb-4">
                <CardTitle className="text-white flex items-center gap-3">
                  <div className="p-2 bg-yellow-500/10 rounded-lg">
                    <TrendingDown className="h-5 w-5 text-yellow-400" />
                  </div>
                  Drawdown Protection
                </CardTitle>
                <CardDescription>Max peak-to-trough drop allowed before halting.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-8">
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <Label className="text-gray-300 font-medium">Max Drawdown</Label>
                    <div className="flex items-center gap-2">
                      <Input
                        type="number"
                        className="w-20 bg-gray-950 border-gray-700 text-right h-8"
                        value={profile.max_drawdown_percentage}
                        onChange={(e) => setProfile({ ...profile, max_drawdown_percentage: Number(e.target.value) })}
                        max={100}
                        min={0}
                      />
                      <span className="text-gray-500 font-medium">%</span>
                    </div>
                  </div>
                  <Slider
                    value={[profile.max_drawdown_percentage]}
                    onValueChange={(v) => setProfile({ ...profile, max_drawdown_percentage: v[0] })}
                    max={100}
                    step={1}
                    className="py-2 cursor-pointer"
                  />
                </div>
              </CardContent>
            </Card>

            <Card className="bg-gray-900/60 border-gray-800 shadow-lg hover:border-gray-700 transition-colors">
              <CardHeader className="pb-4">
                <CardTitle className="text-white flex items-center gap-3">
                  <div className="p-2 bg-orange-500/10 rounded-lg">
                    <AlertTriangle className="h-5 w-5 text-orange-400" />
                  </div>
                  Breach Alerts
                </CardTitle>
                <CardDescription>Notifications for account-wide risk violations.</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between p-4 bg-gray-950/50 rounded-xl border border-gray-800">
                  <div>
                    <p className="text-white font-medium">Enable Alerts</p>
                    <p className="text-xs text-gray-500 mt-1">Receive system notifications immediately when any risk profile limit is breached.</p>
                  </div>
                  <Switch
                    checked={profile.alert_on_breach}
                    onCheckedChange={(v) => setProfile({ ...profile, alert_on_breach: v })}
                  />
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
      <StrategyFooter
        onSave={handleSave}
        onCancel={fetchProfile}
        saving={saving}
      />
    </div>
  );
}
