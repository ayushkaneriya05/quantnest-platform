import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Plug } from 'lucide-react'

export default function BrokerConnections() {
  return (
    <div className="container-padding py-6 lg:py-8">
      <Card className="bg-gray-900/50 border-gray-800/50 max-w-2xl mx-auto">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <Plug className="h-12 w-12 text-blue-400" />
          </div>
          <CardTitle className="text-slate-100">Broker Connections</CardTitle>
          <CardDescription className="text-slate-400">
            Connect your trading accounts
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-slate-300 text-center">
            Securely connect to 15+ major brokers including Interactive Brokers, TD Ameritrade, and Alpaca.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
