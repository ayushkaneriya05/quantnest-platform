import { useEffect, useMemo, useState } from "react";
import { Bookmark, Flag, Hash, MessageSquare, RefreshCw, Send, ShieldCheck, Sparkles, Users } from "lucide-react";

import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { Input } from "@/shared/components/ui/input";
import { Textarea } from "@/shared/components/ui/textarea";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { useSetPageActions } from "@/shared/hooks/useSetPageActions";
import { activityApi } from "@/shared/services/activityApi";
import { communityApi } from "@/shared/services/communityApi";
import { gamificationApi } from "@/shared/services/gamificationApi";

const feedTabs = [
  { id: "for-you", label: "For You" },
  { id: "following", label: "Following" },
  { id: "strategy-rooms", label: "Strategy Rooms" },
  { id: "learning", label: "Learning" },
];

const defaultComposer = {
  title: "",
  body: "",
  post_type: "QUESTION",
  hashtags: [],
};

function listFromResponse(response) {
  return Array.isArray(response?.data?.results) ? response.data.results : response?.data || [];
}

export default function SocialHub() {
  const { notify } = useNotifications();
  const [activeFeed, setActiveFeed] = useState("for-you");
  const [topics, setTopics] = useState([]);
  const [posts, setPosts] = useState([]);
  const [activity, setActivity] = useState([]);
  const [rooms, setRooms] = useState([]);
  const [challenges, setChallenges] = useState([]);
  const [selectedTopic, setSelectedTopic] = useState("");
  const [composer, setComposer] = useState(defaultComposer);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const loadData = async () => {
    try {
      setLoading(true);
      const [topicRes, postRes, activityRes, roomRes, challengeRes] = await Promise.all([
        communityApi.getTopics(),
        communityApi.getPosts({ topic: selectedTopic || undefined }),
        activityApi.getActivity({ feed: activeFeed, topic: selectedTopic || undefined }),
        communityApi.getStrategyRooms(),
        gamificationApi.getChallenges(),
      ]);
      setTopics(listFromResponse(topicRes));
      setPosts(listFromResponse(postRes));
      setActivity(listFromResponse(activityRes));
      setRooms(listFromResponse(roomRes));
      setChallenges(listFromResponse(challengeRes));
    } catch (error) {
      notify.error(error?.response?.data?.detail || "Failed to load community hub");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [activeFeed, selectedTopic]);

  useSetPageActions(
    <Button variant="outline" onClick={loadData} className="border-gray-700 text-gray-100">
      <RefreshCw className="mr-2 h-4 w-4" />
      Refresh
    </Button>,
  );

  const feedItems = useMemo(() => {
    if (posts.length) {
      return posts.map((post) => ({
        id: `post-${post.id}`,
        kind: post.post_type,
        title: post.title,
        summary: post.body,
        author: post.author_name,
        created_at: post.created_at,
        verified: post.is_verified_claim,
        topic: post.topic_slug,
        comments: post.comments_count || 0,
        reactions: post.reactions_count || 0,
        postId: post.id,
      }));
    }
    return activity.map((item) => ({
      id: `activity-${item.id}`,
      kind: item.activity_type,
      title: item.title,
      summary: item.summary,
      author: item.username,
      created_at: item.created_at,
      verified: item.metadata?.verified,
      topic: item.topic_slug,
      comments: 0,
      reactions: 0,
    }));
  }, [activity, posts]);

  const createPost = async () => {
    if (!composer.title.trim()) {
      notify.error("Add a title before posting");
      return;
    }
    try {
      setBusy(true);
      await communityApi.createPost({
        ...composer,
        topic: selectedTopic ? topics.find((topic) => topic.slug === selectedTopic)?.id : null,
        status: "PUBLISHED",
        visibility: "PUBLIC",
      });
      setComposer(defaultComposer);
      notify.success("Post published");
      await loadData();
    } catch (error) {
      notify.error(error?.response?.data?.detail || "Failed to publish post");
    } finally {
      setBusy(false);
    }
  };

  const react = async (postId) => {
    if (!postId) return;
    try {
      await communityApi.reactToPost(postId, "HELPFUL");
      await loadData();
    } catch (error) {
      notify.error("Could not update reaction");
    }
  };

  const bookmark = async (postId) => {
    if (!postId) return;
    try {
      await communityApi.bookmarkPost(postId);
      notify.success("Saved");
    } catch (error) {
      notify.error("Could not save post");
    }
  };

  return (
    <div className="container-padding space-y-6 py-6 lg:py-8">
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-4">
          <Card className="border-gray-800 bg-gray-900/60">
            <CardContent className="space-y-4 p-5">
              <div className="flex flex-wrap gap-2">
                {feedTabs.map((tab) => (
                  <Button
                    key={tab.id}
                    size="sm"
                    variant={activeFeed === tab.id ? "default" : "outline"}
                    className={activeFeed === tab.id ? "bg-amber-600 hover:bg-amber-500" : "border-gray-700 text-gray-200"}
                    onClick={() => setActiveFeed(tab.id)}
                  >
                    {tab.label}
                  </Button>
                ))}
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  size="sm"
                  variant={!selectedTopic ? "default" : "outline"}
                  className={!selectedTopic ? "bg-cyan-600 hover:bg-cyan-500" : "border-gray-700 text-gray-200"}
                  onClick={() => setSelectedTopic("")}
                >
                  All Topics
                </Button>
                {topics.slice(0, 8).map((topic) => (
                  <Button
                    key={topic.id}
                    size="sm"
                    variant={selectedTopic === topic.slug ? "default" : "outline"}
                    className={selectedTopic === topic.slug ? "bg-cyan-600 hover:bg-cyan-500" : "border-gray-700 text-gray-200"}
                    onClick={() => setSelectedTopic(topic.slug)}
                  >
                    <Hash className="mr-1 h-3.5 w-3.5" />
                    {topic.name}
                  </Button>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card className="border-gray-800 bg-gray-900/60">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-white">
                <Send className="h-4 w-4 text-amber-300" />
                Share With The Desk
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Input
                value={composer.title}
                onChange={(event) => setComposer((current) => ({ ...current, title: event.target.value }))}
                placeholder="Ask a question, share a journal lesson, or start a strategy discussion"
                className="border-gray-700 bg-black/20 text-white"
              />
              <Textarea
                value={composer.body}
                onChange={(event) => setComposer((current) => ({ ...current, body: event.target.value }))}
                placeholder="Add context, trade reasoning, risk notes, or learning takeaways"
                className="min-h-24 border-gray-700 bg-black/20 text-white"
              />
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-wrap gap-2">
                  {["QUESTION", "TRADE_REVIEW", "JOURNAL_LESSON", "STRATEGY_NOTE"].map((type) => (
                    <Button
                      key={type}
                      size="sm"
                      variant={composer.post_type === type ? "default" : "outline"}
                      className={composer.post_type === type ? "bg-gray-700" : "border-gray-700 text-gray-200"}
                      onClick={() => setComposer((current) => ({ ...current, post_type: type }))}
                    >
                      {type.replace("_", " ")}
                    </Button>
                  ))}
                </div>
                <Button className="bg-amber-600 hover:bg-amber-500" onClick={createPost} disabled={busy}>
                  <Send className="mr-2 h-4 w-4" />
                  Publish
                </Button>
              </div>
            </CardContent>
          </Card>

          {loading ? (
            <Card className="border-gray-800 bg-gray-900/60">
              <CardContent className="py-12 text-center text-gray-400">Loading community feed...</CardContent>
            </Card>
          ) : feedItems.length === 0 ? (
            <Card className="border-gray-800 bg-gray-900/60">
              <CardContent className="py-12 text-center text-gray-400">
                No community activity yet. The first useful post usually sets the tone.
              </CardContent>
            </Card>
          ) : (
            feedItems.map((item) => (
              <Card key={item.id} className="border-gray-800 bg-gray-900/60">
                <CardContent className="space-y-4 p-5">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge className="border-cyan-500/20 bg-cyan-500/10 text-cyan-300">{item.kind?.replace("_", " ")}</Badge>
                        {item.verified ? (
                          <Badge className="border-emerald-500/20 bg-emerald-500/10 text-emerald-300">
                            <ShieldCheck className="mr-1 h-3 w-3" />
                            Verified
                          </Badge>
                        ) : null}
                        {item.topic ? <Badge className="border-gray-700 bg-gray-800 text-gray-300">#{item.topic}</Badge> : null}
                      </div>
                      <h3 className="mt-3 text-lg font-semibold text-white">{item.title}</h3>
                      <p className="mt-1 text-sm text-gray-500">by {item.author || "QuantNest user"}</p>
                    </div>
                  </div>
                  <p className="text-sm leading-6 text-gray-300">{item.summary || "No additional context added."}</p>
                  <div className="flex flex-wrap gap-2">
                    <Button size="sm" variant="outline" className="border-gray-700 text-gray-100" onClick={() => react(item.postId)}>
                      <Sparkles className="mr-2 h-4 w-4" />
                      Helpful {item.reactions ? `(${item.reactions})` : ""}
                    </Button>
                    <Button size="sm" variant="outline" className="border-gray-700 text-gray-100">
                      <MessageSquare className="mr-2 h-4 w-4" />
                      Comments {item.comments ? `(${item.comments})` : ""}
                    </Button>
                    <Button size="sm" variant="outline" className="border-gray-700 text-gray-100" onClick={() => bookmark(item.postId)}>
                      <Bookmark className="mr-2 h-4 w-4" />
                      Save
                    </Button>
                    <Button size="sm" variant="ghost" className="text-gray-500 hover:text-rose-300">
                      <Flag className="mr-2 h-4 w-4" />
                      Report
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>

        <div className="space-y-4">
          <Card className="border-gray-800 bg-gray-900/60">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-white">
                <Users className="h-4 w-4 text-amber-300" />
                Strategy Rooms
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {rooms.length === 0 ? (
                <p className="text-sm text-gray-400">Rooms appear when strategies opt into community discussion.</p>
              ) : (
                rooms.slice(0, 5).map((room) => (
                  <div key={room.id} className="rounded-lg border border-gray-800 bg-black/20 p-3">
                    <p className="font-medium text-white">{room.title}</p>
                    <p className="mt-1 text-xs text-gray-400">{room.strategy_name}</p>
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          <Card className="border-gray-800 bg-gray-900/60">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-white">
                <ShieldCheck className="h-4 w-4 text-emerald-300" />
                Trust Layer
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-gray-300">
              <p>Community ranking favors verified trades, risk discipline, rule-follow rate, and useful contribution.</p>
              <div className="grid gap-2">
                {["Verified proof badges", "Anti-gaming XP controls", "AI moderation queue", "Sanitized trade sharing"].map((item) => (
                  <div key={item} className="rounded-lg bg-black/20 px-3 py-2 text-gray-300">{item}</div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card className="border-gray-800 bg-gray-900/60">
            <CardHeader>
              <CardTitle className="text-white">Active Challenges</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {challenges.length === 0 ? (
                <p className="text-sm text-gray-400">Simulation challenges will appear here once published.</p>
              ) : (
                challenges.slice(0, 4).map((challenge) => (
                  <div key={challenge.id} className="rounded-lg border border-gray-800 bg-black/20 p-3">
                    <p className="font-medium text-white">{challenge.title}</p>
                    <p className="mt-1 text-xs text-gray-400">{challenge.challenge_type?.replace("_", " ")}</p>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
