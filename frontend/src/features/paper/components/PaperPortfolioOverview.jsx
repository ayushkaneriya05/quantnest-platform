import { useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";
import { Link } from "react-router-dom";
import { Card, CardContent } from "@/shared/components/ui/card";
import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { useStableCallback } from "@/shared/hooks/useStableCallback";
import { usePaperPositionsPnL } from "@/shared/hooks/useLivePositionsPnL";
import { usePaperTradingUpdate } from "@/shared/hooks/usePaperTradingWebSocket";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { paperApi } from "@/shared/services/paperApi";
import { formatCurrency } from "@/shared/utils/formatters";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { statusTone } from "@/shared/constants/statusColors";

export default function PaperPortfolioOverview({ account }) {
  const [positions, setPositions] = useState([]);
  const { notify } = useNotifications();
  const lastMessage = usePaperTradingUpdate();
  const loadPositions = useStableCallback(async () => {
    try {
      const response = await paperApi.getPositions();
      setPositions(response.data);
    } catch (error) { notify.error(getApiErrorMessage(error, "Failed to load Paper positions")); }
  });
  useEffect(() => { loadPositions(); }, [loadPositions]);
  useEffect(() => {
    if (!lastMessage) return undefined;
    const timer = setTimeout(loadPositions, 150);
    return () => clearTimeout(timer);
  }, [lastMessage, loadPositions]);
  const selectedPositions = useMemo(() => positions.filter((position) => position.account === account?.id), [positions, account?.id]);
  const { totals } = usePaperPositionsPnL(selectedPositions);
  if (!account) return <Card><CardContent className="space-y-3 py-12 text-center">
    <p>No Paper deployments yet</p><p className="text-sm text-muted-foreground">Start a session from My Strategies after funding your Paper wallet.</p>
    <Button asChild><Link to="/strategies">Go to My Strategies</Link></Button>
  </CardContent></Card>;
  const unrealized = totals.totalUnrealizedPnL;
  const metrics = [
    ["Session equity", Number(account.current_balance) + unrealized],
    ["Available capital", account.margin_available], ["Margin used", account.margin_used],
    ["Realized P&L", account.realized_pnl], ["Open P&L", unrealized],
    ["Lifetime P&L", Number(account.realized_pnl) + unrealized],
  ];
  return <div className="space-y-5">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div className="flex flex-wrap items-center gap-2"><h2 className="text-lg font-semibold">{account.name}</h2>
        <Badge className={statusTone[account.session_status] || statusTone.STOPPED}>{account.session_status}</Badge>
      </div><Button asChild variant="outline"><Link to="/paper">Manage deployments</Link></Button>
    </div>
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {metrics.map(([label, value]) => <Card key={label} className="border-border bg-card/50"><CardContent className="p-5">
        <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{label}</p>
        <p className="mt-2 text-2xl font-semibold">{formatCurrency(value)}</p>
      </CardContent></Card>)}
    </div>
    <p className="text-sm text-muted-foreground">{selectedPositions.length} open positions · {account.today_trades} trades closed today</p>
  </div>;
}
PaperPortfolioOverview.propTypes = { account: PropTypes.object };
