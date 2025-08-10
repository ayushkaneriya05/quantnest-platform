import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Search as SearchIcon } from 'lucide-react'

export default function Search() {
  return (
    <div className="container-padding py-6 lg:py-8">
      <Card className="bg-gray-900/50 border-gray-800/50 max-w-2xl mx-auto">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <SearchIcon className="h-12 w-12 text-indigo-400" />
          </div>
          <CardTitle className="text-slate-100">Search</CardTitle>
          <CardDescription className="text-slate-400">
            Search functionality coming soon
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-slate-300 text-center">
            This page will contain advanced search functionality for stocks, strategies, and market data.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
