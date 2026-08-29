/**
 * Time Rules Editor - trading hours and session configuration
 */
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { TimePicker } from "@/shared/components/ui/time-picker";
import { Label } from "@/shared/components/ui/label";
import { Switch } from "@/shared/components/ui/switch";
import { Badge } from "@/shared/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/components/ui/select";
import { Input } from "@/shared/components/ui/input";
import { Clock, Calendar, AlertTriangle, Plus, Trash2 } from 'lucide-react';
import { Button } from "@/shared/components/ui/button";
import StrategyConfigNav from './StrategyConfigNav';
import StrategyFooter from './StrategyFooter';
import { timeRuleApi, specialEventApi } from '@/shared/services/rulesApi';
import { strategyApi } from '@/shared/services/strategyApi';
import { useNotifications } from '@/shared/hooks/useNotifications';
import { useEnums } from '@/shared/context/EnumsContext';
import { usePageActions } from '@/shared/context/PageActionsContext'; // Added import
import { GlobalLoader } from '@/shared/components/ui/global-loader';

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
const DAY_SHORT = { Monday: 'Mon', Tuesday: 'Tue', Wednesday: 'Wed', Thursday: 'Thu', Friday: 'Fri', Saturday: 'Sat', Sunday: 'Sun' };



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
    trading_days: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
    market_session: 'ALL',
    start_time: '09:15',
    end_time: '15:30',
    candle_timeframe: '5m',
    timezone: 'Asia/Kolkata',
    avoid_earnings: false,
    avoid_news: false,
    avoid_rbi_policy: false,
    custom_avoid_dates: '',
    no_trade_windows: [],
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
          timezone: rule.timezone || 'Asia/Kolkata',
          no_trade_windows: rule.no_trade_windows || [],
        }));
      }

      if (events.length > 0) {
        const ef = events[0];
        setEventFilter(ef);
        setFormData(prev => ({
          ...prev,
          avoid_earnings: ef.avoid_earnings ?? false,
          avoid_news: ef.avoid_news ?? false,
          avoid_rbi_policy: ef.avoid_rbi_policy ?? false,
          custom_avoid_dates: Array.isArray(ef.custom_avoid_dates) ? ef.custom_avoid_dates.join(', ') : (ef.custom_avoid_dates || ''),
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
        timezone: formData.timezone,
        no_trade_windows: formData.no_trade_windows.filter(w => w.start && w.end),
      };
      const eventPayload = {
        avoid_earnings: formData.avoid_earnings,
        avoid_news: formData.avoid_news,
        avoid_rbi_policy: formData.avoid_rbi_policy,
        custom_avoid_dates: formData.custom_avoid_dates ? formData.custom_avoid_dates.split(',').map(d => d.trim()).filter(Boolean) : [],
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

  const getTradingDuration = () => {
    try {
      const [sh, sm] = formData.start_time.split(':').map(Number);
      const [eh, em] = formData.end_time.split(':').map(Number);
      let mins = (eh * 60 + em) - (sh * 60 + sm);
      if (mins <= 0) return null;
      
      // Subtract exclusion zones
      formData.no_trade_windows.forEach(w => {
        if (!w.start || !w.end) return;
        const [wsh, wsm] = w.start.split(':').map(Number);
        const [weh, wem] = w.end.split(':').map(Number);
        const exclMins = (weh * 60 + wem) - (wsh * 60 + wsm);
        if (exclMins > 0) mins -= exclMins;
      });
      
      if (mins <= 0) return '0h';
      const hours = Math.floor(mins / 60);
      const remainMins = mins % 60;
      return `${hours}h ${remainMins > 0 ? `${remainMins}m` : ''}`.trim();
    } catch { return null; }
  };
  
  const handleAddWindow = () => {
    setFormData({
      ...formData,
      no_trade_windows: [...formData.no_trade_windows, { start: '', end: '' }]
    });
  };
  
  const handleUpdateWindow = (index, field, value) => {
    const windows = [...formData.no_trade_windows];
    windows[index] = { ...windows[index], [field]: value };
    setFormData({ ...formData, no_trade_windows: windows });
  };
  
  const handleRemoveWindow = (index) => {
    const windows = [...formData.no_trade_windows];
    windows.splice(index, 1);
    setFormData({ ...formData, no_trade_windows: windows });
  };

  if (loading) {
    return (
      <div className="flex flex-col justify-center items-center h-96 gap-3">
        <GlobalLoader />
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
            {formData.trading_days.length} of 7 days selected
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
              <TimePicker
                value={formData.start_time}
                onChange={(e) => setFormData({ ...formData, start_time: e.target.value })}
                className="bg-gray-800/60 border-gray-700 text-white h-9 font-mono text-sm"
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs text-gray-500">End Time</Label>
              <TimePicker
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
          
          {/* timezone row */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">

            <div className="space-y-1.5">
              <Label className="text-xs text-gray-500">Timezone</Label>
              <Select 
                value={formData.timezone} 
                onValueChange={(v) => setFormData({ ...formData, timezone: v })}
              >
                <SelectTrigger className="bg-gray-800/60 border-gray-700 h-9 text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(enums.Timezone || [
                    { value: 'Asia/Kolkata', label: 'Asia/Kolkata' },
                    { value: 'UTC', label: 'UTC' }
                  ]).map(t => (
                    <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Visual timeline bar */}
          <div className="pt-2">
            <div className="relative h-3 bg-gray-800/60 rounded-full overflow-hidden border border-gray-700/50">
              {(() => {
                const [sh, sm] = formData.start_time.split(':').map(Number);
                const [eh, em] = formData.end_time.split(':').map(Number);
                const startPercent = ((sh * 60 + sm) / 1440 * 100);
                const endPercent = ((eh * 60 + em) / 1440 * 100);
                const left = Math.max(0, Math.min(100, startPercent));
                const width = Math.max(0, Math.min(100 - left, endPercent - startPercent));
                
                return (
                  <>
                    {/* Active Window */}
                    <div 
                      className="absolute top-0 bottom-0 bg-amber-500/30 rounded-full"
                      style={{ left: `${left}%`, width: `${width}%` }}
                    />
                    {/* Exclusion Zones */}
                    {formData.no_trade_windows.map((w, idx) => {
                      if (!w.start || !w.end) return null;
                      const [wsh, wsm] = w.start.split(':').map(Number);
                      const [weh, wem] = w.end.split(':').map(Number);
                      if (isNaN(wsh) || isNaN(weh)) return null;
                      
                      const wStartPercent = ((wsh * 60 + wsm) / 1440 * 100);
                      const wEndPercent = ((weh * 60 + wem) / 1440 * 100);
                      const wLeft = Math.max(0, Math.min(100, wStartPercent));
                      const wWidth = Math.max(0, Math.min(100 - wLeft, wEndPercent - wStartPercent));
                      
                      return (
                        <div 
                          key={idx}
                          className="absolute top-0 bottom-0 bg-red-500/80 rounded-full border-x border-gray-900 z-10"
                          style={{ left: `${wLeft}%`, width: `${wWidth}%` }}
                        />
                      );
                    })}
                  </>
                );
              })()}
            </div>
            <div className="flex justify-between mt-1">
              <span className="text-[10px] text-gray-600">00:00</span>
              <span className="text-[10px] text-gray-600">06:00</span>
              <span className="text-[10px] text-gray-600">12:00</span>
              <span className="text-[10px] text-gray-600">18:00</span>
              <span className="text-[10px] text-gray-600">23:59</span>
            </div>
          </div>
          
          {/* No Trade Windows Builder */}
          <div className="pt-4 border-t border-gray-800/80">
            <div className="flex items-center justify-between mb-3">
              <Label className="text-sm text-gray-300">Exclusion Zones (No Trade Windows)</Label>
              <Button onClick={handleAddWindow} variant="outline" size="sm" className="h-7 text-xs bg-gray-800/40 border-gray-700/80">
                <Plus className="h-3 w-3 mr-1" /> Add Zone
              </Button>
            </div>
            {formData.no_trade_windows.length === 0 ? (
              <p className="text-xs text-gray-500 italic">No exclusion zones defined. Strategy can trade freely within active hours.</p>
            ) : (
              <div className="space-y-3">
                {formData.no_trade_windows.map((w, index) => (
                  <div key={index} className="flex items-center gap-3">
                    <TimePicker
                      value={w.start}
                      onChange={(e) => handleUpdateWindow(index, 'start', e.target.value)}
                      className="bg-gray-800/60 border-gray-700 text-white h-8 font-mono text-xs w-28"
                    />
                    <span className="text-gray-500 text-xs">to</span>
                    <TimePicker
                      value={w.end}
                      onChange={(e) => handleUpdateWindow(index, 'end', e.target.value)}
                      className="bg-gray-800/60 border-gray-700 text-white h-8 font-mono text-xs w-28"
                    />
                    <Button 
                      variant="ghost" 
                      size="icon" 
                      className="h-8 w-8 text-gray-500 hover:text-red-400 hover:bg-red-500/10"
                      onClick={() => handleRemoveWindow(index)}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
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
            { key: 'avoid_earnings', label: 'Earnings Days', desc: 'Avoid stocks with earnings announcements' },
            { key: 'avoid_news', label: 'Major News Events', desc: 'Skip budget days, macroeconomic announcements, etc.' },
            { key: 'avoid_rbi_policy', label: 'RBI Policy Days', desc: 'Avoid trading during RBI rate announcements' },
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
          
          <div className="pt-3 px-3">
            <Label className="text-xs text-gray-500 mb-1.5 block">Custom Avoid Dates</Label>
            <Input 
              value={formData.custom_avoid_dates}
              onChange={(e) => setFormData({ ...formData, custom_avoid_dates: e.target.value })}
              placeholder="e.g. 2024-01-26, 2024-08-15"
              className="bg-gray-800/60 border-gray-700/80 text-sm text-white h-9"
            />
            <p className="text-[10px] text-gray-600 mt-1.5">Enter dates in YYYY-MM-DD format separated by commas</p>
          </div>
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
