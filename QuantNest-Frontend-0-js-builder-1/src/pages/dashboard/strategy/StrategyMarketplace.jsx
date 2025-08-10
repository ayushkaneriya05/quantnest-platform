import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Store } from 'lucide-react'

export default function StrategyMarketplace() {
  return (
    <div className="container-padding py-6 lg:py-8">
      <Card className="bg-gray-900/50 border-gray-800/50 max-w-2xl mx-auto">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <Store className="h-12 w-12 text-purple-400" />
          </div>
          <CardTitle className="text-slate-100">Strategy Marketplace</CardTitle>
          <CardDescription className="text-slate-400">
            Discover and share trading strategies
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-slate-300 text-center">
            Browse, purchase, and sell proven trading strategies from the QuantNest community.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
