import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { LineChart, ShieldCheck } from "lucide-react";

import { Badge } from "@/shared/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { replayApi } from "@/shared/services/replayApi";

export default function TradeReplayView() {
  const { id } = useParams();
  const [replay, setReplay] = useState(null);

  useEffect(() => {
    replayApi.getReplays().then((response) => {
      const replays = Array.isArray(response.data?.results) ? response.data.results : response.data || [];
      setReplay(replays.find((item) => String(item.id) === String(id)) || null);
    }).catch(() => {});
  }, [id]);

  return (
    <div className="container-padding py-6 lg:py-8">
      <Card className="border-gray-800 bg-gray-900/60">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-white">
            <LineChart className="h-5 w-5 text-cyan-300" />
            {replay?.title || "Trade Replay"}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-gray-300">{replay?.description || "Replay snapshots preserve chart state, indicators, drawings, candles, execution markers, and journal context."}</p>
          <div className="rounded-lg border border-gray-800 bg-black/20 p-4">
            <p className="text-xs uppercase tracking-[0.14em] text-gray-500">Execution Markers</p>
            <pre className="mt-3 max-h-72 overflow-auto rounded bg-gray-950 p-3 text-xs text-gray-300">{JSON.stringify(replay?.execution_markers || [], null, 2)}</pre>
          </div>
          {replay?.is_immutable ? (
            <Badge className="border-emerald-500/20 bg-emerald-500/10 text-emerald-300">
              <ShieldCheck className="mr-1 h-3 w-3" />
              Published snapshot
            </Badge>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}

