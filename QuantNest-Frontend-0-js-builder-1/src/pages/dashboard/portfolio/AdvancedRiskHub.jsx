import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Shield } from 'lucide-react'

export default function AdvancedRiskHub() {
  return (
    <div className="container-padding py-6 lg:py-8">
      <Card className="bg-gray-900/50 border-gray-800/50 max-w-2xl mx-auto">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <Shield className="h-12 w-12 text-cyan-400" />
          </div>
          <CardTitle className="text-slate-100">Advanced Risk Hub</CardTitle>
          <CardDescription className="text-slate-400">
            Comprehensive risk management tools
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-slate-300 text-center">
            Monitor and manage portfolio risk with advanced analytics, VaR calculations, and stress testing.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
