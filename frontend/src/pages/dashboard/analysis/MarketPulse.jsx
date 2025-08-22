// frontend/src/components/MarketPulse.jsx
import React, { useEffect, useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Loader2, TrendingUp, TrendingDown } from "lucide-react";

const MarketPulse = () => {
  const [pulse, setPulse] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchPulse = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("http://localhost:8000/api/pulse/");
      if (!res.ok) throw new Error("Failed to fetch");
      const data = await res.json();
      setPulse(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPulse();
  }, []);

  return (
    <div className="p-4 grid gap-4">
      <Card className="shadow-md rounded-2xl">
        <CardHeader>
          <CardTitle className="text-xl font-semibold flex justify-between items-center">
            Daily Market Pulse
            <Button onClick={fetchPulse} disabled={loading}>
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                "Refresh"
              )}
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {error && <p className="text-red-500">{error}</p>}
          {pulse ? (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                {pulse.sentiment === "positive" ? (
                  <TrendingUp className="text-green-500" />
                ) : pulse.sentiment === "negative" ? (
                  <TrendingDown className="text-red-500" />
                ) : null}
                <p className="font-medium">Sentiment: {pulse.sentiment}</p>
              </div>

              <div>
                <h3 className="font-semibold mb-1">Summary</h3>
                <p className="text-gray-700 text-sm whitespace-pre-line">
                  {pulse.summary}
                </p>
              </div>

              <div>
                <h3 className="font-semibold mb-1">Top Headlines</h3>
                <ul className="list-disc pl-5 space-y-1">
                  {pulse.headlines.map((h, idx) => (
                    <li key={idx} className="text-sm">
                      {h}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ) : (
            !loading && <p className="text-gray-500">No data available.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default MarketPulse;
