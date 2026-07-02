import React, { useState } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
import { Badge } from "@/shared/components/ui/badge";
import { ChevronDown, ChevronUp, AlertCircle, CheckCircle } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { formatNumber, formatDateTime } from "@/shared/utils/formatters";
import { statusTone } from "@/shared/constants/statusColors";

export default function LiveStrategiesOverview({ sessions = [] }) {
  const [expandedSession, setExpandedSession] = useState(null);

  if (sessions.length === 0) {
    return (
      <Card className="bg-slate-900/50 border-slate-800">
        <CardContent className="py-16 text-center">
          <AlertCircle className="h-12 w-12 text-slate-600 mx-auto mb-4" />
          <p className="text-slate-400 text-lg">No strategies deployed</p>
          <p className="text-slate-500 text-sm mt-1">
            Deploy strategies from the strategy list to see them here
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      <Card className="bg-slate-900/50 border-slate-800">
        <CardHeader>
          <CardTitle className="text-lg">
            Active Strategies ({sessions.length})
          </CardTitle>
        </CardHeader>
      </Card>

      {sessions.map((session) => (
        <div
          key={session.id}
          className="border border-slate-700 bg-slate-900/40 rounded-lg overflow-hidden shadow-lg transition-all hover:border-slate-600"
        >
          {/* Compact Header */}
          <div
            className="flex flex-col lg:flex-row lg:items-center justify-between p-4 gap-4 cursor-pointer hover:bg-slate-800/20 transition-colors"
            onClick={() =>
              setExpandedSession(
                expandedSession === session.id ? null : session.id,
              )
            }
          >
            {/* Status & Name */}
            <div className="flex items-center gap-4 flex-1 min-w-0">
              <Badge
                className={statusTone[session.status] || statusTone.STOPPED}
              >
                {session.status}
              </Badge>
              <div className="min-w-0 flex-1">
                <h3 className="font-semibold text-white truncate">
                  {session.strategy_name}
                </h3>
                <p className="text-xs text-slate-500">
                  {session.broker_label || session.broker_name || "No broker"}
                </p>
              </div>
            </div>

            {/* Key Metrics */}
            <div className="grid grid-cols-3 gap-8 lg:flex lg:items-center lg:gap-6 text-sm">
              <div className="text-center lg:text-right">
                <p className="text-slate-500 text-xs uppercase tracking-wider font-bold mb-1">
                  P&L
                </p>
                <p
                  className={`font-bold text-lg ${Number(session.pnl || 0) >= 0 ? "text-emerald-400" : "text-rose-400"}`}
                >
                  ₹{formatNumber(session.pnl)}
                </p>
              </div>
              <div className="text-center lg:text-right">
                <p className="text-slate-500 text-xs uppercase tracking-wider font-bold mb-1">
                  Trades
                </p>
                <p className="text-slate-300 font-bold text-lg">
                  {session.trades_count}
                </p>
              </div>
              <div className="text-center lg:text-right">
                <p className="text-slate-500 text-xs uppercase tracking-wider font-bold mb-1">
                  Positions
                </p>
                <p className="text-slate-300 font-bold text-lg">
                  {session.open_positions}
                </p>
              </div>
            </div>

            {/* Expand Button */}
            <Button
              variant="ghost"
              size="sm"
              className="lg:ml-4 h-8 w-8 p-0 text-slate-400 hover:text-slate-200"
              onClick={(e) => {
                e.stopPropagation();
                setExpandedSession(
                  expandedSession === session.id ? null : session.id,
                );
              }}
            >
              {expandedSession === session.id ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </Button>
          </div>

          {/* Expanded Details */}
          {expandedSession === session.id && (
            <div className="border-t border-slate-700 bg-slate-800/20 p-4 space-y-4">
              {/* Health & Status */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 bg-slate-800/30 rounded-lg border border-slate-700">
                  <div className="flex items-center gap-3 mb-2">
                    {session.broker_session_valid ? (
                      <CheckCircle className="h-4 w-4 text-emerald-400" />
                    ) : (
                      <AlertCircle className="h-4 w-4 text-amber-400" />
                    )}
                    <p className="font-medium text-white">Session Health</p>
                  </div>
                  <p
                    className={
                      session.broker_session_valid
                        ? "text-emerald-400 text-sm"
                        : "text-amber-400 text-sm"
                    }
                  >
                    {session.broker_session_valid
                      ? "Ready"
                      : "Requires reconnection"}
                  </p>
                </div>

                <div className="p-4 bg-slate-800/30 rounded-lg border border-slate-700">
                  <p className="text-slate-500 text-xs uppercase tracking-wider font-bold mb-2">
                    Started
                  </p>
                  <p className="text-slate-300 text-sm">
                    {formatDateTime(session.started_at)}
                  </p>
                </div>
              </div>

              {/* Allocation Details */}
              {session.allocation && (
                <div className="p-4 bg-slate-800/30 rounded-lg border border-slate-700">
                  <p className="text-slate-500 text-xs uppercase tracking-wider font-bold mb-3">
                    Capital Allocation
                  </p>
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <p className="text-slate-500 text-xs mb-1">Allocated</p>
                      <p className="text-white font-semibold">
                        ₹{formatNumber(session.allocation.allocated_capital)}
                      </p>
                    </div>
                    <div>
                      <p className="text-slate-500 text-xs mb-1">Used</p>
                      <p className="text-white font-semibold">
                        ₹{formatNumber(session.allocation.used_capital)}
                      </p>
                    </div>
                    <div>
                      <p className="text-slate-500 text-xs mb-1">Available</p>
                      <p className="text-white font-semibold">
                        ₹{formatNumber(session.allocation.available_capital)}
                      </p>
                    </div>
                  </div>

                  {/* Utilization Bar */}
                  <div className="mt-3">
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-xs text-slate-500">
                        Capital Utilization
                      </p>
                      <p className="text-xs text-slate-300">
                        {(
                          (session.allocation.used_capital /
                            session.allocation.allocated_capital) *
                          100
                        ).toFixed(1)}
                        %
                      </p>
                    </div>
                    <div className="w-full h-2 bg-slate-700 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${
                          session.allocation.used_capital /
                            session.allocation.allocated_capital >
                          0.9
                            ? "bg-rose-500"
                            : session.allocation.used_capital /
                                  session.allocation.allocated_capital >
                                0.7
                              ? "bg-amber-500"
                              : "bg-emerald-500"
                        }`}
                        style={{
                          width: `${Math.min(100, (session.allocation.used_capital / session.allocation.allocated_capital) * 100)}%`,
                        }}
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Error Message */}
              {session.error_message && (
                <div className="p-3 bg-rose-500/5 border border-rose-500/30 rounded-lg flex items-start gap-3">
                  <AlertCircle className="h-4 w-4 text-rose-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-rose-300 text-sm font-medium">Error</p>
                    <p className="text-rose-200 text-sm">
                      {session.error_message}
                    </p>
                  </div>
                </div>
              )}

              {/* Additional Metrics */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                <div className="p-3 bg-slate-800/30 rounded-lg border border-slate-700">
                  <p className="text-slate-500 text-xs uppercase tracking-wider font-bold mb-1">
                    Open Orders
                  </p>
                  <p className="text-white font-bold">
                    {session.active_orders}
                  </p>
                </div>
                <div className="p-3 bg-slate-800/30 rounded-lg border border-slate-700">
                  <p className="text-slate-500 text-xs uppercase tracking-wider font-bold mb-1">
                    Win Rate
                  </p>
                  <p className="text-white font-bold">
                    {session.win_rate || "-"}
                  </p>
                </div>
                <div className="p-3 bg-slate-800/30 rounded-lg border border-slate-700">
                  <p className="text-slate-500 text-xs uppercase tracking-wider font-bold mb-1">
                    Risk/Reward
                  </p>
                  <p className="text-white font-bold">
                    {session.risk_reward || "-"}
                  </p>
                </div>
                <div className="p-3 bg-slate-800/30 rounded-lg border border-slate-700">
                  <p className="text-slate-500 text-xs uppercase tracking-wider font-bold mb-1">
                    Max DD
                  </p>
                  <p className="text-white font-bold">
                    {session.max_drawdown || "-"}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
