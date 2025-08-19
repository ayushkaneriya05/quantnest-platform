import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { CreditCard } from "lucide-react";
import React from "react";

export default function PaperTrading() {
  return (
    <div className="container-padding py-6 lg:py-8">
      <Card className="bg-gray-900/50 border-gray-800/50 max-w-2xl mx-auto">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <CreditCard className="h-12 w-12 text-cyan-400" />
          </div>
          <CardTitle className="text-slate-100">Paper Trading</CardTitle>
          <CardDescription className="text-slate-400">
            Risk-free trading simulation
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-slate-300 text-center">
            Practice your trading strategies without risking real money using
            real-time market data.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
