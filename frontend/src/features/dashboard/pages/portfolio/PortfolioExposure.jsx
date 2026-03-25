/**
 * Portfolio Exposure - current market exposure breakdown
 */
import { useState, useEffect, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { Badge } from "@/shared/components/ui/badge";
import { 
  Activity, TrendingUp, TrendingDown, BarChart2, 
  PieChart, Clock, RefreshCw
} from 'lucide-react';
import { Button } from "@/shared/components/ui/button";
import { portfolioApi } from '@/shared/services/portfolioApi';
import { useNotifications } from '@/shared/hooks/useNotifications';
import { useSetPageActions } from '@/shared/hooks/useSetPageActions';

export default function PortfolioExposure() {
  const { notify } = useNotifications();
  const [portfolio, setPortfolio] = useState(null);
  const [exposure, setExposure] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [portfolioData, exposureData] = await Promise.all([
        portfolioApi.getMyPortfolio(),
        portfolioApi.getLatestExposure()
      ]);
      setPortfolio(portfolioData.data);
      setExposure(exposureData.data);
    } catch (error) {
      notify.error('Failed to load exposure data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Set page actions in header
  const pageActions = useMemo(() => (
    <Button 
      onClick={fetchData}
      variant="outline"
      className="border-gray-700"
      size="sm"
    >
      <RefreshCw className="h-4 w-4 mr-1" />
      Refresh
    </Button>
  ), []);

  useSetPageActions(pageActions);

  const formatCurrency = (val) => {
    return new Intl.NumberFormat('en-IN', { 
      style: 'currency', currency: 'INR', maximumFractionDigits: 0 
    }).format(val || 0);
  };

  const formatTime = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString('en-IN', {
      day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'
    });
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
      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-indigo-500/20 rounded-lg">
                <Activity className="h-5 w-5 text-indigo-400" />
              </div>
              <div>
                <p className="text-xs text-gray-400">Total Exposure</p>
                <p className="text-lg font-bold text-white">
                  {formatCurrency(exposure?.total_exposure)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-500/20 rounded-lg">
                <BarChart2 className="h-5 w-5 text-blue-400" />
              </div>
              <div>
                <p className="text-xs text-gray-400">Exposure %</p>
                <p className="text-lg font-bold text-white">
                  {(exposure?.exposure_percentage || 0).toFixed(1)}%
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-500/20 rounded-lg">
                <TrendingUp className="h-5 w-5 text-green-400" />
              </div>
              <div>
                <p className="text-xs text-gray-400">Long</p>
                <p className="text-lg font-bold text-green-400">
                  {formatCurrency(exposure?.long_exposure)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-red-500/20 rounded-lg">
                <TrendingDown className="h-5 w-5 text-red-400" />
              </div>
              <div>
                <p className="text-xs text-gray-400">Short</p>
                <p className="text-lg font-bold text-red-400">
                  {formatCurrency(exposure?.short_exposure)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-500/20 rounded-lg">
                <BarChart2 className="h-5 w-5 text-purple-400" />
              </div>
              <div>
                <p className="text-xs text-gray-400">Net Exposure</p>
                <p className={`text-lg font-bold ${parseFloat(exposure?.net_exposure || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {formatCurrency(exposure?.net_exposure)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-amber-500/20 rounded-lg">
                <PieChart className="h-5 w-5 text-amber-400" />
              </div>
              <div>
                <p className="text-xs text-gray-400">Open Positions</p>
                <p className="text-lg font-bold text-white">
                  {exposure?.open_positions_count || 0}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Breakdown Cards */}
      <div className="grid md:grid-cols-3 gap-6">
        {/* By Asset Type */}
        <Card className="bg-gray-900/50 border-gray-800">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <PieChart className="h-5 w-5 text-indigo-400" />
              By Asset Type
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {Object.entries(exposure?.exposure_by_asset_type || {}).length === 0 ? (
              <p className="text-gray-500 text-sm">No exposure data</p>
            ) : (
              Object.entries(exposure.exposure_by_asset_type).map(([type, value]) => (
                <div key={type} className="flex justify-between items-center">
                  <span className="text-gray-300">{type}</span>
                  <span className="text-white font-medium">{formatCurrency(value)}</span>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        {/* By Sector */}
        <Card className="bg-gray-900/50 border-gray-800">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <BarChart2 className="h-5 w-5 text-indigo-400" />
              By Sector
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {Object.entries(exposure?.exposure_by_sector || {}).length === 0 ? (
              <p className="text-gray-500 text-sm">No sector data</p>
            ) : (
              Object.entries(exposure.exposure_by_sector).map(([sector, value]) => (
                <div key={sector} className="flex justify-between items-center">
                  <span className="text-gray-300">{sector}</span>
                  <span className="text-white font-medium">{formatCurrency(value)}</span>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        {/* By Strategy */}
        <Card className="bg-gray-900/50 border-gray-800">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Activity className="h-5 w-5 text-indigo-400" />
              By Strategy
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {Object.entries(exposure?.exposure_by_strategy || {}).length === 0 ? (
              <p className="text-gray-500 text-sm">No strategy data</p>
            ) : (
              Object.entries(exposure.exposure_by_strategy).map(([strategy, value]) => (
                <div key={strategy} className="flex justify-between items-center">
                  <span className="text-gray-300">{strategy}</span>
                  <span className="text-white font-medium">{formatCurrency(value)}</span>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>

      {/* Last Updated */}
      <div className="flex items-center justify-center gap-2 text-sm text-gray-500">
        <Clock className="h-4 w-4" />
        Last updated: {formatTime(exposure?.snapshot_time)}
      </div>
    </div>
  );
}
