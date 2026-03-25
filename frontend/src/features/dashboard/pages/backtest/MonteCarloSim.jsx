/**
 * Monte Carlo Simulation - statistical analysis of backtest results
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/components/ui/select";
import { Badge } from "@/shared/components/ui/badge";
import { 
  Play, Dices, BarChart2, TrendingUp, Activity
} from 'lucide-react';
import { backtestApi } from '@/shared/services/backtestApi';
import { useNotifications } from '@/shared/hooks/useNotifications';

export default function MonteCarloSim() {
  const { notify } = useNotifications();
  const [backtestRuns, setBacktestRuns] = useState([]);
  const [monteCarloRuns, setMonteCarloRuns] = useState([]);
  const [selectedRun, setSelectedRun] = useState(null);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  
  const [formData, setFormData] = useState({
    backtest_run: '',
    num_simulations: 1000,
    confidence_level: 0.95,
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [runsData, mcData] = await Promise.all([
        backtestApi.getRuns(),
        backtestApi.getMonteCarloRuns()
      ]);
      setBacktestRuns(runsData.data.filter(r => r.status === 'COMPLETED'));
      setMonteCarloRuns(mcData.data);
    } catch (error) {
      notify.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.backtest_run) {
      notify.error('Please select a backtest run');
      return;
    }
    
    try {
      const response = await backtestApi.createMonteCarlo(formData);
      notify.success('Monte Carlo simulation started!');
      await backtestApi.startMonteCarlo(response.data.id);
      setShowForm(false);
      fetchData();
    } catch (error) {
      notify.error('Failed to start simulation');
    }
  };

  const viewResults = async (mcRun) => {
    try {
      setSelectedRun(mcRun);
      const response = await backtestApi.getMonteCarloResults(mcRun.id);
      setResults(response.data);
    } catch (error) {
      notify.error('Failed to load results');
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
    <div className="container-padding py-6 lg:py-8 space-y-6">
      {/* New Simulation Form */}
      {showForm && (
        <Card className="bg-gray-900/50 border-gray-800">
          <CardHeader>
            <CardTitle className="text-white">Configure Simulation</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label className="text-gray-400">Backtest Run *</Label>
                  <Select 
                    value={formData.backtest_run} 
                    onValueChange={(v) => setFormData({ ...formData, backtest_run: v })}
                  >
                    <SelectTrigger className="bg-gray-800 border-gray-700">
                      <SelectValue placeholder="Select completed backtest" />
                    </SelectTrigger>
                    <SelectContent>
                      {backtestRuns.map(r => (
                        <SelectItem key={r.id} value={r.id.toString()}>{r.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label className="text-gray-400">Simulations</Label>
                  <Input
                    type="number"
                    value={formData.num_simulations}
                    onChange={(e) => setFormData({ ...formData, num_simulations: parseInt(e.target.value) })}
                    className="bg-gray-800 border-gray-700 text-white"
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-gray-400">Confidence Level</Label>
                  <Select 
                    value={formData.confidence_level.toString()} 
                    onValueChange={(v) => setFormData({ ...formData, confidence_level: parseFloat(v) })}
                  >
                    <SelectTrigger className="bg-gray-800 border-gray-700">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="0.90">90%</SelectItem>
                      <SelectItem value="0.95">95%</SelectItem>
                      <SelectItem value="0.99">99%</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => setShowForm(false)} className="border-gray-700">
                  Cancel
                </Button>
                <Button type="submit" className="bg-indigo-600">
                  <Play className="h-4 w-4 mr-1" />
                  Run Simulation
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Results Display */}
      {selectedRun && results.length > 0 && (
        <Card className="bg-gray-900/50 border-gray-800">
          <CardHeader>
            <CardTitle className="text-white">
              Results: {monteCarloRuns.find(m => m.id === selectedRun.id)?.backtest_run_name || 'Simulation'}
            </CardTitle>
            <CardDescription>
              {selectedRun.num_simulations} simulations at {(selectedRun.confidence_level * 100).toFixed(0)}% confidence
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {results.map((result) => (
                <div key={result.id} className="p-4 bg-gray-800/50 rounded-lg">
                  <h4 className="text-white font-medium mb-3">{result.metric_name}</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-400">Mean</span>
                      <span className="text-white">{parseFloat(result.mean_value).toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Median</span>
                      <span className="text-white">{parseFloat(result.median_value).toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Std Dev</span>
                      <span className="text-white">{parseFloat(result.std_dev).toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">5th Percentile</span>
                      <span className="text-red-400">{parseFloat(result.percentile_5).toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">95th Percentile</span>
                      <span className="text-green-400">{parseFloat(result.percentile_95).toFixed(2)}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Simulation History */}
      <Card className="bg-gray-900/50 border-gray-800">
        <CardHeader>
          <CardTitle className="text-white">Simulation History</CardTitle>
        </CardHeader>
        <CardContent>
          {monteCarloRuns.length === 0 ? (
            <div className="py-8 text-center text-gray-500">
              No simulations yet
            </div>
          ) : (
            <div className="space-y-3">
              {monteCarloRuns.map((mc) => (
                <div 
                  key={mc.id}
                  className="flex items-center justify-between p-4 bg-gray-800/50 rounded-lg cursor-pointer hover:bg-gray-800"
                  onClick={() => viewResults(mc)}
                >
                  <div>
                    <p className="text-white font-medium">
                      {backtestRuns.find(r => r.id === mc.backtest_run)?.name || `Backtest #${mc.backtest_run}`}
                    </p>
                    <p className="text-sm text-gray-400">
                      {mc.num_simulations} simulations • {(mc.confidence_level * 100).toFixed(0)}% confidence
                    </p>
                  </div>
                  <Badge className={mc.status === 'COMPLETED' ? 'bg-green-600' : 'bg-blue-600'}>
                    {mc.status}
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
