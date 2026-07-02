import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Target } from "lucide-react";

import { Button } from "@/shared/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { gamificationApi } from "@/shared/services/gamificationApi";

export default function ChallengeDetail() {
  const { id } = useParams();
  const { notify } = useNotifications();
  const [challenge, setChallenge] = useState(null);

  useEffect(() => {
    gamificationApi.getChallenges().then((response) => {
      const rows = Array.isArray(response.data?.results) ? response.data.results : response.data || [];
      setChallenge(rows.find((item) => String(item.id) === String(id)) || null);
    }).catch(() => {});
  }, [id]);

  const join = async () => {
    await gamificationApi.joinChallenge(id);
    notify.success("Challenge joined");
  };

  return (
    <div className="container-padding py-6 lg:py-8">
      <Card className="border-gray-800 bg-gray-900/60">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-white">
            <Target className="h-5 w-5 text-amber-300" />
            {challenge?.title || "Simulation Challenge"}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-gray-300">{challenge?.description || "Practice under drawdown, risk, replay, and market-event constraints."}</p>
          <pre className="max-h-80 overflow-auto rounded-lg border border-gray-800 bg-black/20 p-4 text-xs text-gray-300">{JSON.stringify(challenge?.rules || {}, null, 2)}</pre>
          <Button className="bg-amber-600 hover:bg-amber-500" onClick={join}>Join Challenge</Button>
        </CardContent>
      </Card>
    </div>
  );
}

