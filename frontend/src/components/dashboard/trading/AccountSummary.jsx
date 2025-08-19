import React, { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Wallet, TrendingUp, TrendingDown } from "lucide-react";
import api from "@/services/api";

const StatCard = ({ title, value, icon, change }) => (
  <div className="bg-gray-900/50 p-4 rounded-lg">
    <div className="flex items-center justify-between">
      <p className="text-sm font-medium text-slate-400">{title}</p>
      {icon}
    </div>
    <div className="mt-2">
      <p className="text-2xl font-bold text-slate-100">{value}</p>
      {change && (
        <p
          className={`text-xs ${
            change.includes("+") ? "text-emerald-400" : "text-red-400"
          }`}
        >
          {change}
        </p>
      )}
    </div>
  </div>
);

export default function AccountSummary() {
  const [account, setAccount] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAccountData = async () => {
      try {
        const response = await api.get("/trading/account/");
        setAccount(response.data);
      } catch (error) {
        console.error("Failed to fetch account data:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchAccountData();
  }, []);

  if (loading) {
    return <p className="text-slate-400">Loading account details...</p>;
  }

  if (!account) {
    return <p className="text-red-400">Could not load account details.</p>;
  }

  const formatCurrency = (value) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
    }).format(value);
  };

  return (
    <Card className="bg-transparent border-0 shadow-none">
      <CardHeader>
        <CardTitle className="text-2xl font-bold text-slate-100">
          Account Overview
        </CardTitle>
      </CardHeader>
      <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard
          title="Available Balance"
          value={formatCurrency(account.balance)}
          icon={<Wallet className="h-5 w-5 text-cyan-400" />}
        />
        <StatCard
          title="Unrealized P&L"
          value={formatCurrency(0.0)} // This would be calculated from positions
          icon={<TrendingUp className="h-5 w-5 text-emerald-400" />}
          change="+₹1,250.75 today"
        />
        <StatCard
          title="Margin Used"
          value={formatCurrency(account.margin)}
          icon={<TrendingDown className="h-5 w-5 text-red-400" />}
        />
      </CardContent>
    </Card>
  );
}
