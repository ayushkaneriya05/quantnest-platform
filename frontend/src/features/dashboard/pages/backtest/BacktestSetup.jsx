/**
 * Backtest Setup - configure and run a new backtest
 */
import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/components/ui/select";
import { 
  Play, Settings, Calendar, DollarSign, TrendingUp
} from 'lucide-react';
import { backtestApi } from '@/shared/services/backtestApi';
import { strategyApi } from '@/shared/services/strategyApi';
import { useNotifications } from '@/shared/hooks/useNotifications';
import { useEnums } from '@/shared/context/EnumsContext';


export default function BacktestSetup() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { notify } = useNotifications();
  const { enums } = useEnums();
  const TIMEFRAMES = enums.CandleTimeframe || [];
  const [strategies, setStrategies] = useState([]);
  const [loading, setLoading] = useState(false);
  
  // Pre-select strategy from URL param if provided
  const preSelectedStrategy = searchParams.get('strategy') || '';
  
  const [formData, setFormData] = useState({
    name: '',
    strategy: preSelectedStrategy,
    start_date: '',
    end_date: '',
    initial_capital: 100000,
    slippage_pct: 0.01,
    brokerage_per_trade: 20,
    brokerage_pct: 0.03,
    data_resolution: '5m',
  });

  useEffect(() => {
    fetchStrategies();
  }, []);

  useEffect(() => {
    // Update form when URL param changes and strategies are loaded
    if (preSelectedStrategy && strategies.length > 0) {
      const strategy = strategies.find(s => s.id.toString() === preSelectedStrategy);
      if (strategy) {
        setFormData(prev => ({ 
          ...prev, 
          strategy: preSelectedStrategy,
          name: `${strategy.name} - Backtest`
        }));
      }
    }
  }, [preSelectedStrategy, strategies]);

  const fetchStrategies = async () => {
    try {
      const response = await strategyApi.getAll();
      setStrategies(response.data || response);
    } catch (error) {
      notify.error('Failed to load strategies');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.strategy || !formData.start_date || !formData.end_date) {
      notify.error('Please fill all required fields');
      return;
    }
    
    try {
      setLoading(true);
      const response = await backtestApi.createRun(formData);
      notify.success('Backtest created! Starting...');
      
      // Start the backtest
      await backtestApi.startRun(response.data.id);
      navigate(`/dashboard/backtest/results/${response.data.id}`);
    } catch (error) {
      notify.error('Failed to create backtest');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (field, value) => {
    setFormData({ ...formData, [field]: value });
  };

  return (
    <div className="container-padding py-6 lg:py-8 space-y-6">
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Strategy Selection */}
        <Card className="bg-gray-900/50 border-gray-800">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-indigo-400" />
              Strategy Selection
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="text-gray-400">Strategy *</Label>
                <Select 
                  value={formData.strategy} 
                  onValueChange={(v) => handleChange('strategy', v)}
                >
                  <SelectTrigger className="bg-gray-800 border-gray-700">
                    <SelectValue placeholder="Select a strategy" />
                  </SelectTrigger>
                  <SelectContent>
                    {strategies.map(s => (
                      <SelectItem key={s.id} value={s.id.toString()}>{s.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label className="text-gray-400">Backtest Name *</Label>
                <Input
                  value={formData.name}
                  onChange={(e) => handleChange('name', e.target.value)}
                  placeholder="e.g., EMA Crossover - 2024"
                  className="bg-gray-800 border-gray-700 text-white"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Date Range */}
        <Card className="bg-gray-900/50 border-gray-800">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Calendar className="h-5 w-5 text-indigo-400" />
              Date Range
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label className="text-gray-400">Start Date *</Label>
                <Input
                  type="date"
                  value={formData.start_date}
                  onChange={(e) => handleChange('start_date', e.target.value)}
                  className="bg-gray-800 border-gray-700 text-white"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-gray-400">End Date *</Label>
                <Input
                  type="date"
                  value={formData.end_date}
                  onChange={(e) => handleChange('end_date', e.target.value)}
                  className="bg-gray-800 border-gray-700 text-white"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-gray-400">Data Resolution</Label>
                <Select 
                  value={formData.data_resolution} 
                  onValueChange={(v) => handleChange('data_resolution', v)}
                >
                  <SelectTrigger className="bg-gray-800 border-gray-700">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {TIMEFRAMES.map(tf => (
                      <SelectItem key={tf.value} value={tf.value}>{tf.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Capital & Costs */}
        <Card className="bg-gray-900/50 border-gray-800">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <DollarSign className="h-5 w-5 text-indigo-400" />
              Capital & Costs
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="space-y-2">
                <Label className="text-gray-400">Initial Capital (₹)</Label>
                <Input
                  type="number"
                  value={formData.initial_capital}
                  onChange={(e) => handleChange('initial_capital', parseFloat(e.target.value))}
                  className="bg-gray-800 border-gray-700 text-white"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-gray-400">Slippage (%)</Label>
                <Input
                  type="number"
                  step="0.01"
                  value={formData.slippage_pct}
                  onChange={(e) => handleChange('slippage_pct', parseFloat(e.target.value))}
                  className="bg-gray-800 border-gray-700 text-white"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-gray-400">Brokerage/Trade (₹)</Label>
                <Input
                  type="number"
                  value={formData.brokerage_per_trade}
                  onChange={(e) => handleChange('brokerage_per_trade', parseFloat(e.target.value))}
                  className="bg-gray-800 border-gray-700 text-white"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-gray-400">Brokerage (%)</Label>
                <Input
                  type="number"
                  step="0.001"
                  value={formData.brokerage_pct}
                  onChange={(e) => handleChange('brokerage_pct', parseFloat(e.target.value))}
                  className="bg-gray-800 border-gray-700 text-white"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Submit */}
        <div className="flex justify-end">
          <Button 
            type="submit" 
            disabled={loading}
            className="bg-indigo-600 hover:bg-indigo-700"
          >
            <Play className="h-4 w-4 mr-1" />
            {loading ? 'Starting...' : 'Run Backtest'}
          </Button>
        </div>
      </form>
    </div>
  );
}
