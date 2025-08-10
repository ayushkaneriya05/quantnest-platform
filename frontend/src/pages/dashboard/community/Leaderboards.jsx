import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Trophy } from 'lucide-react'

export default function Leaderboards() {
  return (
    <div className="container-padding py-6 lg:py-8">
      <Card className="bg-gray-900/50 border-gray-800/50 max-w-2xl mx-auto">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <Trophy className="h-12 w-12 text-yellow-400" />
          </div>
          <CardTitle className="text-slate-100">Leaderboards</CardTitle>
          <CardDescription className="text-slate-400">
            Compete with top traders
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-slate-300 text-center">
            See how your trading performance ranks against other QuantNest users across various metrics.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
