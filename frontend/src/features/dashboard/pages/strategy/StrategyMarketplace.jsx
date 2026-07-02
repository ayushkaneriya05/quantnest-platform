import { Link } from "react-router-dom";
import { ArrowRight, Store, TrendingUp } from "lucide-react";

import { Button } from "@/shared/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";

export default function StrategyMarketplace() {
  return (
    <div className="container-padding space-y-6 py-6 lg:py-8">
      <Card className="border-gray-800 bg-gray-900/60">
        <CardHeader>
          <div className="flex items-center gap-3">
            <Store className="h-8 w-8 text-cyan-300" />
            <div>
              <CardTitle className="text-white">Strategy Marketplace Hub</CardTitle>
              <p className="mt-1 text-sm text-gray-400">
                Publish your own strategies or explore the marketplace from one place.
              </p>
            </div>
          </div>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div className="rounded-2xl border border-gray-800 bg-black/20 p-5">
            <p className="text-lg font-semibold text-white">Explore Marketplace</p>
            <p className="mt-2 text-sm text-gray-400">
              Review listing performance, pricing, reviews, and subscribe to strategies.
            </p>
            <Button asChild className="mt-4 bg-cyan-600 hover:bg-cyan-500">
              <Link to="/dashboard/marketplace">
                <ArrowRight className="mr-2 h-4 w-4" />
                Open Marketplace
              </Link>
            </Button>
          </div>
          <div className="rounded-2xl border border-gray-800 bg-black/20 p-5">
            <p className="text-lg font-semibold text-white">Creator Dashboard</p>
            <p className="mt-2 text-sm text-gray-400">
              Publish owned strategies, manage pricing, and track subscriber earnings.
            </p>
            <Button asChild variant="outline" className="mt-4 border-gray-700 text-gray-100">
              <Link to="/dashboard/marketplace/creator">
                <TrendingUp className="mr-2 h-4 w-4" />
                Manage Creator Flow
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
