// src/pages/dashboard/trading/PaperTrading.jsx
import React from "react";
import PaperTradingTerminal from "@/components/trading/PaperTradingTerminal";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

export default function PaperTrading() {
  return (
    <div className="container-padding py-6 lg:py-8">
      <Card className="bg-gray-900/50 border-gray-800/50">
        <CardHeader>
          <CardTitle className="text-slate-100">
            Paper Trading Terminal
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <PaperTradingTerminal />
        </CardContent>
      </Card>
    </div>
  );
}
