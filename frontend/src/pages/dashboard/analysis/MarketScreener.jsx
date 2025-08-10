import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { BarChart } from 'lucide-react'

export default function MarketScreener() {
  return (
    <div className="container-padding py-6 lg:py-8">
      <Card className="bg-gray-900/50 border-gray-800/50 max-w-2xl mx-auto">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <BarChart className="h-12 w-12 text-emerald-400" />
          </div>
          <CardTitle className="text-slate-100">Market Screener</CardTitle>
          <CardDescription className="text-slate-400">
            Powerful stock and market screening tools
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-slate-300 text-center">
            Screen thousands of stocks using technical indicators, fundamental metrics, and custom criteria.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
