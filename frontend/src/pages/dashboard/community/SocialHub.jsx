import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Users } from 'lucide-react'

export default function SocialHub() {
  return (
    <div className="container-padding py-6 lg:py-8">
      <Card className="bg-gray-900/50 border-gray-800/50 max-w-2xl mx-auto">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <Users className="h-12 w-12 text-amber-400" />
          </div>
          <CardTitle className="text-slate-100">Social Hub</CardTitle>
          <CardDescription className="text-slate-400">
            Connect with the trading community
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-slate-300 text-center">
            Share insights, discuss strategies, and learn from other professional traders in our community.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
