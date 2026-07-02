import { useEffect, useMemo, useState } from "react";
import { Award, BarChart3, Medal, RefreshCw, ShieldCheck, Trophy } from "lucide-react";

import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { useSetPageActions } from "@/shared/hooks/useSetPageActions";
import { gamificationApi } from "@/shared/services/gamificationApi";
import { proofApi } from "@/shared/services/proofApi";
import { reputationApi } from "@/shared/services/reputationApi";

const categories = [
  { id: "VERIFIED_TRADER_SCORE", label: "Verified Trader", icon: ShieldCheck },
  { id: "JOURNAL_DISCIPLINE", label: "Discipline", icon: Medal },
  { id: "LEARNING_XP", label: "Learning", icon: Award },
  { id: "PAPER_PERFORMANCE", label: "Paper Trading", icon: BarChart3 },
  { id: "CREATOR_REPUTATION", label: "Creators", icon: Trophy },
  { id: "COMMUNITY_HELPFULNESS", label: "Helpful", icon: Medal },
];

const scopes = ["WEEKLY", "MONTHLY", "ALL_TIME"];

function listFromResponse(response) {
  return Array.isArray(response?.data?.results) ? response.data.results : response?.data || [];
}

export default function Leaderboards() {
  const { notify } = useNotifications();
  const [category, setCategory] = useState("VERIFIED_TRADER_SCORE");
  const [scope, setScope] = useState("WEEKLY");
  const [rows, setRows] = useState([]);
  const [me, setMe] = useState(null);
  const [proofs, setProofs] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      setLoading(true);
      const [leaderboardRes, reputationRes, proofRes] = await Promise.all([
        gamificationApi.getLeaderboards({ category, scope }),
        reputationApi.getMyReputation(),
        proofApi.getTradingProofs(),
      ]);
      setRows(listFromResponse(leaderboardRes));
      setMe(reputationRes.data || null);
      setProofs(listFromResponse(proofRes));
    } catch (error) {
      notify.error(error?.response?.data?.detail || "Failed to load leaderboards");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [category, scope]);

  useSetPageActions(
    <Button variant="outline" onClick={loadData} className="border-gray-700 text-gray-100">
      <RefreshCw className="mr-2 h-4 w-4" />
      Refresh
    </Button>,
  );

  const activeCategory = useMemo(() => categories.find((item) => item.id === category), [category]);
  const ActiveIcon = activeCategory?.icon || Trophy;
  const verifiedProofs = proofs.filter((proof) => proof.status === "VERIFIED").length;

  return (
    <div className="container-padding space-y-6 py-6 lg:py-8">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card className="border-gray-800 bg-gray-900/60">
          <CardContent className="p-5">
            <p className="text-xs uppercase tracking-[0.16em] text-gray-500">Credibility</p>
            <p className="mt-2 text-2xl font-semibold text-white">{Number(me?.credibility_score || 0).toFixed(0)}</p>
            <p className="mt-1 text-xs text-gray-400">Risk-adjusted trader score</p>
          </CardContent>
        </Card>
        <Card className="border-gray-800 bg-gray-900/60">
          <CardContent className="p-5">
            <p className="text-xs uppercase tracking-[0.16em] text-gray-500">Rule Follow</p>
            <p className="mt-2 text-2xl font-semibold text-emerald-300">{Number(me?.rule_follow_rate || 0).toFixed(0)}%</p>
            <p className="mt-1 text-xs text-gray-400">Journal-backed discipline</p>
          </CardContent>
        </Card>
        <Card className="border-gray-800 bg-gray-900/60">
          <CardContent className="p-5">
            <p className="text-xs uppercase tracking-[0.16em] text-gray-500">Sample Size</p>
            <p className="mt-2 text-2xl font-semibold text-cyan-300">{me?.sample_size || 0}</p>
            <p className="mt-1 text-xs text-gray-400">Confidence grows with data</p>
          </CardContent>
        </Card>
        <Card className="border-gray-800 bg-gray-900/60">
          <CardContent className="p-5">
            <p className="text-xs uppercase tracking-[0.16em] text-gray-500">Verified Proofs</p>
            <p className="mt-2 text-2xl font-semibold text-amber-300">{verifiedProofs}</p>
            <p className="mt-1 text-xs text-gray-400">Broker, paper, or replay proof</p>
          </CardContent>
        </Card>
      </div>

      <Card className="border-gray-800 bg-gray-900/60">
        <CardContent className="space-y-4 p-5">
          <div className="flex flex-wrap gap-2">
            {categories.map((item) => {
              const Icon = item.icon;
              return (
                <Button
                  key={item.id}
                  size="sm"
                  variant={category === item.id ? "default" : "outline"}
                  className={category === item.id ? "bg-yellow-600 hover:bg-yellow-500" : "border-gray-700 text-gray-200"}
                  onClick={() => setCategory(item.id)}
                >
                  <Icon className="mr-2 h-4 w-4" />
                  {item.label}
                </Button>
              );
            })}
          </div>
          <div className="flex flex-wrap gap-2">
            {scopes.map((item) => (
              <Button
                key={item}
                size="sm"
                variant={scope === item ? "default" : "outline"}
                className={scope === item ? "bg-gray-700" : "border-gray-700 text-gray-200"}
                onClick={() => setScope(item)}
              >
                {item.replace("_", " ")}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
        <Card className="border-gray-800 bg-gray-900/60">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-white">
              <ActiveIcon className="h-5 w-5 text-yellow-300" />
              {activeCategory?.label} Leaderboard
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="py-12 text-center text-gray-400">Loading leaderboard...</div>
            ) : rows.length === 0 ? (
              <div className="py-12 text-center text-gray-400">No ranked users yet. Snapshot jobs will populate this leaderboard as activity grows.</div>
            ) : (
              <div className="overflow-hidden rounded-lg border border-gray-800">
                <table className="w-full text-sm">
                  <thead className="bg-gray-950/80 text-left text-xs uppercase tracking-[0.14em] text-gray-500">
                    <tr>
                      <th className="px-4 py-3">Rank</th>
                      <th className="px-4 py-3">Trader</th>
                      <th className="px-4 py-3">Score</th>
                      <th className="px-4 py-3">Trust</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-800">
                    {rows.map((row) => (
                      <tr key={row.id} className="text-gray-200">
                        <td className="px-4 py-3 font-semibold text-white">#{row.rank}</td>
                        <td className="px-4 py-3">{row.username || "Trader"}</td>
                        <td className="px-4 py-3">{Number(row.score || 0).toFixed(2)}</td>
                        <td className="px-4 py-3">
                          {row.eligible ? (
                            <Badge className="border-emerald-500/20 bg-emerald-500/10 text-emerald-300">Eligible</Badge>
                          ) : (
                            <Badge className="border-amber-500/20 bg-amber-500/10 text-amber-300">Needs sample</Badge>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card className="border-gray-800 bg-gray-900/60">
            <CardHeader>
              <CardTitle className="text-white">Scoring Model</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-gray-300">
              {["Verified proof has priority over screenshots.", "Risk-adjusted metrics beat raw return.", "Low sample sizes reduce eligibility.", "Trust flags can remove users from rankings."].map((item) => (
                <div key={item} className="rounded-lg bg-black/20 px-3 py-2">{item}</div>
              ))}
            </CardContent>
          </Card>

          <Card className="border-gray-800 bg-gray-900/60">
            <CardHeader>
              <CardTitle className="text-white">Your Score Mix</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {[
                ["Consistency", me?.consistency_score],
                ["Discipline", me?.discipline_score],
                ["Transparency", me?.transparency_score],
                ["Risk", me?.risk_score],
                ["Sample Size", me?.sample_size_score],
              ].map(([label, value]) => (
                <div key={label}>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-400">{label}</span>
                    <span className="text-white">{Number(value || 0).toFixed(0)}</span>
                  </div>
                  <div className="mt-2 h-2 rounded-full bg-gray-800">
                    <div className="h-2 rounded-full bg-cyan-500" style={{ width: `${Math.min(Number(value || 0), 100)}%` }} />
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
