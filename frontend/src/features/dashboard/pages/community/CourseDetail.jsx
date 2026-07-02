import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { BookOpen, PlayCircle } from "lucide-react";

import { Button } from "@/shared/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { learningApi } from "@/shared/services/learningApi";

export default function CourseDetail() {
  const { id } = useParams();
  const [course, setCourse] = useState(null);

  useEffect(() => {
    learningApi.getCourse(id).then((response) => setCourse(response.data)).catch(() => {});
  }, [id]);

  return (
    <div className="container-padding space-y-4 py-6 lg:py-8">
      <Card className="border-gray-800 bg-gray-900/60">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-white">
            <BookOpen className="h-5 w-5 text-blue-300" />
            {course?.title || "Course"}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-gray-300">{course?.description || "Course content will load here."}</p>
        </CardContent>
      </Card>
      {(course?.modules || []).map((module) => (
        <Card key={module.id} className="border-gray-800 bg-gray-900/60">
          <CardHeader>
            <CardTitle className="text-white">{module.title}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {(module.lessons || []).map((lesson) => (
              <div key={lesson.id} className="flex items-center justify-between rounded-lg border border-gray-800 bg-black/20 p-3">
                <span className="text-sm text-gray-200">{lesson.title}</span>
                <Button size="sm" className="bg-blue-600 hover:bg-blue-500">
                  <PlayCircle className="mr-2 h-4 w-4" />
                  Start
                </Button>
              </div>
            ))}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

