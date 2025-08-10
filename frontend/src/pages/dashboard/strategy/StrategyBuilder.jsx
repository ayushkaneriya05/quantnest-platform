import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Code } from 'lucide-react'

export default function StrategyBuilder() {
  return (
    <div className="container-padding py-6 lg:py-8">
      <Card className="bg-gray-900/50 border-gray-800/50 max-w-2xl mx-auto">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <Code className="h-12 w-12 text-indigo-400" />
          </div>
          <CardTitle className="text-slate-100">Strategy Builder</CardTitle>
          <CardDescription className="text-slate-400">
            Build sophisticated trading strategies with visual tools
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-slate-300 text-center">
            Create and customize trading algorithms using our drag-and-drop interface or code editor.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
