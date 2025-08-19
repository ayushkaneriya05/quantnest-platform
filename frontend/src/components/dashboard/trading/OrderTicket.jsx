import React, { useState, useEffect } from "react";
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
import { useToast } from "@/hooks/use-toast";
import { Calculator, AlertCircle, DollarSign, X } from "lucide-react";
import api from "@/services/api";

export default function OrderTicket({
  symbol,
  transactionType,
  onOrderPlaced,
  onClose,
}) {
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState({
    transaction_type: transactionType,
    order_type: "MARKET",
    quantity: "",
    price: "",
    trigger_price: "",
  });
  
  const [estimatedValue, setEstimatedValue] = useState(0);
  const currentPrice = 2458.50; // Mock current price

  useEffect(() => {
    const quantity = parseInt(formData.quantity) || 0;
    const price = formData.order_type === "MARKET" 
      ? currentPrice 
      : parseFloat(formData.price) || currentPrice;
    
    setEstimatedValue(quantity * price);
  }, [formData.quantity, formData.price, formData.order_type]);

  const handleChange = (e) => {
    setFormData((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSelectChange = (name, value) => {
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleQuickQuantity = (qty) => {
    setFormData((prev) => ({ ...prev, quantity: qty.toString() }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      await api.post("/trading/orders/", {
        ...formData,
        instrument_symbol: symbol,
      });
      toast({ 
        title: "Order Placed", 
        description: `${formData.transaction_type} order for ${formData.quantity} shares of ${symbol} placed successfully.`,
        className: "bg-[#161b22] border-gray-700 text-white"
      });
      onOrderPlaced();
      // Reset form
      setFormData({
        transaction_type: transactionType,
        order_type: "MARKET",
        quantity: "",
        price: "",
        trigger_price: "",
      });
    } catch (error) {
      const errorMsg = error.response?.data?.detail || "Failed to place order.";
      toast({ 
        variant: "destructive", 
        title: "Order Failed", 
        description: errorMsg,
        className: "bg-red-900 border-red-700 text-white"
      });
    } finally {
      setIsLoading(false);
    }
  };

  const isFormValid = formData.quantity && 
    (formData.order_type === "MARKET" || (formData.order_type === "LIMIT" && formData.price));

  return (
    <div className="space-y-6">
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Order Type Selection */}
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-2">
            <Label className="text-gray-400 text-xs uppercase tracking-wider">Order Type</Label>
            <Select
              onValueChange={(v) => handleSelectChange("order_type", v)}
              value={formData.order_type}
            >
              <SelectTrigger className="bg-[#21262d] border-gray-700 text-white focus:border-gray-500 focus:ring-1 focus:ring-gray-500">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-[#21262d] border-gray-700">
                <SelectItem value="MARKET" className="text-white hover:bg-gray-700">
                  Market Order
                </SelectItem>
                <SelectItem value="LIMIT" className="text-white hover:bg-gray-700">
                  Limit Order
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label className="text-gray-400 text-xs uppercase tracking-wider">Transaction</Label>
            <Select
              onValueChange={(v) => handleSelectChange("transaction_type", v)}
              value={formData.transaction_type}
            >
              <SelectTrigger className="bg-[#21262d] border-gray-700 text-white focus:border-gray-500 focus:ring-1 focus:ring-gray-500">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-[#21262d] border-gray-700">
                <SelectItem value="BUY" className="text-emerald-400 hover:bg-gray-700">
                  Buy
                </SelectItem>
                <SelectItem value="SELL" className="text-red-400 hover:bg-gray-700">
                  Sell
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Quantity Input */}
        <div className="space-y-3">
          <Label className="text-gray-400 text-xs uppercase tracking-wider">Quantity</Label>
          <Input
            name="quantity"
            type="number"
            placeholder="Enter quantity"
            value={formData.quantity}
            onChange={handleChange}
            required
            className="bg-[#21262d] border-gray-700 text-white text-lg font-mono placeholder-gray-500 focus:border-gray-500 focus:ring-1 focus:ring-gray-500"
          />
          
          {/* Quick Quantity Buttons */}
          <div className="flex gap-2">
            {[1, 5, 10, 25, 50].map((qty) => (
              <Button
                key={qty}
                type="button"
                variant="outline"
                size="sm"
                onClick={() => handleQuickQuantity(qty)}
                className="bg-transparent border-gray-700 text-gray-400 hover:bg-gray-800 hover:text-white text-xs"
              >
                {qty}
              </Button>
            ))}
          </div>
        </div>

        {/* Price Input (for Limit Orders) */}
        {formData.order_type === "LIMIT" && (
          <div className="space-y-2">
            <Label className="text-gray-400 text-xs uppercase tracking-wider">Limit Price</Label>
            <Input
              name="price"
              type="number"
              step="0.01"
              placeholder="Enter limit price"
              value={formData.price}
              onChange={handleChange}
              required
              className="bg-[#21262d] border-gray-700 text-white text-lg font-mono placeholder-gray-500 focus:border-gray-500 focus:ring-1 focus:ring-gray-500"
            />
          </div>
        )}

        {/* Order Summary */}
        <div className="bg-[#161b22] rounded-lg p-4 border border-gray-700">
          <div className="flex items-center gap-2 mb-3">
            <Calculator className="h-4 w-4 text-gray-400" />
            <span className="text-sm font-medium text-gray-400 uppercase tracking-wider">Order Summary</span>
          </div>
          
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-400">Quantity:</span>
              <span className="text-white font-mono">{formData.quantity || '0'} shares</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Price:</span>
              <span className="text-white font-mono">
                {formData.order_type === "MARKET" 
                  ? `₹${currentPrice.toFixed(2)} (Market)` 
                  : `₹${formData.price || '0.00'}`}
              </span>
            </div>
            <div className="flex justify-between items-center pt-2 border-t border-gray-700">
              <span className="text-gray-400">Estimated Value:</span>
              <div className="flex items-center gap-2">
                <DollarSign className="h-4 w-4 text-gray-400" />
                <span className="text-white font-mono font-bold">
                  ₹{estimatedValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Risk Warning */}
        <div className="bg-orange-500/10 border border-orange-500/30 rounded-lg p-3">
          <div className="flex items-start gap-2">
            <AlertCircle className="h-4 w-4 text-orange-400 mt-0.5 flex-shrink-0" />
            <p className="text-xs text-orange-200">
              This is a paper trading environment. No real money is involved.
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3">
          <Button
            type="button"
            variant="outline"
            onClick={onClose}
            className="flex-1 border-gray-700 text-gray-400 hover:bg-gray-800 hover:text-white"
          >
            Cancel
          </Button>
          <Button
            type="submit"
            disabled={isLoading || !isFormValid}
            className={`flex-1 py-3 text-lg font-semibold transition-all duration-200 ${
              formData.transaction_type === "BUY"
                ? "bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-600/50"
                : "bg-red-600 hover:bg-red-700 disabled:bg-red-600/50"
            } disabled:cursor-not-allowed`}
          >
            {isLoading ? (
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Placing...
              </div>
            ) : (
              `${formData.transaction_type} ${formData.quantity || '0'} Shares`
            )}
          </Button>
        </div>
      </form>
    </div>
  );
}
