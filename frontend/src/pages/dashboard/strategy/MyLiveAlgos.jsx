import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Rocket } from 'lucide-react'

export default function MyLiveAlgos() {
  return (
    <div className="container-padding py-6 lg:py-8">
      <Card className="bg-gray-900/50 border-gray-800/50 max-w-2xl mx-auto">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <Rocket className="h-12 w-12 text-green-400" />
          </div>
          <CardTitle className="text-slate-100">My Live Algos</CardTitle>
          <CardDescription className="text-slate-400">
            Manage your active trading algorithms
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-slate-300 text-center">
            Monitor and control your live trading algorithms with real-time performance metrics.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
