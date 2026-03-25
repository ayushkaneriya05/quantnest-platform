/**
 * Time Rules Editor - trading hours and session configuration
 */
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import { Switch } from "@/shared/components/ui/switch";
import { Badge } from "@/shared/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/components/ui/select";
import { 
  Save, Clock, Calendar, AlertTriangle, 
  Loader2
} from 'lucide-react';
import StrategyConfigNav from './StrategyConfigNav';
import StrategyFooter from './StrategyFooter';
import { timeRuleApi, specialEventApi } from '@/shared/services/rulesApi';
import { strategyApi } from '@/shared/services/strategyApi';
import { useNotifications } from '@/shared/hooks/useNotifications';
import { useEnums } from '@/shared/context/EnumsContext';
import { usePageActions } from '@/shared/context/PageActionsContext'; // Added import

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
const DAY_SHORT = { Monday: 'Mon', Tuesday: 'Tue', Wednesday: 'Wed', Thursday: 'Thu', Friday: 'Fri' };



export default function TimeRulesEditor() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { notify } = useNotifications();
  const { enums } = useEnums();
  const { setPageHeader } = usePageActions(); // Use context
  
  const [strategy, setStrategy] = useState(null);
  const [timeRule, setTimeRule] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [eventFilter, setEventFilter] = useState(null);
  
  const [formData, setFormData] = useState({
    trading_days: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'],
    market_session: 'ALL',
    start_time: '09:15',
    end_time: '15:30',
    candle_timeframe: '5m',
    candle_completion_rule: 'ON_CLOSE',
    timezone: 'Asia/Kolkata',
    avoid_expiry_day: true,
    avoid_earnings: false,
    avoid_news: false,
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
      const [strategyData, rules, events] = await Promise.all([
        strategyApi.getById(id),
        timeRuleApi.get(id),
        specialEventApi.getByStrategy(id).catch(() => []),
      ]);
      setStrategy(strategyData);
      
      if (rules.length > 0) {
        const rule = rules[0];
        setTimeRule(rule);
        setFormData(prev => ({
          ...prev,
          trading_days: rule.trading_days || DAYS,
          market_session: rule.market_session || 'ALL',
          start_time: rule.start_time || '09:15',
          end_time: rule.end_time || '15:30',
          candle_timeframe: rule.candle_timeframe || '5m',
          candle_completion_rule: rule.candle_completion_rule || 'ON_CLOSE',
          timezone: rule.timezone || 'Asia/Kolkata',
        }));
      }

      if (events.length > 0) {
        const ef = events[0];
        setEventFilter(ef);
        setFormData(prev => ({
          ...prev,
          avoid_expiry_day: ef.avoid_expiry_day ?? true,
          avoid_earnings: ef.avoid_earnings ?? false,
          avoid_news: ef.avoid_news ?? false,
        }));
      }
    } catch (error) {
      notify.error('Failed to load time rules');
    } finally {
      setLoading(false);
    }
  };

  const handleDayToggle = (day) => {
    const days = formData.trading_days.includes(day)
      ? formData.trading_days.filter(d => d !== day)
      : [...formData.trading_days, day];
    setFormData({ ...formData, trading_days: days });
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      const timePayload = {
        trading_days: formData.trading_days,
        market_session: formData.market_session,
        start_time: formData.start_time,
        end_time: formData.end_time,
        candle_timeframe: formData.candle_timeframe,
        candle_completion_rule: formData.candle_completion_rule,
        timezone: formData.timezone,
      };
      const eventPayload = {
        avoid_expiry_day: formData.avoid_expiry_day,
        avoid_earnings: formData.avoid_earnings,
        avoid_news: formData.avoid_news,
      };

      // Save time rule
      if (timeRule) {
        await timeRuleApi.update(timeRule.id, timePayload);
      } else {
        await timeRuleApi.create({ strategy: id, ...timePayload });
      }

      // Save special event filters
      if (eventFilter) {
        await specialEventApi.update(eventFilter.id, eventPayload);
      } else {
        await specialEventApi.create({ strategy: id, ...eventPayload });
      }

      notify.success('Time rules saved');
      // navigate removed to keep user on same page
    } catch (error) {
      notify.error('Failed to save time rules');
    } finally {
      setSaving(false);
    }
  };

  // Calculate trading window duration
  const getTradingDuration = () => {
    try {
      const [sh, sm] = formData.start_time.split(':').map(Number);
      const [eh, em] = formData.end_time.split(':').map(Number);
      const mins = (eh * 60 + em) - (sh * 60 + sm);
      if (mins <= 0) return null;
      const hours = Math.floor(mins / 60);
      const remainMins = mins % 60;
      return `${hours}h ${remainMins > 0 ? `${remainMins}m` : ''}`.trim();
    } catch { return null; }
  };

  if (loading) {
    return (
      <div className="flex flex-col justify-center items-center h-96 gap-3">
        <Loader2 className="h-8 w-8 text-amber-400 animate-spin" />
        <p className="text-sm text-gray-400">Loading time rules...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col flex-1 min-h-0">
      <div className="flex-1 overflow-y-auto scrollbar-theme">
        <div className="container-padding py-6 lg:py-8 space-y-6">
      {/* Trading Days */}
      <Card className="bg-gray-900/40 border-gray-800/80">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2 text-base">
            <div className="p-1.5 rounded-lg bg-amber-500/10">
              <Calendar className="h-4 w-4 text-amber-400" />
            </div>
            Trading Days
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            {DAYS.map(day => {
              const isActive = formData.trading_days.includes(day);
              return (
                <button
                  key={day}
                  onClick={() => handleDayToggle(day)}
                  className={`flex-1 py-3 rounded-lg text-sm font-medium transition-all duration-200 border ${
                    isActive 
                      ? 'bg-amber-500/15 text-amber-400 border-amber-500/30 hover:bg-amber-500/20' 
                      : 'bg-gray-800/30 text-gray-500 border-gray-700/50 hover:text-gray-400 hover:border-gray-600'
                  }`}
                >
                  {DAY_SHORT[day]}
                </button>
              );
            })}
          </div>
          <p className="text-xs text-gray-500 mt-3">
            {formData.trading_days.length} of 5 days selected
          </p>
        </CardContent>
      </Card>

      {/* Trading Hours */}
      <Card className="bg-gray-900/40 border-gray-800/80">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2 text-base">
            <div className="p-1.5 rounded-lg bg-amber-500/10">
              <Clock className="h-4 w-4 text-amber-400" />
            </div>
            Trading Hours
            {getTradingDuration() && (
              <Badge variant="outline" className="ml-auto text-xs text-gray-400 border-gray-700/80 font-normal">
                {getTradingDuration()} window
              </Badge>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="space-y-1.5">
              <Label className="text-xs text-gray-500">Start Time</Label>
              <Input
                type="time"
                value={formData.start_time}
                onChange={(e) => setFormData({ ...formData, start_time: e.target.value })}
                className="bg-gray-800/60 border-gray-700 text-white h-9 font-mono text-sm"
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs text-gray-500">End Time</Label>
              <Input
                type="time"
                value={formData.end_time}
                onChange={(e) => setFormData({ ...formData, end_time: e.target.value })}
                className="bg-gray-800/60 border-gray-700 text-white h-9 font-mono text-sm"
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs text-gray-500">Session</Label>
              <Select 
                value={formData.market_session} 
                onValueChange={(v) => setFormData({ ...formData, market_session: v })}
              >
                <SelectTrigger className="bg-gray-800/60 border-gray-700 h-9 text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(enums.MarketSession || []).map(s => (
                    <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs text-gray-500">Candle Timeframe</Label>
              <Select 
                value={formData.candle_timeframe} 
                onValueChange={(v) => setFormData({ ...formData, candle_timeframe: v })}
              >
                <SelectTrigger className="bg-gray-800/60 border-gray-700 h-9 text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(enums.CandleTimeframe || []).map(t => (
                    <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          
          {/* Candle completion & timezone row */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="space-y-1.5">
              <Label className="text-xs text-gray-500">Candle Completion</Label>
              <Select 
                value={formData.candle_completion_rule} 
                onValueChange={(v) => setFormData({ ...formData, candle_completion_rule: v })}
              >
                <SelectTrigger className="bg-gray-800/60 border-gray-700 h-9 text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(enums.CandleCompletionRule || []).map(t => (
                    <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs text-gray-500">Timezone</Label>
              <Input
                value={formData.timezone}
                onChange={(e) => setFormData({ ...formData, timezone: e.target.value })}
                className="bg-gray-800/60 border-gray-700 text-white h-9 text-sm"
                placeholder="Asia/Kolkata"
              />
            </div>
          </div>

          {/* Visual timeline bar */}
          <div className="pt-2">
            <div className="relative h-3 bg-gray-800/60 rounded-full overflow-hidden border border-gray-700/50">
              {(() => {
                const [sh, sm] = formData.start_time.split(':').map(Number);
                const [eh, em] = formData.end_time.split(':').map(Number);
                const startPercent = ((sh * 60 + sm - 540) / (390) * 100); // 9:00 to 15:30 span
                const endPercent = ((eh * 60 + em - 540) / (390) * 100);
                const left = Math.max(0, Math.min(100, startPercent));
                const width = Math.max(0, Math.min(100 - left, endPercent - startPercent));
                return (
                  <div 
                    className="absolute top-0 bottom-0 bg-amber-500/30 rounded-full"
                    style={{ left: `${left}%`, width: `${width}%` }}
                  />
                );
              })()}
            </div>
            <div className="flex justify-between mt-1">
              <span className="text-[10px] text-gray-600">09:00</span>
              <span className="text-[10px] text-gray-600">12:00</span>
              <span className="text-[10px] text-gray-600">15:30</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Special Events */}
      <Card className="bg-gray-900/40 border-gray-800/80">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2 text-base">
            <div className="p-1.5 rounded-lg bg-amber-500/10">
              <AlertTriangle className="h-4 w-4 text-amber-400" />
            </div>
            Avoid Special Events
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-1">
          {[
            { key: 'avoid_expiry_day', label: 'Expiry Days', desc: 'Skip trading on F&O expiry days' },
            { key: 'avoid_earnings', label: 'Earnings Days', desc: 'Avoid stocks with earnings announcements' },
            { key: 'avoid_news', label: 'Major News Events', desc: 'Skip RBI policy, budget days, etc.' },
          ].map(event => (
            <div key={event.key} className="flex items-center justify-between py-3 px-3 rounded-lg hover:bg-gray-800/30 transition-colors">
              <div>
                <p className="text-sm text-white font-medium">{event.label}</p>
                <p className="text-xs text-gray-500 mt-0.5">{event.desc}</p>
              </div>
              <Switch 
                checked={formData[event.key]}
                onCheckedChange={(v) => setFormData({ ...formData, [event.key]: v })}
              />
            </div>
          ))}
        </CardContent>
      </Card>

        </div>
      </div>
      <StrategyFooter
        onSave={handleSave}
        onCancel={() => navigate(`/dashboard/strategy/${id}/edit`)}
        saving={saving}
        saveLabel="Save Time Rules"
        savingLabel="Saving..."
      />
    </div>
  );
}
