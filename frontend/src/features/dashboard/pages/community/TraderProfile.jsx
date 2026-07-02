import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { ShieldCheck, UserCircle } from "lucide-react";

import { Badge } from "@/shared/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { communityApi } from "@/shared/services/communityApi";
import { reputationApi } from "@/shared/services/reputationApi";

export default function TraderProfile() {
  const { username } = useParams();
  const [profile, setProfile] = useState(null);
  const [reputation, setReputation] = useState(null);

  useEffect(() => {
    async function load() {
      const [profileRes, reputationRes] = await Promise.allSettled([
        communityApi.getProfiles({ search: username }),
        reputationApi.getProfiles(),
      ]);
      const profiles = Array.isArray(profileRes.value?.data?.results) ? profileRes.value.data.results : profileRes.value?.data || [];
      const reps = Array.isArray(reputationRes.value?.data?.results) ? reputationRes.value.data.results : reputationRes.value?.data || [];
      setProfile(profiles.find((item) => item.username === username) || profiles[0] || null);
      setReputation(reps.find((item) => item.username === username) || null);
    }
    load();
  }, [username]);

  return (
    <div className="container-padding py-6 lg:py-8">
      <Card className="border-gray-800 bg-gray-900/60">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-white">
            <UserCircle className="h-5 w-5 text-amber-300" />
            {profile?.display_name || profile?.username || username}
          </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 lg:grid-cols-[1fr_320px]">
          <div className="space-y-4">
            <p className="text-gray-300">{profile?.headline || profile?.bio || "This trader has not published a community profile yet."}</p>
            <div className="flex flex-wrap gap-2">
              <Badge className="border-cyan-500/20 bg-cyan-500/10 text-cyan-300">{profile?.trader_level || "TRADER"}</Badge>
              {profile?.trader_archetype ? <Badge className="border-amber-500/20 bg-amber-500/10 text-amber-300">{profile.trader_archetype}</Badge> : null}
              {reputation ? (
                <Badge className="border-emerald-500/20 bg-emerald-500/10 text-emerald-300">
                  <ShieldCheck className="mr-1 h-3 w-3" />
                  Reputation tracked
                </Badge>
              ) : null}
            </div>
          </div>
          <div className="grid gap-3">
            {[
              ["Credibility", reputation?.credibility_score],
              ["Discipline", reputation?.discipline_score],
              ["Sample Size", reputation?.sample_size],
            ].map(([label, value]) => (
              <div key={label} className="rounded-lg border border-gray-800 bg-black/20 p-4">
                <p className="text-xs uppercase tracking-[0.14em] text-gray-500">{label}</p>
                <p className="mt-2 text-xl font-semibold text-white">{Number(value || 0).toFixed(0)}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
