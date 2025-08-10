import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { BookOpen } from 'lucide-react'

export default function TradeJournal() {
  return (
    <div className="container-padding py-6 lg:py-8">
      <Card className="bg-gray-900/50 border-gray-800/50 max-w-2xl mx-auto">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <BookOpen className="h-12 w-12 text-amber-400" />
          </div>
          <CardTitle className="text-slate-100">Trade Journal</CardTitle>
          <CardDescription className="text-slate-400">
            Track and analyze your trading performance
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-slate-300 text-center">
            Keep detailed records of your trades with automated journaling and performance analysis.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
