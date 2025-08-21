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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../ui/select';
import { Badge } from '../../ui/badge';
import { Card, CardContent } from '../../ui/card';
import { Separator } from '../../ui/separator';
import { AlertTriangle, Edit3, X, TrendingUp, TrendingDown } from 'lucide-react';
import { useApi } from '../../../hooks/use-api';
import { useWebSocket } from '../../../contexts/websocket-context';
import { toast } from 'react-hot-toast';
import { cn } from '../../../lib/utils';

const ORDER_TYPES = [
  { value: 'MARKET', label: 'Market', requiresPrice: false },
  { value: 'LIMIT', label: 'Limit', requiresPrice: true },
  { value: 'STOP', label: 'Stop-Loss', requiresPrice: false, requiresTrigger: true },
  { value: 'STOP_LIMIT', label: 'Stop-Limit', requiresPrice: true, requiresTrigger: true }
];

const TRANSACTION_TYPES = [
  { value: 'BUY', label: 'Buy', className: 'text-green-600' },
  { value: 'SELL', label: 'Sell', className: 'text-red-600' },
  { value: 'SHORT', label: 'Short Sell', className: 'text-orange-600' },
  { value: 'COVER', label: 'Cover Short', className: 'text-blue-600' }
];

const ModifyOrderModal = ({ order, isOpen, onClose, onOrderUpdated }) => {
  const [formData, setFormData] = useState({
    order_type: '',
    quantity: '',
    price: '',
    trigger_price: ''
  });
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [currentPrice, setCurrentPrice] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const { callApi } = useApi();
  const { marketData, subscribeToInstrument, addMarketDataListener } = useWebSocket();

  // Initialize form data when order changes
  useEffect(() => {
    if (order) {
      setFormData({
        order_type: order.order_type || 'MARKET',
        quantity: order.quantity?.toString() || '',
        price: order.price?.toString() || '',
        trigger_price: order.trigger_price?.toString() || ''
      });
      setErrors({});

      // Subscribe to instrument for live price
      if (order.instrument?.symbol) {
        subscribeToInstrument(order.instrument.symbol);
      }
    }
  }, [order, subscribeToInstrument]);

  // Listen for live price updates
  useEffect(() => {
    if (!order?.instrument?.symbol) return;

    const unsubscribe = addMarketDataListener(order.instrument.symbol, (data) => {
      if (data?.close) {
        setCurrentPrice(parseFloat(data.close));
      }
    });

    // Set initial price from market data
    const marketPrice = marketData.get(order.instrument.symbol);
    if (marketPrice?.close) {
      setCurrentPrice(parseFloat(marketPrice.close));
    }

    return unsubscribe;
  }, [order?.instrument?.symbol, addMarketDataListener, marketData]);

  const validateForm = () => {
    const newErrors = {};
    const selectedOrderType = ORDER_TYPES.find(type => type.value === formData.order_type);

    // Quantity validation
    const quantity = parseInt(formData.quantity);
    if (!quantity || quantity <= 0) {
      newErrors.quantity = 'Quantity must be greater than 0';
    }

    // Price validation for limit orders
    if (selectedOrderType?.requiresPrice) {
      const price = parseFloat(formData.price);
      if (!price || price <= 0) {
        newErrors.price = 'Price must be greater than 0';
      }
    }

    // Trigger price validation for stop orders
    if (selectedOrderType?.requiresTrigger) {
      const triggerPrice = parseFloat(formData.trigger_price);
      if (!triggerPrice || triggerPrice <= 0) {
        newErrors.trigger_price = 'Trigger price must be greater than 0';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleInputChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));

    // Clear specific error when user starts typing
    if (errors[field]) {
      setErrors(prev => ({
        ...prev,
        [field]: undefined
      }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);

    try {
      const payload = {
        order_type: formData.order_type,
        quantity: parseInt(formData.quantity)
      };

      // Add price fields based on order type
      const selectedOrderType = ORDER_TYPES.find(type => type.value === formData.order_type);
      
      if (selectedOrderType?.requiresPrice && formData.price) {
        payload.price = parseFloat(formData.price);
      }
      
      if (selectedOrderType?.requiresTrigger && formData.trigger_price) {
        payload.trigger_price = parseFloat(formData.trigger_price);
      }

      const response = await callApi(
        `/api/v1/trading/orders/${order.id}/`,
        'PATCH',
        payload
      );

      if (response.success) {
        toast.success('Order modified successfully');
        onOrderUpdated?.(response.data);
        onClose();
      } else {
        throw new Error(response.error || 'Failed to modify order');
      }
    } catch (error) {
      console.error('Error modifying order:', error);
      toast.error(error.message || 'Failed to modify order');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancelOrder = async () => {
    if (!order?.id) return;

    setIsDeleting(true);

    try {
      const response = await callApi(
        `/api/v1/trading/orders/${order.id}/cancel/`,
        'POST'
      );

      if (response.success) {
        toast.success('Order cancelled successfully');
        onOrderUpdated?.(null, true); // null data, cancelled = true
        onClose();
      } else {
        throw new Error(response.error || 'Failed to cancel order');
      }
    } catch (error) {
      console.error('Error cancelling order:', error);
      toast.error(error.message || 'Failed to cancel order');
    } finally {
      setIsDeleting(false);
    }
  };

  const getTransactionTypeInfo = (type) => {
    return TRANSACTION_TYPES.find(t => t.value === type) || TRANSACTION_TYPES[0];
  };

  const formatPrice = (price) => {
    return price ? `₹${parseFloat(price).toFixed(2)}` : '--';
  };

  const calculatePriceDeviation = (price) => {
    if (!currentPrice || !price) return null;
    
    const deviation = ((price - currentPrice) / currentPrice) * 100;
    return {
      percentage: Math.abs(deviation).toFixed(2),
      isAbove: deviation > 0,
      isSignificant: Math.abs(deviation) > 5
    };
  };

  if (!order) return null;

  const selectedOrderType = ORDER_TYPES.find(type => type.value === formData.order_type);
  const transactionType = getTransactionTypeInfo(order.transaction_type);
  const priceDeviation = formData.price ? calculatePriceDeviation(parseFloat(formData.price)) : null;
  const triggerDeviation = formData.trigger_price ? calculatePriceDeviation(parseFloat(formData.trigger_price)) : null;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Edit3 className="h-5 w-5" />
            Modify Order
          </DialogTitle>
          <DialogDescription>
            Modify the details of your {order.instrument?.symbol} order
          </DialogDescription>
        </DialogHeader>

        {/* Order Summary */}
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h4 className="font-medium">{order.instrument?.symbol}</h4>
                <p className="text-sm text-muted-foreground">
                  {order.instrument?.company_name}
                </p>
              </div>
              <div className="text-right">
                <Badge className={transactionType.className}>
                  {transactionType.label}
                </Badge>
                <p className="text-xs text-muted-foreground mt-1">
                  {formatPrice(currentPrice)} Current
                </p>
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">Original Quantity:</span>
                <p className="font-medium">{order.quantity}</p>
              </div>
              <div>
                <span className="text-muted-foreground">Order Type:</span>
                <p className="font-medium">{order.order_type}</p>
              </div>
              {order.price && (
                <div>
                  <span className="text-muted-foreground">Original Price:</span>
                  <p className="font-medium">{formatPrice(order.price)}</p>
                </div>
              )}
              {order.trigger_price && (
                <div>
                  <span className="text-muted-foreground">Original Trigger:</span>
                  <p className="font-medium">{formatPrice(order.trigger_price)}</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        <Separator />

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Order Type */}
          <div className="space-y-2">
            <Label htmlFor="order_type">Order Type</Label>
            <Select value={formData.order_type} onValueChange={(value) => handleInputChange('order_type', value)}>
              <SelectTrigger>
                <SelectValue placeholder="Select order type" />
              </SelectTrigger>
              <SelectContent>
                {ORDER_TYPES.map(type => (
                  <SelectItem key={type.value} value={type.value}>
                    {type.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Quantity */}
          <div className="space-y-2">
            <Label htmlFor="quantity">Quantity</Label>
            <Input
              id="quantity"
              type="number"
              min="1"
              value={formData.quantity}
              onChange={(e) => handleInputChange('quantity', e.target.value)}
              className={errors.quantity ? 'border-red-500' : ''}
              placeholder="Enter quantity"
            />
            {errors.quantity && (
              <p className="text-sm text-red-500">{errors.quantity}</p>
            )}
          </div>

          {/* Price (for limit orders) */}
          {selectedOrderType?.requiresPrice && (
            <div className="space-y-2">
              <Label htmlFor="price">Limit Price</Label>
              <Input
                id="price"
                type="number"
                step="0.01"
                min="0.01"
                value={formData.price}
                onChange={(e) => handleInputChange('price', e.target.value)}
                className={errors.price ? 'border-red-500' : ''}
                placeholder="Enter limit price"
              />
              {errors.price && (
                <p className="text-sm text-red-500">{errors.price}</p>
              )}
              {priceDeviation && (
                <div className={cn(
                  "flex items-center gap-1 text-xs",
                  priceDeviation.isSignificant ? "text-orange-600" : "text-muted-foreground"
                )}>
                  {priceDeviation.isAbove ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                  {priceDeviation.percentage}% {priceDeviation.isAbove ? 'above' : 'below'} current price
                  {priceDeviation.isSignificant && <AlertTriangle className="h-3 w-3 text-orange-600" />}
                </div>
              )}
            </div>
          )}

          {/* Trigger Price (for stop orders) */}
          {selectedOrderType?.requiresTrigger && (
            <div className="space-y-2">
              <Label htmlFor="trigger_price">Trigger Price</Label>
              <Input
                id="trigger_price"
                type="number"
                step="0.01"
                min="0.01"
                value={formData.trigger_price}
                onChange={(e) => handleInputChange('trigger_price', e.target.value)}
                className={errors.trigger_price ? 'border-red-500' : ''}
                placeholder="Enter trigger price"
              />
              {errors.trigger_price && (
                <p className="text-sm text-red-500">{errors.trigger_price}</p>
              )}
              {triggerDeviation && (
                <div className={cn(
                  "flex items-center gap-1 text-xs",
                  triggerDeviation.isSignificant ? "text-orange-600" : "text-muted-foreground"
                )}>
                  {triggerDeviation.isAbove ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                  {triggerDeviation.percentage}% {triggerDeviation.isAbove ? 'above' : 'below'} current price
                </div>
              )}
            </div>
          )}
        </form>

        <DialogFooter className="flex-col sm:flex-row gap-2">
          {/* Cancel Order Button */}
          <Button
            type="button"
            variant="destructive"
            size="sm"
            onClick={handleCancelOrder}
            disabled={isDeleting || isSubmitting}
            className="flex items-center gap-2"
          >
            <X className="h-4 w-4" />
            {isDeleting ? 'Cancelling...' : 'Cancel Order'}
          </Button>

          <div className="flex gap-2">
            <Button type="button" variant="outline" onClick={onClose}>
              Close
            </Button>
            <Button
              type="submit"
              onClick={handleSubmit}
              disabled={isSubmitting || isDeleting}
            >
              {isSubmitting ? 'Updating...' : 'Update Order'}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default ModifyOrderModal;
