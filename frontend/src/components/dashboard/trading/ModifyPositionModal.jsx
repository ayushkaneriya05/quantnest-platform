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
import { AlertCircle, TrendingUp, TrendingDown, Settings, X, DollarSign } from "lucide-react";
import { useWebSocketContext } from "@/contexts/websocket-context";
import api from "@/services/api";
import toast from "react-hot-toast";

const TRANSACTION_TYPES = [
  { value: 'BUY', label: 'Buy More', description: 'Add to existing position' },
  { value: 'SELL', label: 'Sell Partial', description: 'Reduce position size' },
  { value: 'CLOSE', label: 'Close Position', description: 'Exit entire position' },
];

const ORDER_TYPES = [
  { value: 'MARKET', label: 'Market', description: 'Execute immediately' },
  { value: 'LIMIT', label: 'Limit', description: 'Execute at specified price' },
];

export default function ModifyPositionModal({ 
  isOpen, 
  onClose, 
  position, 
  onPositionModified 
}) {
  const [formData, setFormData] = useState({
    action: '',
    order_type: 'MARKET',
    quantity: '',
    price: '',
  });
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [currentMarketPrice, setCurrentMarketPrice] = useState(null);
  const [estimatedValue, setEstimatedValue] = useState(0);
  const [profitLoss, setProfitLoss] = useState({ amount: 0, percentage: 0 });

  const { getLatestPrice } = useWebSocketContext();

  // Initialize form data and calculations when position changes
  useEffect(() => {
    if (position) {
      const marketPrice = getLatestPrice(position.instrument?.symbol);
      setCurrentMarketPrice(marketPrice);
      
      if (marketPrice) {
        const currentValue = position.quantity * marketPrice;
        const investedValue = position.quantity * position.average_price;
        const pnl = currentValue - investedValue;
        const pnlPercentage = (pnl / investedValue) * 100;
        
        setProfitLoss({ 
          amount: pnl, 
          percentage: pnlPercentage 
        });
      }
      
      // Reset form
      setFormData({
        action: '',
        order_type: 'MARKET',
        quantity: '',
        price: '',
      });
    }
  }, [position, getLatestPrice]);

  // Calculate estimated value when form data changes
  useEffect(() => {
    if (!formData.quantity || !currentMarketPrice) {
      setEstimatedValue(0);
      return;
    }

    const quantity = parseInt(formData.quantity);
    const price = formData.order_type === 'LIMIT' && formData.price 
      ? parseFloat(formData.price) 
      : currentMarketPrice;
    
    setEstimatedValue(quantity * price);
  }, [formData, currentMarketPrice]);

  const validateForm = () => {
    const newErrors = {};

    if (!formData.action) {
      newErrors.action = 'Please select an action';
    }

    if (!formData.quantity || formData.quantity <= 0) {
      newErrors.quantity = 'Quantity must be greater than 0';
    }

    // Check if trying to sell more than available
    if ((formData.action === 'SELL' || formData.action === 'CLOSE') && position) {
      const quantity = parseInt(formData.quantity);
      if (formData.action === 'CLOSE' && quantity !== Math.abs(position.quantity)) {
        newErrors.quantity = `To close position, quantity must be ${Math.abs(position.quantity)}`;
      } else if (formData.action === 'SELL' && quantity > Math.abs(position.quantity)) {
        newErrors.quantity = `Cannot sell more than available quantity (${Math.abs(position.quantity)})`;
      }
    }

    if (formData.order_type === 'LIMIT') {
      if (!formData.price || formData.price <= 0) {
        newErrors.price = 'Price must be greater than 0';
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
      let transaction_type = formData.action;
      let quantity = parseInt(formData.quantity);

      // For closing position, determine transaction type based on current position
      if (formData.action === 'CLOSE') {
        transaction_type = position.quantity > 0 ? 'SELL' : 'BUY';
        quantity = Math.abs(position.quantity);
      }

      const orderData = {
        instrument_id: position.instrument.id,
        order_type: formData.order_type,
        transaction_type: transaction_type,
        quantity: quantity,
      };

      // Add price for limit orders
      if (formData.order_type === 'LIMIT') {
        orderData.price = parseFloat(formData.price);
      }

      const response = await api.post('/trading/orders/', orderData);
      
      toast.success(
        formData.action === 'CLOSE' 
          ? 'Position close order placed successfully' 
          : 'Position modification order placed successfully'
      );
      
      if (onPositionModified) {
        onPositionModified(response.data);
      }
      
      onClose();
    } catch (err) {
      console.error('Failed to modify position:', err);
      
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
        toast.error('Failed to modify position. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleInputChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    
    // Auto-fill quantity for close position
    if (field === 'action' && value === 'CLOSE' && position) {
      setFormData(prev => ({ ...prev, quantity: Math.abs(position.quantity).toString() }));
    }
    
    // Clear error when user starts typing
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }));
    }
  };

  const handleCancel = () => {
    setFormData({
      action: '',
      order_type: 'MARKET',
      quantity: '',
      price: '',
    });
    setErrors({});
    onClose();
  };

  const requiresPrice = formData.order_type === 'LIMIT';

  if (!position) return null;

  const isLongPosition = position.quantity > 0;
  const positionValue = Math.abs(position.quantity) * (currentMarketPrice || position.average_price);

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[550px] bg-gray-900 border-gray-700 text-white">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl">
            <Settings className="h-5 w-5 text-blue-400" />
            Modify Position
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Position Info */}
          <div className="bg-gray-800/50 p-4 rounded-lg">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h3 className="font-semibold text-lg">{position.instrument?.symbol}</h3>
                <p className="text-sm text-gray-400">{position.instrument?.company_name}</p>
              </div>
              <div className="text-right">
                <Badge variant={isLongPosition ? 'default' : 'secondary'}>
                  {isLongPosition ? 'LONG' : 'SHORT'}
                </Badge>
                <div className="text-sm text-gray-400 mt-1">
                  {Math.abs(position.quantity)} shares
                </div>
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-400">Avg Price:</span>
                <div className="font-mono text-white">₹{position.average_price}</div>
              </div>
              <div>
                <span className="text-gray-400">Current Price:</span>
                <div className="font-mono text-white">
                  ₹{currentMarketPrice?.toFixed(2) || '---'}
                </div>
              </div>
              <div>
                <span className="text-gray-400">Position Value:</span>
                <div className="font-mono text-white">₹{positionValue.toFixed(2)}</div>
              </div>
              <div>
                <span className="text-gray-400">P&L:</span>
                <div className={`font-mono flex items-center gap-1 ${
                  profitLoss.amount >= 0 ? 'text-green-400' : 'text-red-400'
                }`}>
                  {profitLoss.amount >= 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                  ₹{profitLoss.amount.toFixed(2)} ({profitLoss.percentage.toFixed(2)}%)
                </div>
              </div>
            </div>
          </div>

          {/* Action Selection */}
          <div className="space-y-2">
            <Label htmlFor="action">Action</Label>
            <Select 
              value={formData.action} 
              onValueChange={(value) => handleInputChange('action', value)}
            >
              <SelectTrigger className="bg-gray-800 border-gray-700">
                <SelectValue placeholder="Select action" />
              </SelectTrigger>
              <SelectContent className="bg-gray-800 border-gray-700">
                {TRANSACTION_TYPES.map((type) => (
                  <SelectItem key={type.value} value={type.value} className="text-white hover:bg-gray-700">
                    <div>
                      <div className="font-medium">{type.label}</div>
                      <div className="text-xs text-gray-400">{type.description}</div>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {errors.action && (
              <p className="text-red-400 text-sm flex items-center gap-1">
                <AlertCircle className="h-4 w-4" />
                {errors.action}
              </p>
            )}
          </div>

          {/* Order Type */}
          {formData.action && (
            <div className="space-y-2">
              <Label htmlFor="order_type">Order Type</Label>
              <Select 
                value={formData.order_type} 
                onValueChange={(value) => handleInputChange('order_type', value)}
              >
                <SelectTrigger className="bg-gray-800 border-gray-700">
                  <SelectValue placeholder="Select order type" />
                </SelectTrigger>
                <SelectContent className="bg-gray-800 border-gray-700">
                  {ORDER_TYPES.map((type) => (
                    <SelectItem key={type.value} value={type.value} className="text-white hover:bg-gray-700">
                      <div>
                        <div className="font-medium">{type.label}</div>
                        <div className="text-xs text-gray-400">{type.description}</div>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {/* Quantity */}
          {formData.action && (
            <div className="space-y-2">
              <Label htmlFor="quantity">
                Quantity
                {formData.action === 'SELL' && (
                  <span className="text-sm text-gray-400 ml-2">
                    (Available: {Math.abs(position.quantity)})
                  </span>
                )}
              </Label>
              <Input
                id="quantity"
                type="number"
                value={formData.quantity}
                onChange={(e) => handleInputChange('quantity', e.target.value)}
                placeholder="Enter quantity"
                className="bg-gray-800 border-gray-700"
                min="1"
                step="1"
                disabled={formData.action === 'CLOSE'}
              />
              {errors.quantity && (
                <p className="text-red-400 text-sm flex items-center gap-1">
                  <AlertCircle className="h-4 w-4" />
                  {errors.quantity}
                </p>
              )}
            </div>
          )}

          {/* Price (for LIMIT orders) */}
          {requiresPrice && formData.action && (
            <div className="space-y-2">
              <Label htmlFor="price">Limit Price</Label>
              <Input
                id="price"
                type="number"
                value={formData.price}
                onChange={(e) => handleInputChange('price', e.target.value)}
                placeholder="Enter limit price"
                className="bg-gray-800 border-gray-700"
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

          {/* Estimated Value */}
          {estimatedValue > 0 && (
            <div className="bg-blue-900/20 p-3 rounded-lg border border-blue-700/30">
              <div className="flex items-center gap-2 text-blue-300">
                <DollarSign className="h-4 w-4" />
                <span className="text-sm font-medium">Estimated Value: ₹{estimatedValue.toFixed(2)}</span>
              </div>
            </div>
          )}

          <DialogFooter className="gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={handleCancel}
              disabled={isSubmitting}
              className="border-gray-700 text-gray-300 hover:bg-gray-800"
            >
              <X className="h-4 w-4 mr-2" />
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={isSubmitting || !formData.action}
              className="bg-blue-600 hover:bg-blue-700"
            >
              {isSubmitting ? (
                <div className="flex items-center gap-2">
                  <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full" />
                  Processing...
                </div>
              ) : (
                <>
                  <Settings className="h-4 w-4 mr-2" />
                  {formData.action === 'CLOSE' ? 'Close Position' : 'Place Order'}
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
