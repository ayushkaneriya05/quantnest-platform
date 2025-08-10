import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Database } from 'lucide-react'

export default function AlternativeDataHub() {
  return (
    <div className="container-padding py-6 lg:py-8">
      <Card className="bg-gray-900/50 border-gray-800/50 max-w-2xl mx-auto">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <Database className="h-12 w-12 text-cyan-400" />
          </div>
          <CardTitle className="text-slate-100">Alternative Data Hub</CardTitle>
          <CardDescription className="text-slate-400">
            Access unique datasets for trading insights
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-slate-300 text-center">
            Explore alternative data sources including satellite imagery, social sentiment, and economic indicators.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
