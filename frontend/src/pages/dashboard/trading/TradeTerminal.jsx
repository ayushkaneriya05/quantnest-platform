import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Terminal } from 'lucide-react'

export default function TradeTerminal() {
  return (
    <div className="container-padding py-6 lg:py-8">
      <Card className="bg-gray-900/50 border-gray-800/50 max-w-2xl mx-auto">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <Terminal className="h-12 w-12 text-emerald-400" />
          </div>
          <CardTitle className="text-slate-100">Trade Terminal</CardTitle>
          <CardDescription className="text-slate-400">
            Professional trading interface
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-slate-300 text-center">
            Execute trades with our advanced trading terminal featuring real-time data and order management.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
