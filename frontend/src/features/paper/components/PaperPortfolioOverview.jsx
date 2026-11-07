import { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { Link } from "react-router-dom";
import { Card, CardContent } from "@/shared/components/ui/card";
import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { usePaperTradingUpdate } from "@/shared/hooks/usePaperTradingWebSocket";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { paperApi } from "@/shared/services/paperApi";
import { formatCurrency, formatNumber } from "@/shared/utils/formatters";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { statusTone } from "@/shared/constants/statusColors";
import { useLivePositionSummary } from "@/shared/hooks/useLivePositionsPnL";

export default function PaperPortfolioOverview({ account, refreshKey = 0 }) {
  const [snapshot, setSummary] = useState(null);
  const summary = useLivePositionSummary(snapshot?.accountId === account?.id ? snapshot?.data : null);
  const { notify } = useNotifications();
  const lastMessage = usePaperTradingUpdate();
  useEffect(() => {
    const controller = new AbortController();
    if (!account?.id) return undefined;
    const timer = setTimeout(() => {
      paperApi.getPositionsSummary({ account_id: account.id }, controller.signal)
        .then(response => { if (!controller.signal.aborted) setSummary({ accountId: account.id, data: response.data }); })
        .catch(error => { if (!controller.signal.aborted) notify.error(getApiErrorMessage(error, "Failed to load Paper positions")); });
    }, lastMessage ? 150 : 0);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [account?.id, refreshKey, lastMessage, notify]);
  if (!account) return <Card><CardContent className="space-y-3 py-12 text-center">
    <p>No Paper deployments yet</p><p className="text-sm text-muted-foreground">Start a session from My Strategies after funding your Paper wallet.</p>
    <Button asChild><Link to="/strategies">Go to My Strategies</Link></Button>
  </CardContent></Card>;
  const unrealized = Number(summary.unrealized_pnl || 0);
  const metrics = [
    ["Session equity", Number(account.current_balance) + unrealized],
    ["Available capital", account.margin_available], ["Margin used", account.margin_used],
    ["Realized P&L", account.realized_pnl], ["Open P&L", unrealized],
    ["Lifetime P&L", Number(account.realized_pnl) + unrealized],
  ];
  return <div className="space-y-3">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div className="flex flex-wrap items-center gap-2"><h2 className="text-lg font-semibold">{account.name}</h2>
        <Badge className={statusTone[account.session_status] || statusTone.STOPPED}>{account.session_status}</Badge>
      </div><Button asChild variant="outline"><Link to="/paper">Manage deployments</Link></Button>
    </div>
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {metrics.map(([label, value]) => <Card key={label} className="border-border bg-card/50"><CardContent className="p-3">
        <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{label}</p>
        <p className="mt-2 text-2xl font-semibold">{formatCurrency(value)}</p>
      </CardContent></Card>)}
    </div>
    <p className="text-sm text-muted-foreground">{summary.count || 0} open positions · {formatNumber(account.today_trades, { maximumFractionDigits: 0 })} trades closed today</p>
  </div>;
}
PaperPortfolioOverview.propTypes = { account: PropTypes.object, refreshKey: PropTypes.number };
