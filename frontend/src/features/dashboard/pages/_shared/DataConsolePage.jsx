import { useEffect, useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import { Badge } from "@/shared/components/ui/badge";
import { Loader2, RefreshCw } from "lucide-react";
import { usePageActions } from "@/shared/context/PageActionsContext";
import { useNotifications } from "@/shared/hooks/useNotifications";

function normalizeRows(data, selectRows) {
  const payload = selectRows ? selectRows(data) : data;
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload?.results)) return payload.results;
  if (payload && typeof payload === "object") return [payload];
  return [];
}

export default function DataConsolePage({
  title,
  subtitle,
  fetcher,
  selectRows,
  renderCard,
  headerActions = [],
  emptyState = "No records found",
}) {
  const { notify } = useNotifications();
  const { setPageActions, clearPageActions } = usePageActions();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      setLoading(true);
      const response = await fetcher();
      setRows(normalizeRows(response.data, selectRows));
    } catch (error) {
      notify.error(`Failed to load ${title}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const actions = useMemo(() => headerActions, [headerActions]);

  useEffect(() => {
    setPageActions(
      <>
        {actions.map((action) => (
          <Button
            key={action.label}
            onClick={async () => {
              await action.onClick();
              await loadData();
            }}
            className="bg-cyan-600 hover:bg-cyan-500"
          >
            {action.label}
          </Button>
        ))}
        <Button variant="outline" onClick={loadData} className="border-gray-700 text-gray-100">
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </>
    );
    return () => clearPageActions();
  }, [actions, setPageActions, clearPageActions]);

  return (
    <div className="container-padding py-6 lg:py-8 space-y-6">
      {loading ? (
        <div className="flex justify-center py-20 text-cyan-300">
          <Loader2 className="h-8 w-8 animate-spin" />
        </div>
      ) : rows.length === 0 ? (
        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-12 text-center text-gray-400">{emptyState}</CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
          {rows.map((row, index) => (
            <Card key={row.id || index} className="bg-gray-900/60 border-gray-800">
              <CardHeader>
                <CardTitle className="text-white text-base flex items-center justify-between gap-3">
                  <span className="truncate">{row.title || row.name || row.strategy_name || row.instrument_symbol || row.entity_name || `${title} #${row.id || index + 1}`}</span>
                  <Badge className="bg-cyan-500/10 text-cyan-300 border-cyan-500/20">
                    {row.status || row.status_code || row.severity || row.type || row.action || "LIVE"}
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>{renderCard(row)}</CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
