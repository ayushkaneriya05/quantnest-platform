import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { AlertCircle, TrendingUp, TrendingDown, Edit3, X, DollarSign, Clock, Info } from "lucide-react";
import { useWebSocketContext } from "@/contexts/websocket-context";
import api from "@/services/api";
import toast from "react-hot-toast";

const ORDER_TYPES = [
  { value: 'MARKET', label: 'Market', description: 'Execute immediately at current market price' },
  { value: 'LIMIT', label: 'Limit', description: 'Execute only at specified price or better' },
  { value: 'STOP', label: 'Stop Loss', description: 'Market order triggered at stop price' },
  { value: 'STOP_LIMIT', label: 'Stop Limit', description: 'Limit order triggered at stop price' },
];

export default function ModifyOrderModal({ 
  isOpen, 
  onClose, 
  order, 
  onOrderModified 
}) {
  const [formData, setFormData] = useState({
    order_type: '',
    quantity: '',
    price: '',
    trigger_price: '',
  });
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [currentMarketPrice, setCurrentMarketPrice] = useState(null);
  const [estimatedValue, setEstimatedValue] = useState(0);

  const { getLatestPrice } = useWebSocketContext();

  // Initialize form data when order changes
  useEffect(() => {
    if (order) {
      setFormData({
        order_type: order.order_type || 'MARKET',
        quantity: order.quantity?.toString() || '',
        price: order.price?.toString() || '',
        trigger_price: order.trigger_price?.toString() || '',
      });
      
      // Get current market price
      const marketPrice = getLatestPrice(order.instrument?.symbol);
      setCurrentMarketPrice(marketPrice);
    }
  }, [order, getLatestPrice]);

  // Calculate estimated value when form data changes
  useEffect(() => {
    if (!formData.quantity) {
      setEstimatedValue(0);
      return;
    }

    const quantity = parseInt(formData.quantity);
    let price = 0;

    if (formData.order_type === 'MARKET') {
      price = currentMarketPrice || 2500; // Mock current price
    } else if (formData.price) {
      price = parseFloat(formData.price);
    }

    setEstimatedValue(quantity * price);
  }, [formData, currentMarketPrice]);

  const validateForm = () => {
    const newErrors = {};

    if (!formData.quantity || formData.quantity <= 0) {
      newErrors.quantity = 'Quantity must be greater than 0';
    }

    if (formData.order_type === 'LIMIT' || formData.order_type === 'STOP_LIMIT') {
      if (!formData.price || formData.price <= 0) {
        newErrors.price = 'Price must be greater than 0';
      }
    }

    if (formData.order_type === 'STOP' || formData.order_type === 'STOP_LIMIT') {
      if (!formData.trigger_price || formData.trigger_price <= 0) {
        newErrors.trigger_price = 'Trigger price must be greater than 0';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) return;

    setIsSubmitting(true);

    try {
      const updateData = {
        order_type: formData.order_type,
        quantity: parseInt(formData.quantity),
      };

      // Add price fields based on order type
      if (formData.order_type === 'LIMIT' || formData.order_type === 'STOP_LIMIT') {
        updateData.price = parseFloat(formData.price);
      }

      if (formData.order_type === 'STOP' || formData.order_type === 'STOP_LIMIT') {
        updateData.trigger_price = parseFloat(formData.trigger_price);
      }

      const response = await api.put(`/api/v1/trading/orders/${order.id}/`, updateData);
      
      toast.success('Order modified successfully');
      
      if (onOrderModified) {
        onOrderModified(response.data);
      }
      
      onClose();
    } catch (err) {
      console.error('Failed to modify order:', err);
      
      if (err.response?.data?.error) {
        toast.error(err.response.data.error);
      } else if (err.response?.data) {
        // Handle field-specific errors
        const fieldErrors = {};
        Object.keys(err.response.data).forEach(field => {
          if (Array.isArray(err.response.data[field])) {
            fieldErrors[field] = err.response.data[field][0];
          }
        });
        setErrors(fieldErrors);
      } else {
        toast.error('Failed to modify order. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleInputChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    
    // Clear error when user starts typing
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }));
    }
  };

  const handleCancel = () => {
    setFormData({
      order_type: '',
      quantity: '',
      price: '',
      trigger_price: '',
    });
    setErrors({});
    onClose();
  };

  const requiresPrice = formData.order_type === 'LIMIT' || formData.order_type === 'STOP_LIMIT';
  const requiresTriggerPrice = formData.order_type === 'STOP' || formData.order_type === 'STOP_LIMIT';

  if (!order) return null;

  const timeSinceCreated = new Date() - new Date(order.created_at);
  const hoursAgo = Math.floor(timeSinceCreated / (1000 * 60 * 60));
  const minutesAgo = Math.floor((timeSinceCreated % (1000 * 60 * 60)) / (1000 * 60));

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[550px] bg-slate-900 border-slate-700 text-white max-h-[90vh] overflow-y-auto [&::-webkit-scrollbar]:w-2 [&::-webkit-scrollbar-track]:bg-slate-800 [&::-webkit-scrollbar-thumb]:bg-slate-600 [&::-webkit-scrollbar-thumb]:rounded-full hover:[&::-webkit-scrollbar-thumb]:bg-slate-500">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl">
            <Edit3 className="h-5 w-5 text-blue-400" />
            Modify Order
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Order Info */}
          <div className="bg-slate-800/50 p-4 rounded-lg border border-slate-700/50">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h3 className="font-semibold text-lg">{order.instrument?.symbol}</h3>
                <p className="text-sm text-gray-400">{order.instrument?.company_name}</p>
              </div>
              <div className="text-right space-y-1">
                <div className="flex items-center gap-2">
                  <Badge variant={order.transaction_type === 'BUY' ? 'default' : 'secondary'} className="text-xs">
                    {order.transaction_type}
                  </Badge>
                  <Badge variant="outline" className="text-xs border-gray-600 text-gray-400">
                    {order.status}
                  </Badge>
                </div>
                <div className="flex items-center gap-1 text-xs text-gray-500">
                  <Clock className="h-3 w-3" />
                  {hoursAgo > 0 ? `${hoursAgo}h ` : ''}{minutesAgo}m ago
                </div>
              </div>
            </div>
            
            {currentMarketPrice && (
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                <div>
                  <span className="text-gray-400">Current Price:</span>
                  <div className="font-mono text-white">₹{currentMarketPrice.toFixed(2)}</div>
                </div>
                <div>
                  <span className="text-gray-400">Order Price:</span>
                  <div className="font-mono text-white">
                    {order.order_type === 'MARKET' ? 'Market' : `₹${order.price}`}
                  </div>
                </div>
                {order.price && order.order_type !== 'MARKET' && (
                  <div>
                    <span className="text-gray-400">Price Diff:</span>
                    <div className={`font-mono flex items-center gap-1 ${
                      currentMarketPrice > order.price ? 'text-emerald-400' : 'text-red-400'
                    }`}>
                      {currentMarketPrice > order.price ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                      {((currentMarketPrice - order.price) / order.price * 100).toFixed(2)}%
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Order Type */}
          <div className="space-y-2">
            <Label htmlFor="order_type">Order Type</Label>
            <Select 
              value={formData.order_type} 
              onValueChange={(value) => handleInputChange('order_type', value)}
            >
              <SelectTrigger className="bg-slate-800 border-slate-700">
                <SelectValue placeholder="Select order type" />
              </SelectTrigger>
              <SelectContent className="bg-slate-800 border-slate-700">
                {ORDER_TYPES.map((type) => (
                  <SelectItem key={type.value} value={type.value} className="text-white hover:bg-slate-700">
                    <div>
                      <div className="font-medium">{type.label}</div>
                      <div className="text-xs text-gray-400">{type.description}</div>
                    </div>
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
              value={formData.quantity}
              onChange={(e) => handleInputChange('quantity', e.target.value)}
              placeholder="Enter quantity"
              className="bg-slate-800 border-slate-700"
              min="1"
              step="1"
            />
            {errors.quantity && (
              <p className="text-red-400 text-sm flex items-center gap-1">
                <AlertCircle className="h-4 w-4" />
                {errors.quantity}
              </p>
            )}
          </div>

          {/* Price Fields */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Price (for LIMIT and STOP_LIMIT orders) */}
            {requiresPrice && (
              <div className="space-y-2">
                <Label htmlFor="price">Limit Price</Label>
                <Input
                  id="price"
                  type="number"
                  value={formData.price}
                  onChange={(e) => handleInputChange('price', e.target.value)}
                  placeholder="Enter limit price"
                  className="bg-slate-800 border-slate-700"
                  min="0"
                  step="0.01"
                />
                {errors.price && (
                  <p className="text-red-400 text-sm flex items-center gap-1">
                    <AlertCircle className="h-4 w-4" />
                    {errors.price}
                  </p>
                )}
              </div>
            )}

            {/* Trigger Price (for STOP and STOP_LIMIT orders) */}
            {requiresTriggerPrice && (
              <div className="space-y-2">
                <Label htmlFor="trigger_price">Stop/Trigger Price</Label>
                <Input
                  id="trigger_price"
                  type="number"
                  value={formData.trigger_price}
                  onChange={(e) => handleInputChange('trigger_price', e.target.value)}
                  placeholder="Enter trigger price"
                  className="bg-slate-800 border-slate-700"
                  min="0"
                  step="0.01"
                />
                {errors.trigger_price && (
                  <p className="text-red-400 text-sm flex items-center gap-1">
                    <AlertCircle className="h-4 w-4" />
                    {errors.trigger_price}
                  </p>
                )}
              </div>
            )}
          </div>

          <Separator className="bg-slate-700" />

          {/* Order Summary */}
          <div className="bg-blue-900/20 p-4 rounded-lg border border-blue-700/30">
            <div className="flex items-center gap-2 mb-3">
              <Info className="h-4 w-4 text-blue-400" />
              <span className="text-sm font-medium text-blue-300">Order Summary</span>
            </div>
            
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
              <div>
                <div className="text-gray-400">Side</div>
                <div className={`font-medium ${order.transaction_type === 'BUY' ? 'text-emerald-400' : 'text-red-400'}`}>
                  {order.transaction_type}
                </div>
              </div>
              <div>
                <div className="text-gray-400">Quantity</div>
                <div className="text-white font-mono">{formData.quantity || order.quantity} shares</div>
              </div>
              <div>
                <div className="text-gray-400">Type</div>
                <div className="text-white">{formData.order_type || order.order_type}</div>
              </div>
            </div>

            {estimatedValue > 0 && (
              <div className="mt-3 pt-3 border-t border-blue-700/30">
                <div className="flex items-center justify-between">
                  <span className="text-gray-400">Estimated Value:</span>
                  <div className="flex items-center gap-1 text-blue-300">
                    <DollarSign className="h-4 w-4" />
                    <span className="font-mono font-bold">₹{estimatedValue.toFixed(2)}</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          <DialogFooter className="gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={handleCancel}
              disabled={isSubmitting}
              className="border-slate-600 text-slate-300 hover:bg-slate-700 hover:text-white hover:border-slate-500"
            >
              <X className="h-4 w-4 mr-2" />
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={isSubmitting}
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              {isSubmitting ? (
                <div className="flex items-center gap-2">
                  <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full" />
                  Modifying...
                </div>
              ) : (
                <>
                  <Edit3 className="h-4 w-4 mr-2" />
                  Modify Order
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
