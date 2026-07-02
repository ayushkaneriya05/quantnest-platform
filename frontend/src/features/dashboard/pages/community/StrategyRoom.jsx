import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { MessageSquare, ShieldCheck } from "lucide-react";

import { Badge } from "@/shared/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { communityApi } from "@/shared/services/communityApi";

export default function StrategyRoom() {
  const { id } = useParams();
  const [room, setRoom] = useState(null);
  const [posts, setPosts] = useState([]);

  useEffect(() => {
    async function load() {
      const roomRes = await communityApi.getStrategyRoomByStrategy(id);
      setRoom(roomRes.data);
      const postRes = await communityApi.getPosts({ strategy_room: roomRes.data.id });
      setPosts(Array.isArray(postRes.data?.results) ? postRes.data.results : postRes.data || []);
    }
    load().catch(() => {});
  }, [id]);

  return (
    <div className="container-padding space-y-4 py-6 lg:py-8">
      <Card className="border-gray-800 bg-gray-900/60">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-white">
            <MessageSquare className="h-5 w-5 text-amber-300" />
            {room?.title || "Strategy Room"}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-gray-300">{room?.description || "Creator updates, optimization ideas, subscriber questions, and verified strategy discussion live here."}</p>
          <Badge className="mt-4 border-emerald-500/20 bg-emerald-500/10 text-emerald-300">
            <ShieldCheck className="mr-1 h-3 w-3" />
            Strategy-linked discussion
          </Badge>
        </CardContent>
      </Card>
      {posts.length === 0 ? (
        <Card className="border-gray-800 bg-gray-900/60">
          <CardContent className="py-12 text-center text-gray-400">No strategy room posts yet.</CardContent>
        </Card>
      ) : (
        posts.map((post) => (
          <Card key={post.id} className="border-gray-800 bg-gray-900/60">
            <CardContent className="p-5">
              <p className="font-semibold text-white">{post.title}</p>
              <p className="mt-2 text-sm text-gray-300">{post.body}</p>
            </CardContent>
          </Card>
        ))
      )}
    </div>
  );
}

