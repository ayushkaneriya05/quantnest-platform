import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../../ui/dialog';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { Label } from '../../ui/label';
import { Badge } from '../../ui/badge';
import { Card, CardContent } from '../../ui/card';
import { Separator } from '../../ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../ui/tabs';
import { Alert, AlertDescription } from '../../ui/alert';
import { 
  TrendingUp, 
  TrendingDown, 
  X, 
  DollarSign, 
  BarChart3,
  AlertTriangle,
  Target
} from 'lucide-react';
import { useApi } from '../../../hooks/use-api';
import { useWebSocket } from '../../../contexts/websocket-context';
import { toast } from 'react-hot-toast';
import { cn } from '../../../lib/utils';

const ModifyPositionModal = ({ position, isOpen, onClose, onPositionUpdated }) => {
  const [activeTab, setActiveTab] = useState('close');
  const [closeQuantity, setCloseQuantity] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [currentPrice, setCurrentPrice] = useState(null);
  const [errors, setErrors] = useState({});

  const { callApi } = useApi();
  const { marketData, subscribeToInstrument, addMarketDataListener } = useWebSocket();

  // Initialize form data when position changes
  useEffect(() => {
    if (position) {
      setCloseQuantity(position.abs_quantity?.toString() || '');
      setErrors({});

      // Subscribe to instrument for live price
      if (position.instrument?.symbol) {
        subscribeToInstrument(position.instrument.symbol);
      }
    }
  }, [position, subscribeToInstrument]);

  // Listen for live price updates
  useEffect(() => {
    if (!position?.instrument?.symbol) return;

    const unsubscribe = addMarketDataListener(position.instrument.symbol, (data) => {
      if (data?.close) {
        setCurrentPrice(parseFloat(data.close));
      }
    });

    // Set initial price from market data
    const marketPrice = marketData.get(position.instrument.symbol);
    if (marketPrice?.close) {
      setCurrentPrice(parseFloat(marketPrice.close));
    }

    return unsubscribe;
  }, [position?.instrument?.symbol, addMarketDataListener, marketData]);

  const validateCloseForm = () => {
    const newErrors = {};
    const quantity = parseInt(closeQuantity);
    
    if (!quantity || quantity <= 0) {
      newErrors.closeQuantity = 'Quantity must be greater than 0';
    } else if (quantity > position.abs_quantity) {
      newErrors.closeQuantity = `Quantity cannot exceed ${position.abs_quantity}`;
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleClosePosition = async (isPartial = false) => {
    if (isPartial && !validateCloseForm()) {
      return;
    }

    setIsSubmitting(true);

    try {
      const payload = {};
      
      if (isPartial) {
        payload.quantity = parseInt(closeQuantity);
      }
      // For full close, no quantity needed (backend will close entire position)

      const response = await callApi(
        `/api/v1/trading/positions/${position.id}/close/`,
        'POST',
        payload
      );

      if (response.success) {
        const action = isPartial ? 'partially closed' : 'closed';
        toast.success(`Position ${action} successfully`);
        onPositionUpdated?.(response.data, action);
        onClose();
      } else {
        throw new Error(response.error || 'Failed to close position');
      }
    } catch (error) {
      console.error('Error closing position:', error);
      toast.error(error.message || 'Failed to close position');
    } finally {
      setIsSubmitting(false);
    }
  };

  const calculatePnL = () => {
    if (!currentPrice || !position) return null;

    const { quantity, average_price, is_long } = position;
    const absQuantity = Math.abs(quantity);
    
    let unrealizedPnL;
    if (is_long) {
      unrealizedPnL = (currentPrice - average_price) * absQuantity;
    } else {
      unrealizedPnL = (average_price - currentPrice) * absQuantity;
    }

    const totalPnL = unrealizedPnL + (position.realized_pnl || 0);
    const pnlPercentage = ((unrealizedPnL / (average_price * absQuantity)) * 100);

    return {
      unrealized: unrealizedPnL,
      total: totalPnL,
      percentage: pnlPercentage,
      isProfit: unrealizedPnL >= 0
    };
  };

  const calculateCloseValue = () => {
    if (!currentPrice || !closeQuantity) return null;

    const quantity = parseInt(closeQuantity);
    if (isNaN(quantity) || quantity <= 0) return null;

    const closeValue = currentPrice * quantity;
    const costBasis = position.average_price * quantity;
    
    let pnl;
    if (position.is_long) {
      pnl = closeValue - costBasis;
    } else {
      pnl = costBasis - closeValue;
    }

    return {
      value: closeValue,
      pnl: pnl,
      isProfit: pnl >= 0
    };
  };

  const formatPrice = (price) => {
    return price ? `₹${parseFloat(price).toFixed(2)}` : '--';
  };

  const formatPnL = (pnl, showSign = true) => {
    if (typeof pnl !== 'number') return '--';
    const sign = showSign ? (pnl >= 0 ? '+' : '') : '';
    return `${sign}₹${Math.abs(pnl).toFixed(2)}`;
  };

  if (!position) return null;

  const pnlData = calculatePnL();
  const closeData = calculateCloseValue();

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            Manage Position
          </DialogTitle>
          <DialogDescription>
            Manage your {position.instrument?.symbol} position
          </DialogDescription>
        </DialogHeader>

        {/* Position Summary */}
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h4 className="font-medium text-lg">{position.instrument?.symbol}</h4>
                <p className="text-sm text-muted-foreground">
                  {position.instrument?.company_name}
                </p>
              </div>
              <div className="text-right">
                <Badge variant={position.is_long ? "default" : "secondary"}>
                  {position.is_long ? 'Long' : 'Short'} Position
                </Badge>
                <p className="text-xs text-muted-foreground mt-1">
                  {formatPrice(currentPrice)} Current
                </p>
              </div>
            </div>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">Quantity:</span>
                <p className="font-medium">{position.abs_quantity}</p>
              </div>
              <div>
                <span className="text-muted-foreground">Avg Price:</span>
                <p className="font-medium">{formatPrice(position.average_price)}</p>
              </div>
              <div>
                <span className="text-muted-foreground">Investment:</span>
                <p className="font-medium">
                  {formatPrice(position.average_price * position.abs_quantity)}
                </p>
              </div>
              <div>
                <span className="text-muted-foreground">Current Value:</span>
                <p className="font-medium">
                  {formatPrice(currentPrice * position.abs_quantity)}
                </p>
              </div>
            </div>

            {/* P&L Display */}
            {pnlData && (
              <div className="mt-4 p-3 bg-accent/50 rounded-lg">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <DollarSign className="h-4 w-4" />
                    <span className="text-sm font-medium">Unrealized P&L</span>
                  </div>
                  <div className={cn(
                    "flex items-center gap-1 font-medium",
                    pnlData.isProfit ? "text-green-600" : "text-red-600"
                  )}>
                    {pnlData.isProfit ? (
                      <TrendingUp className="h-4 w-4" />
                    ) : (
                      <TrendingDown className="h-4 w-4" />
                    )}
                    <span>{formatPnL(pnlData.unrealized)}</span>
                    <span className="text-xs">
                      ({pnlData.percentage > 0 ? '+' : ''}{pnlData.percentage.toFixed(2)}%)
                    </span>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Separator />

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="close">Close Position</TabsTrigger>
            <TabsTrigger value="info">Position Details</TabsTrigger>
          </TabsList>

          <TabsContent value="close" className="space-y-4">
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="closeQuantity">Quantity to Close</Label>
                <Input
                  id="closeQuantity"
                  type="number"
                  min="1"
                  max={position.abs_quantity}
                  value={closeQuantity}
                  onChange={(e) => {
                    setCloseQuantity(e.target.value);
                    if (errors.closeQuantity) {
                      setErrors(prev => ({ ...prev, closeQuantity: undefined }));
                    }
                  }}
                  className={errors.closeQuantity ? 'border-red-500' : ''}
                  placeholder={`Max: ${position.abs_quantity}`}
                />
                {errors.closeQuantity && (
                  <p className="text-sm text-red-500">{errors.closeQuantity}</p>
                )}
                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setCloseQuantity(Math.floor(position.abs_quantity / 2).toString())}
                  >
                    50%
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setCloseQuantity(position.abs_quantity.toString())}
                  >
                    100%
                  </Button>
                </div>
              </div>

              {/* Close Preview */}
              {closeData && parseInt(closeQuantity) > 0 && (
                <Card>
                  <CardContent className="p-4">
                    <h4 className="font-medium mb-3 flex items-center gap-2">
                      <Target className="h-4 w-4" />
                      Close Preview
                    </h4>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-muted-foreground">Close Value:</span>
                        <p className="font-medium">{formatPrice(closeData.value)}</p>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Estimated P&L:</span>
                        <p className={cn(
                          "font-medium",
                          closeData.isProfit ? "text-green-600" : "text-red-600"
                        )}>
                          {formatPnL(closeData.pnl)}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Warning for full close */}
              {parseInt(closeQuantity) === position.abs_quantity && (
                <Alert>
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription>
                    This will completely close your position in {position.instrument?.symbol}.
                  </AlertDescription>
                </Alert>
              )}
            </div>
          </TabsContent>

          <TabsContent value="info" className="space-y-4">
            <div className="grid gap-4">
              <Card>
                <CardContent className="p-4">
                  <h4 className="font-medium mb-3">Position Details</h4>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-muted-foreground">Position Type:</span>
                      <p className="font-medium">
                        {position.is_long ? 'Long' : 'Short'} ({position.quantity} shares)
                      </p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Entry Date:</span>
                      <p className="font-medium">
                        {position.created_at ? new Date(position.created_at).toLocaleDateString() : '--'}
                      </p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Last Updated:</span>
                      <p className="font-medium">
                        {position.updated_at ? new Date(position.updated_at).toLocaleDateString() : '--'}
                      </p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Realized P&L:</span>
                      <p className={cn(
                        "font-medium",
                        (position.realized_pnl || 0) >= 0 ? "text-green-600" : "text-red-600"
                      )}>
                        {formatPnL(position.realized_pnl || 0)}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Risk Metrics */}
              {pnlData && (
                <Card>
                  <CardContent className="p-4">
                    <h4 className="font-medium mb-3">Risk Metrics</h4>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-muted-foreground">Unrealized P&L:</span>
                        <p className={cn(
                          "font-medium",
                          pnlData.isProfit ? "text-green-600" : "text-red-600"
                        )}>
                          {formatPnL(pnlData.unrealized)}
                        </p>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Total P&L:</span>
                        <p className={cn(
                          "font-medium",
                          pnlData.total >= 0 ? "text-green-600" : "text-red-600"
                        )}>
                          {formatPnL(pnlData.total)}
                        </p>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Return %:</span>
                        <p className={cn(
                          "font-medium",
                          pnlData.percentage >= 0 ? "text-green-600" : "text-red-600"
                        )}>
                          {pnlData.percentage > 0 ? '+' : ''}{pnlData.percentage.toFixed(2)}%
                        </p>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Price Change:</span>
                        <p className={cn(
                          "font-medium",
                          currentPrice >= position.average_price ? "text-green-600" : "text-red-600"
                        )}>
                          {formatPrice(currentPrice - position.average_price)}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          </TabsContent>
        </Tabs>

        <DialogFooter className="flex-col sm:flex-row gap-2">
          {activeTab === 'close' && (
            <>
              <Button
                type="button"
                variant="destructive"
                onClick={() => handleClosePosition(false)}
                disabled={isSubmitting}
                className="flex items-center gap-2"
              >
                <X className="h-4 w-4" />
                {isSubmitting ? 'Closing...' : 'Close Full Position'}
              </Button>
              
              <div className="flex gap-2">
                <Button type="button" variant="outline" onClick={onClose}>
                  Cancel
                </Button>
                <Button
                  type="button"
                  onClick={() => handleClosePosition(true)}
                  disabled={isSubmitting || !closeQuantity || parseInt(closeQuantity) <= 0}
                >
                  {isSubmitting ? 'Closing...' : 'Close Partial'}
                </Button>
              </div>
            </>
          )}
          
          {activeTab === 'info' && (
            <Button type="button" variant="outline" onClick={onClose}>
              Close
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default ModifyPositionModal;
