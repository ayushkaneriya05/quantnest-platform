import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { CheckCircle2, GraduationCap } from "lucide-react";

import { Button } from "@/shared/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { learningApi } from "@/shared/services/learningApi";

export default function LessonDetail() {
  const { id } = useParams();
  const { notify } = useNotifications();
  const [lesson, setLesson] = useState(null);

  useEffect(() => {
    learningApi.getLesson(id).then((response) => setLesson(response.data)).catch(() => {});
  }, [id]);

  const complete = async () => {
    await learningApi.completeLesson(id, { time_spent_seconds: 300 });
    notify.success("Lesson completed");
  };

  return (
    <div className="container-padding py-6 lg:py-8">
      <Card className="border-gray-800 bg-gray-900/60">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-white">
            <GraduationCap className="h-5 w-5 text-blue-300" />
            {lesson?.title || "Lesson"}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="prose prose-invert max-w-none text-gray-300">
            <p>{lesson?.content || "Lesson content will appear here."}</p>
          </div>
          <Button className="bg-emerald-600 hover:bg-emerald-500" onClick={complete}>
            <CheckCircle2 className="mr-2 h-4 w-4" />
            Mark Complete
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
