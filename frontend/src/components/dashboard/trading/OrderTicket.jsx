import React, { useState } from "react";
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
import api from "@/services/api";

export default function OrderTicket({ symbol, onOrderPlaced }) {
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState({
    transaction_type: "BUY",
    order_type: "MARKET",
    quantity: "",
    price: "",
    trigger_price: "",
  });

  const handleChange = (e) => {
    setFormData((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSelectChange = (name, value) => {
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      await api.post("/trading/orders/", {
        ...formData,
        instrument_symbol: symbol,
      });
      toast({ title: "Success", description: "Order placed successfully." });
      onOrderPlaced(); // Refresh parent component
      setFormData({
        transaction_type: "BUY",
        order_type: "MARKET",
        quantity: "",
        price: "",
        trigger_price: "",
      });
    } catch (error) {
      const errorMsg = error.response?.data?.detail || "Failed to place order.";
      toast({ variant: "destructive", title: "Error", description: errorMsg });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="p-4 bg-gray-950 border border-gray-800 rounded-lg space-y-4"
    >
      <h3 className="text-lg font-semibold text-slate-100">Trade {symbol}</h3>
      <div className="grid grid-cols-2 gap-4">
        <Select
          onValueChange={(v) => handleSelectChange("transaction_type", v)}
          defaultValue="BUY"
        >
          <SelectTrigger className="bg-gray-900">
            <SelectValue placeholder="Type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="BUY">Buy</SelectItem>
            <SelectItem value="SELL">Sell</SelectItem>
          </SelectContent>
        </Select>
        <Select
          onValueChange={(v) => handleSelectChange("order_type", v)}
          defaultValue="MARKET"
        >
          <SelectTrigger className="bg-gray-900">
            <SelectValue placeholder="Order Type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="MARKET">Market</SelectItem>
            <SelectItem value="LIMIT">Limit</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div>
        <Label htmlFor="quantity">Quantity</Label>
        <Input
          id="quantity"
          name="quantity"
          type="number"
          placeholder="0"
          value={formData.quantity}
          onChange={handleChange}
          required
          className="bg-gray-900"
        />
      </div>
      {formData.order_type === "LIMIT" && (
        <div>
          <Label htmlFor="price">Limit Price</Label>
          <Input
            id="price"
            name="price"
            type="number"
            placeholder="0.00"
            value={formData.price}
            onChange={handleChange}
            required
            className="bg-gray-900"
          />
        </div>
      )}
      <Button
        type="submit"
        disabled={isLoading}
        className="w-full bg-indigo-600 hover:bg-indigo-700"
      >
        {isLoading
          ? "Placing Order..."
          : `Place ${formData.transaction_type} Order`}
      </Button>
    </form>
  );
}
