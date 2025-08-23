import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Brain } from "lucide-react";
import React from "react";
export default function AIResearchAssistant() {
  return (
    <div className="container-padding py-6 lg:py-8">
      <Card className="bg-gray-900/50 border-gray-800/50 max-w-2xl mx-auto">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <Brain className="h-12 w-12 text-purple-400" />
          </div>
          <CardTitle className="text-slate-100">
            AI Research Assistant
          </CardTitle>
          <CardDescription className="text-slate-400">
            Your personal AI-powered trading research assistant
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-slate-300 text-center">
            Get personalized stock picks, market analysis, and trading insights
            powered by advanced AI.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
