import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { TestTube } from 'lucide-react'

export default function BacktestingHub() {
  return (
    <div className="container-padding py-6 lg:py-8">
      <Card className="bg-gray-900/50 border-gray-800/50 max-w-2xl mx-auto">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <TestTube className="h-12 w-12 text-orange-400" />
          </div>
          <CardTitle className="text-slate-100">Backtesting Hub</CardTitle>
          <CardDescription className="text-slate-400">
            Test your strategies against historical data
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-slate-300 text-center">
            Validate your trading strategies with comprehensive backtesting using years of historical market data.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
