// src/components/trading/AuditLogs.jsx
import { useEffect, useState } from "react";
import { useTrading } from "@/contexts/TradingContext";

export default function AuditLogs() {
  const trading = useTrading();
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    try {
      await trading.fetchAuditLogs();
    } catch (e) {
      console.warn(e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="space-y-2">
      {loading && <div className="text-sm text-muted-foreground">loading…</div>}
      <div className="max-h-48 overflow-auto text-xs">
        {trading.auditLogs.map((a) => (
          <div key={a.id} className="p-2 border-b border-slate-800">
            <div className="font-medium">
              {a.action} — {a.timestamp}
            </div>
            <div className="text-muted">
              {a.performed_by || "system"} • order {a.order}
            </div>
            <div className="text-xs mt-1">{JSON.stringify(a.details)}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
