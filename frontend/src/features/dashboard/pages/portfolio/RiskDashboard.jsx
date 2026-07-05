import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import { Badge } from "@/shared/components/ui/badge";
import { Input } from "@/shared/components/ui/input";
import { ShieldAlert, CheckCircle2, AlertTriangle, AlertOctagon, Clock, Loader2 } from 'lucide-react';
import { riskApi } from '@/shared/services/portfolioApi';
import { useNotifications } from '@/shared/hooks/useNotifications';
import { usePageActions } from '@/shared/context/PageActionsContext';
import { useLiveTradingWebSocket } from '@/shared/hooks/useLiveTradingWebSocket';
import { formatDistanceToNow, format } from 'date-fns';
import PortfolioRiskNav from './PortfolioRiskNav';
import { GlobalLoader } from '@/shared/components/ui/global-loader';

export default function RiskDashboard() {
  const { notify } = useNotifications();
  const { setPageHeader } = usePageActions();
  const [violations, setViolations] = useState([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    setPageHeader(<PortfolioRiskNav />);
    return () => setPageHeader(null);
  }, [setPageHeader]);
  
  const [resolvingId, setResolvingId] = useState(null);
  const [resolutionNotes, setResolutionNotes] = useState('');

  const handleLiveUpdate = useCallback((payload) => {
    if (payload?.event_type === 'RISK_VIOLATION' || payload?.event_type === 'AUTO_DISABLE') {
      fetchData();
      notify.warning('New risk violation detected', { duration: 5000 });
    }
  }, [notify]);

  useLiveTradingWebSocket(handleLiveUpdate);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [violRes] = await Promise.all([riskApi.getViolations()]);
      setViolations(violRes.data || []);
    } catch (error) {
      notify.error('Failed to load risk violations');
    } finally {
      setLoading(false);
    }
  };

  const handleResolve = async (id) => {
    try {
      await riskApi.resolveViolation(id, resolutionNotes);
      notify.success('Violation resolved successfully');
      setResolvingId(null);
      setResolutionNotes('');
      fetchData();
    } catch (error) {
      notify.error('Failed to resolve violation');
    }
  };

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'CRITICAL': return 'bg-rose-500/20 text-rose-400 border border-rose-500/30';
      case 'WARNING': return 'bg-amber-500/20 text-amber-400 border border-amber-500/30';
      case 'INFO': return 'bg-blue-500/20 text-blue-400 border border-blue-500/30';
      default: return 'bg-gray-500/20 text-gray-400 border border-gray-500/30';
    }
  };

  const getSeverityIcon = (severity) => {
    switch (severity) {
      case 'CRITICAL': return <AlertOctagon className="h-4 w-4 text-rose-500" />;
      case 'WARNING': return <AlertTriangle className="h-4 w-4 text-amber-500" />;
      default: return <ShieldAlert className="h-4 w-4 text-blue-500" />;
    }
  };

  if (loading) {
    return (
      <GlobalLoader />
    );
  }

  const activeViolations = violations.filter(v => !v.is_resolved);
  const resolvedViolations = violations.filter(v => v.is_resolved);

  return (
    <div className="container-padding py-6 lg:py-8 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <ShieldAlert className="h-6 w-6 text-indigo-400" />
            Risk Compliance Dashboard
          </h1>
          <p className="text-gray-400 mt-1 text-sm">Monitor account-wide risk breaches and strategy safeguard events.</p>
        </div>
      </div>

      {activeViolations.length === 0 ? (
        <Card className="bg-emerald-900/10 border-emerald-900/50">
          <CardContent className="h-48 flex flex-col items-center justify-center text-center">
            <CheckCircle2 className="h-12 w-12 text-emerald-500 mb-4" />
            <h3 className="text-lg font-medium text-emerald-100 mb-1">System limits look healthy</h3>
            <p className="text-sm text-emerald-500/80">No active risk violations require your attention.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          <h2 className="text-lg font-medium text-white px-1">Active Alerts ({activeViolations.length})</h2>
          {activeViolations.map(v => (
            <Card key={v.id} className="bg-gray-900 border-gray-800 lg:border-l-4" style={{borderLeftColor: v.severity === 'CRITICAL' ? '#f43f5e' : v.severity === 'WARNING' ? '#fbbf24' : '#3b82f6'}}>
              <CardContent className="p-4 sm:p-6">
                <div className="flex flex-col sm:flex-row gap-4 justify-between sm:items-start">
                  <div className="space-y-2 flex-1">
                    <div className="flex items-center gap-2">
                      {getSeverityIcon(v.severity)}
                      <Badge variant="outline" className={`text-[10px] uppercase font-bold ${getSeverityColor(v.severity)}`}>
                        {v.severity}
                      </Badge>
                      <span className="text-sm font-medium text-gray-300">
                        {v.strategy_name || 'Portfolio Level'}
                      </span>
                      <span className="text-xs text-gray-500 flex items-center gap-1 ml-auto sm:ml-2">
                        <Clock className="h-3 w-3" />
                        {formatDistanceToNow(new window.Date(v.created_at), {addSuffix: true})}
                      </span>
                    </div>
                    
                    <h3 className="text-base text-white font-medium">{v.violation_type.replace(/_/g, ' ')}</h3>
                    <p className="text-sm text-gray-400 max-w-2xl">{v.message}</p>
                  </div>

                  {resolvingId === v.id ? (
                    <div className="min-w-[280px] space-y-2 bg-gray-800/50 p-3 rounded-lg border border-gray-700">
                      <Input 
                        placeholder="Resolution notes... (optional)" 
                        value={resolutionNotes}
                        onChange={(e) => setResolutionNotes(e.target.value)}
                        className="bg-gray-900 text-sm border-gray-700 h-9"
                      />
                      <div className="flex gap-2">
                        <Button size="sm" onClick={() => handleResolve(v.id)} className="flex-1 bg-emerald-600 hover:bg-emerald-700 h-8">Resolve</Button>
                        <Button size="sm" variant="ghost" onClick={() => setResolvingId(null)} className="flex-1 h-8">Cancel</Button>
                      </div>
                    </div>
                  ) : (
                    <Button onClick={() => setResolvingId(v.id)} variant="outline" className="border-gray-700 whitespace-nowrap">
                      Mark Resolved
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {resolvedViolations.length > 0 && (
        <div className="pt-8 space-y-4">
          <h2 className="text-lg font-medium text-gray-300 px-1">Recent History</h2>
          <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="text-xs text-gray-500 uppercase bg-gray-800/50">
                  <tr>
                    <th className="px-4 py-3 font-medium">Date</th>
                    <th className="px-4 py-3 font-medium">Severity</th>
                    <th className="px-4 py-3 font-medium">Type</th>
                    <th className="px-4 py-3 font-medium">Target</th>
                    <th className="px-4 py-3 font-medium">Resolution Note</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800 text-gray-300">
                  {resolvedViolations.map(v => (
                    <tr key={v.id} className="hover:bg-gray-800/30">
                      <td className="px-4 py-3 whitespace-nowrap">
                        {format(new window.Date(v.created_at), "MMM d, HH:mm")}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${getSeverityColor(v.severity)}`}>
                          {v.severity.substring(0, 1)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-400">{v.violation_type.replace(/_/g, ' ')}</td>
                      <td className="px-4 py-3 truncate max-w-[150px]" title={v.strategy_name || 'Portfolio Level'}>
                        {v.strategy_name || 'Portfolio Level'}
                      </td>
                      <td className="px-4 py-3 text-gray-400 italic truncate max-w-[200px]" title={v.resolution_notes}>
                        {v.resolution_notes || '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
