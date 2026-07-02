import { useEffect, useMemo, useState } from "react";
import { Award, BookOpen, Brain, CheckCircle2, GraduationCap, PlayCircle, RefreshCw, Target } from "lucide-react";

import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { useSetPageActions } from "@/shared/hooks/useSetPageActions";
import { gamificationApi } from "@/shared/services/gamificationApi";
import { learningApi } from "@/shared/services/learningApi";

function listFromResponse(response) {
  return Array.isArray(response?.data?.results) ? response.data.results : response?.data || [];
}

export default function LearningCenter() {
  const { notify } = useNotifications();
  const [paths, setPaths] = useState([]);
  const [courses, setCourses] = useState([]);
  const [progress, setProgress] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [certificates, setCertificates] = useState([]);
  const [challenges, setChallenges] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState("ALL");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");

  const loadData = async () => {
    try {
      setLoading(true);
      const [pathsRes, coursesRes, progressRes, recRes, certRes, challengeRes] = await Promise.all([
        learningApi.getPaths(),
        learningApi.getCourses(),
        learningApi.getProgress(),
        learningApi.getRecommendations(),
        learningApi.getCertificates(),
        gamificationApi.getChallenges(),
      ]);
      setPaths(listFromResponse(pathsRes));
      setCourses(listFromResponse(coursesRes));
      setProgress(listFromResponse(progressRes));
      setRecommendations(listFromResponse(recRes));
      setCertificates(listFromResponse(certRes));
      setChallenges(listFromResponse(challengeRes));
    } catch (error) {
      notify.error(error?.response?.data?.detail || "Failed to load learning center");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  useSetPageActions(
    <Button variant="outline" onClick={loadData} className="border-gray-700 text-gray-100">
      <RefreshCw className="mr-2 h-4 w-4" />
      Refresh
    </Button>,
  );

  const categories = useMemo(() => ["ALL", ...new Set(courses.map((course) => course.category).filter(Boolean))], [courses]);
  const visibleCourses = selectedCategory === "ALL" ? courses : courses.filter((course) => course.category === selectedCategory);
  const completedLessons = progress.filter((item) => item.is_completed).length;
  const avgProgress = courses.length ? courses.reduce((sum, course) => sum + Number(course.my_progress || 0), 0) / courses.length : 0;

  const enroll = async (course) => {
    try {
      setBusy(`enroll-${course.slug}`);
      await learningApi.enrollCourse(course.slug);
      notify.success("Course added to your learning path");
      await loadData();
    } catch (error) {
      notify.error(error?.response?.data?.detail || "Failed to enroll");
    } finally {
      setBusy("");
    }
  };

  const joinChallenge = async (challenge) => {
    try {
      setBusy(`challenge-${challenge.id}`);
      await gamificationApi.joinChallenge(challenge.id);
      notify.success("Challenge joined");
      await loadData();
    } catch (error) {
      notify.error(error?.response?.data?.detail || "Failed to join challenge");
    } finally {
      setBusy("");
    }
  };

  return (
    <div className="container-padding space-y-6 py-6 lg:py-8">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card className="border-gray-800 bg-gray-900/60">
          <CardContent className="p-5">
            <p className="text-xs uppercase tracking-[0.16em] text-gray-500">Courses</p>
            <p className="mt-2 text-2xl font-semibold text-white">{courses.length}</p>
            <p className="mt-1 text-xs text-gray-400">Published learning modules</p>
          </CardContent>
        </Card>
        <Card className="border-gray-800 bg-gray-900/60">
          <CardContent className="p-5">
            <p className="text-xs uppercase tracking-[0.16em] text-gray-500">Progress</p>
            <p className="mt-2 text-2xl font-semibold text-cyan-300">{avgProgress.toFixed(0)}%</p>
            <p className="mt-1 text-xs text-gray-400">Average enrolled progress</p>
          </CardContent>
        </Card>
        <Card className="border-gray-800 bg-gray-900/60">
          <CardContent className="p-5">
            <p className="text-xs uppercase tracking-[0.16em] text-gray-500">Completed Lessons</p>
            <p className="mt-2 text-2xl font-semibold text-emerald-300">{completedLessons}</p>
            <p className="mt-1 text-xs text-gray-400">Linked to XP and streaks</p>
          </CardContent>
        </Card>
        <Card className="border-gray-800 bg-gray-900/60">
          <CardContent className="p-5">
            <p className="text-xs uppercase tracking-[0.16em] text-gray-500">Certificates</p>
            <p className="mt-2 text-2xl font-semibold text-amber-300">{certificates.length}</p>
            <p className="mt-1 text-xs text-gray-400">Profile-ready proof</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
        <div className="space-y-4">
          <Card className="border-gray-800 bg-gray-900/60">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-white">
                <GraduationCap className="h-5 w-5 text-blue-300" />
                Learning Paths
              </CardTitle>
            </CardHeader>
            <CardContent>
              {paths.length === 0 ? (
                <div className="rounded-lg border border-dashed border-gray-800 p-6 text-center text-gray-400">
                  Learning paths will appear here once your content team publishes them.
                </div>
              ) : (
                <div className="grid gap-3 md:grid-cols-2">
                  {paths.map((path) => (
                    <div key={path.id} className="rounded-lg border border-gray-800 bg-black/20 p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="font-semibold text-white">{path.title}</p>
                          <p className="mt-2 text-sm leading-6 text-gray-400">{path.description || "Structured progression for trader growth."}</p>
                        </div>
                        <Badge className="border-blue-500/20 bg-blue-500/10 text-blue-300">{path.level}</Badge>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="border-gray-800 bg-gray-900/60">
            <CardContent className="flex flex-wrap gap-2 p-5">
              {categories.map((item) => (
                <Button
                  key={item}
                  size="sm"
                  variant={selectedCategory === item ? "default" : "outline"}
                  className={selectedCategory === item ? "bg-blue-600 hover:bg-blue-500" : "border-gray-700 text-gray-200"}
                  onClick={() => setSelectedCategory(item)}
                >
                  {item.replace("_", " ")}
                </Button>
              ))}
            </CardContent>
          </Card>

          <div className="grid gap-4 xl:grid-cols-2">
            {loading ? (
              <Card className="border-gray-800 bg-gray-900/60 xl:col-span-2">
                <CardContent className="py-12 text-center text-gray-400">Loading courses...</CardContent>
              </Card>
            ) : visibleCourses.length === 0 ? (
              <Card className="border-gray-800 bg-gray-900/60 xl:col-span-2">
                <CardContent className="py-12 text-center text-gray-400">No courses published in this category yet.</CardContent>
              </Card>
            ) : (
              visibleCourses.map((course) => (
                <Card key={course.id} className="border-gray-800 bg-gray-900/60">
                  <CardHeader>
                    <div className="flex items-start justify-between gap-3">
                      <CardTitle className="text-white">{course.title}</CardTitle>
                      <Badge className="border-gray-700 bg-gray-800 text-gray-300">{course.level}</Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <p className="text-sm leading-6 text-gray-300">{course.description || "Focused lessons, quizzes, and applied trading exercises."}</p>
                    <div className="grid gap-3 sm:grid-cols-2">
                      <div className="rounded-lg bg-black/20 p-3">
                        <p className="text-xs uppercase tracking-[0.14em] text-gray-500">Category</p>
                        <p className="mt-1 text-sm text-white">{course.category?.replace("_", " ")}</p>
                      </div>
                      <div className="rounded-lg bg-black/20 p-3">
                        <p className="text-xs uppercase tracking-[0.14em] text-gray-500">Progress</p>
                        <p className="mt-1 text-sm text-white">{Number(course.my_progress || 0).toFixed(0)}%</p>
                      </div>
                    </div>
                    <div className="h-2 rounded-full bg-gray-800">
                      <div className="h-2 rounded-full bg-blue-500" style={{ width: `${Math.min(Number(course.my_progress || 0), 100)}%` }} />
                    </div>
                    <Button className="w-full bg-blue-600 hover:bg-blue-500" onClick={() => enroll(course)} disabled={busy === `enroll-${course.slug}`}>
                      <PlayCircle className="mr-2 h-4 w-4" />
                      Continue Path
                    </Button>
                  </CardContent>
                </Card>
              ))
            )}
          </div>
        </div>

        <div className="space-y-4">
          <Card className="border-gray-800 bg-gray-900/60">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-white">
                <Brain className="h-4 w-4 text-fuchsia-300" />
                Adaptive Recommendations
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {recommendations.length === 0 ? (
                <p className="text-sm text-gray-400">Recommendations will be created from journal mistakes, quiz gaps, and risk signals.</p>
              ) : (
                recommendations.slice(0, 5).map((item) => (
                  <div key={item.id} className="rounded-lg border border-gray-800 bg-black/20 p-3">
                    <div className="flex items-center justify-between gap-2">
                      <p className="font-medium text-white">{item.title}</p>
                      <Badge className="border-fuchsia-500/20 bg-fuchsia-500/10 text-fuchsia-300">{item.priority}</Badge>
                    </div>
                    <p className="mt-2 text-xs leading-5 text-gray-400">{item.reason}</p>
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          <Card className="border-gray-800 bg-gray-900/60">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-white">
                <Target className="h-4 w-4 text-amber-300" />
                Simulation Challenges
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {challenges.length === 0 ? (
                <p className="text-sm text-gray-400">Market replay, crash survival, and drawdown challenges will appear here.</p>
              ) : (
                challenges.slice(0, 4).map((challenge) => (
                  <div key={challenge.id} className="rounded-lg border border-gray-800 bg-black/20 p-3">
                    <p className="font-medium text-white">{challenge.title}</p>
                    <p className="mt-1 text-xs text-gray-400">{challenge.challenge_type?.replace("_", " ")}</p>
                    <Button size="sm" className="mt-3 bg-amber-600 hover:bg-amber-500" onClick={() => joinChallenge(challenge)} disabled={busy === `challenge-${challenge.id}`}>
                      Join Challenge
                    </Button>
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          <Card className="border-gray-800 bg-gray-900/60">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-white">
                <Award className="h-4 w-4 text-emerald-300" />
                Certificates
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {certificates.length === 0 ? (
                <p className="text-sm text-gray-400">Complete required lessons and quizzes to earn certificates.</p>
              ) : (
                certificates.map((certificate) => (
                  <div key={certificate.id} className="flex items-center gap-3 rounded-lg bg-black/20 p-3">
                    <CheckCircle2 className="h-5 w-5 text-emerald-300" />
                    <div>
                      <p className="text-sm font-medium text-white">{certificate.course_title}</p>
                      <p className="text-xs text-gray-500">{certificate.certificate_code}</p>
                    </div>
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          <Card className="border-gray-800 bg-gray-900/60">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-white">
                <BookOpen className="h-4 w-4 text-cyan-300" />
                Product Labs
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm text-gray-300">
              {["Create a journal entry from a real trade.", "Run a backtest and explain the drawdown.", "Build a strategy and submit a risk review.", "Share a trade replay with annotations."].map((item) => (
                <div key={item} className="rounded-lg bg-black/20 px-3 py-2">{item}</div>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
