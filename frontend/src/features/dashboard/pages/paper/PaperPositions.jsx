/**
 * Paper Positions - view and manage open positions
 */
import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import { Badge } from "@/shared/components/ui/badge";
import { 
  ChevronLeft, X, RefreshCw, TrendingUp, TrendingDown, Layers
} from 'lucide-react';
import { paperApi } from '@/shared/services/paperApi';
import { useNotifications } from '@/shared/hooks/useNotifications';
import { useSetPageActions } from '@/shared/hooks/useSetPageActions';

export default function PaperPositions() {
  const navigate = useNavigate();
  const { notify } = useNotifications();
  const [positions, setPositions] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchPositions = async () => {
    try {
      const response = await paperApi.getPositions();
      setPositions(response.data);
    } catch (error) {
      notify.error('Failed to load positions');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPositions();
    const interval = setInterval(fetchPositions, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleClose = async (positionId) => {
    if (!confirm('Close this position at market price?')) return;
    try {
      const response = await paperApi.closePosition(positionId);
      notify.success(`Position closed. P&L: ₹${response.data.pnl.toFixed(2)}`);
      fetchPositions();
    } catch (error) {
      notify.error('Failed to close position');
    }
  };

  // Set page actions in header
  const pageActions = useMemo(() => (
    <Button variant="outline" size="sm" onClick={fetchPositions} className="border-gray-700">
      <RefreshCw className="h-4 w-4" />
    </Button>
  ), []);

  useSetPageActions(pageActions);

  const formatCurrency = (val) => {
    return new Intl.NumberFormat('en-IN', { 
      style: 'currency', currency: 'INR', maximumFractionDigits: 0 
    }).format(val || 0);
  };

  // Calculate totals
  const totalValue = positions.reduce((sum, p) => sum + parseFloat(p.current_value || 0), 0);
  const totalUnrealizedPnl = positions.reduce((sum, p) => sum + parseFloat(p.unrealized_pnl || 0), 0);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-96">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500" />
      </div>
    );
  }

  return (
    <div className="container-padding py-6 lg:py-8 space-y-6">
      {/* Summary */}
      <div className="grid grid-cols-3 gap-4">
        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-4 text-center">
            <p className="text-2xl font-bold text-white">{positions.length}</p>
            <p className="text-xs text-gray-400">Open Positions</p>
          </CardContent>
        </Card>
        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-4 text-center">
            <p className="text-2xl font-bold text-white">{formatCurrency(totalValue)}</p>
            <p className="text-xs text-gray-400">Total Value</p>
          </CardContent>
        </Card>
        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-4 text-center">
            <p className={`text-2xl font-bold ${totalUnrealizedPnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {totalUnrealizedPnl >= 0 ? '+' : ''}{formatCurrency(totalUnrealizedPnl)}
            </p>
            <p className="text-xs text-gray-400">Unrealized P&L</p>
          </CardContent>
        </Card>
      </div>

      {/* Positions List */}
      {positions.length === 0 ? (
        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-12 text-center">
            <Layers className="h-10 w-10 text-gray-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-300">No open positions</h3>
            <p className="text-gray-500">Place orders to open new positions</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {positions.map((pos) => (
            <Card key={pos.id} className="bg-gray-900/50 border-gray-800">
              <CardContent className="py-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className={`p-3 rounded-lg ${pos.side === 'BUY' ? 'bg-green-900/30' : 'bg-red-900/30'}`}>
                      {pos.side === 'BUY' ? 
                        <TrendingUp className="h-6 w-6 text-green-400" /> :
                        <TrendingDown className="h-6 w-6 text-red-400" />
                      }
                    </div>
                    <div>
                      <h3 className="text-lg font-bold text-white">{pos.instrument_symbol}</h3>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge className={pos.side === 'BUY' ? 'bg-green-600' : 'bg-red-600'}>
                          {pos.side}
                        </Badge>
                        {pos.strategy_name && (
                          <Badge variant="outline" className="border-gray-600">{pos.strategy_name}</Badge>
                        )}
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-8">
                    <div className="text-right">
                      <p className="text-sm text-gray-400">Quantity</p>
                      <p className="text-white font-medium">{pos.quantity}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm text-gray-400">Avg Price</p>
                      <p className="text-white font-medium">₹{parseFloat(pos.avg_price).toFixed(2)}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm text-gray-400">Current</p>
                      <p className="text-white font-medium">₹{parseFloat(pos.current_price).toFixed(2)}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm text-gray-400">P&L</p>
                      <p className={`font-bold ${parseFloat(pos.unrealized_pnl) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {formatCurrency(pos.unrealized_pnl)}
                      </p>
                      <p className="text-xs text-gray-500">
                        ({parseFloat(pos.unrealized_pnl_pct).toFixed(2)}%)
                      </p>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleClose(pos.id)}
                      className="border-red-800 text-red-400 hover:bg-red-900/30"
                    >
                      <X className="h-4 w-4 mr-1" />
                      Close
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
