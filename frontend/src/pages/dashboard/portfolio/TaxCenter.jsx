import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { CreditCard } from 'lucide-react'

export default function TaxCenter() {
  return (
    <div className="container-padding py-6 lg:py-8">
      <Card className="bg-gray-900/50 border-gray-800/50 max-w-2xl mx-auto">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <CreditCard className="h-12 w-12 text-green-400" />
          </div>
          <CardTitle className="text-slate-100">Tax Center</CardTitle>
          <CardDescription className="text-slate-400">
            Manage trading taxes and reporting
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-slate-300 text-center">
            Simplify tax preparation with automated trade reporting and tax optimization strategies.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
