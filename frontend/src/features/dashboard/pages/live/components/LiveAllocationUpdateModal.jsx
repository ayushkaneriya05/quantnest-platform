import React, { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/shared/components/ui/dialog";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select";
import { liveTradingApi } from "@/shared/services/liveTradingApi";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { Loader2 } from "lucide-react";

export default function LiveAllocationUpdateModal({
  session,
  open,
  onOpenChange,
  onSuccess,
}) {
  const { notify } = useNotifications();
  const [loading, setLoading] = useState(false);
  
  const currentAllocation = session?.allocation || {};
  const [allocationType, setAllocationType] = useState(
    currentAllocation.allocation_type || "FIXED"
  );
  const [amount, setAmount] = useState(
    allocationType === "FIXED" 
      ? currentAllocation.allocated_capital 
      : currentAllocation.allocated_percentage
  );

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      setLoading(true);
      const payload = {
        allocation_amount: allocationType === "FIXED" ? amount : null,
        allocation_percentage: allocationType === "PERCENTAGE" ? amount : null,
      };
      
      await liveTradingApi.updateAllocation(session.id, payload);
      notify.success("Strategy allocation updated successfully");
      onSuccess?.();
      onOpenChange(false);
    } catch (error) {
      let errorMsg = "Failed to update allocation";
      const data = error?.response?.data;
      if (typeof data === 'object' && data !== null) {
        if (data.error) errorMsg = data.error;
        else if (data.detail) errorMsg = data.detail;
        else if (data.non_field_errors) errorMsg = Array.isArray(data.non_field_errors) ? data.non_field_errors[0] : data.non_field_errors;
        else {
           const firstKey = Object.keys(data)[0];
           if (firstKey) {
             const firstError = data[firstKey];
             const msg = Array.isArray(firstError) ? firstError[0] : firstError;
             const displayKey = firstKey.charAt(0).toUpperCase() + firstKey.slice(1).replace(/_/g, ' ');
             errorMsg = `${displayKey}: ${msg}`;
           }
        }
      } else if (typeof data === 'string') {
        errorMsg = data;
      }
      notify.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px] bg-slate-900 border-slate-800 text-white">
        <DialogHeader>
          <DialogTitle>Update Strategy Allocation</DialogTitle>
          <DialogDescription className="text-slate-400">
            Change the capital allocated to {session?.strategy_name}.
          </DialogDescription>
        </DialogHeader>
        
        <form onSubmit={handleSubmit} className="space-y-6 py-4">
          <div className="space-y-2">
            <Label htmlFor="allocationType">Allocation Type</Label>
            <Select
              value={allocationType}
              onValueChange={(val) => {
                setAllocationType(val);
                setAmount("");
              }}
            >
              <SelectTrigger className="bg-slate-800 border-slate-700">
                <SelectValue placeholder="Select type" />
              </SelectTrigger>
              <SelectContent className="bg-slate-800 border-slate-700 text-white">
                <SelectItem value="FIXED">Fixed Amount (INR)</SelectItem>
                <SelectItem value="PERCENTAGE">Percentage of Equity (%)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="amount">
              {allocationType === "FIXED" ? "Amount (₹)" : "Percentage (%)"}
            </Label>
            <Input
              id="amount"
              type="number"
              step="0.01"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder={allocationType === "FIXED" ? "e.g. 50000" : "e.g. 10"}
              className="bg-slate-800 border-slate-700"
              required
            />
          </div>

          <div className="p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg text-xs text-blue-300">
            Note: Updating allocation will affect future orders. Existing positions will not be automatically adjusted.
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="ghost"
              onClick={() => onOpenChange(false)}
              disabled={loading}
              className="text-slate-400 hover:text-white"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={loading || !amount}
              className="bg-indigo-600 hover:bg-indigo-500 text-white min-w-[100px]"
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Updating...
                </>
              ) : (
                "Update Allocation"
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
