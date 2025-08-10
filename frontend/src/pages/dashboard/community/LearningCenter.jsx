import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { GraduationCap } from 'lucide-react'

export default function LearningCenter() {
  return (
    <div className="container-padding py-6 lg:py-8">
      <Card className="bg-gray-900/50 border-gray-800/50 max-w-2xl mx-auto">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <GraduationCap className="h-12 w-12 text-blue-400" />
          </div>
          <CardTitle className="text-slate-100">Learning Center</CardTitle>
          <CardDescription className="text-slate-400">
            Educational resources and tutorials
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-slate-300 text-center">
            Access comprehensive tutorials, courses, and educational content to improve your trading skills.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
