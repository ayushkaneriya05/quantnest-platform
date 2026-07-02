/**
 * Market Overview Dashboard - market status and key indices
 */
import React,  { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { Badge } from "@/shared/components/ui/badge";
import { 
  Activity, Clock, Globe
} from 'lucide-react';
import marketApi from '@/shared/services/marketApi';
import { useNotifications } from '@/shared/hooks/useNotifications';

export default function MarketOverview() {
  const [currentTime, setCurrentTime] = useState(new Date());
  const [indices, setIndices] = useState([]);
  const [events, setEvents] = useState([]);
  const { notify } = useNotifications();

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const load = async () => {
      try {
        const [indicesRes, eventsRes] = await Promise.all([
          marketApi.getLiveIndices(),
          marketApi.getEvents(),
        ]);
        setIndices(indicesRes.data || []);
        setEvents(eventsRes.data || []);
      } catch (error) {
        notify.error('Failed to load market overview');
      }
    };
    load();
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, []);

  const formatCurrency = (val) => {
    return new Intl.NumberFormat('en-IN', { 
      maximumFractionDigits: 2,
      minimumFractionDigits: 2
    }).format(val);
  };

  return (
    <div className="container-padding py-6 lg:py-8 space-y-6">
      {/* Indices */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {indices.map((index) => (
          <Card key={index.name} className="bg-gray-900/50 border-gray-800">
            <CardContent className="py-4">
              <p className="text-sm text-gray-400">{index.name}</p>
              <p className="text-xl font-bold text-white mt-1">
                {formatCurrency(index.price)}
              </p>
              <div className="flex items-center gap-1 mt-1 text-indigo-300">
                <Activity className="h-4 w-4" />
                <span className="text-sm font-medium">
                  Live
                </span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Events */}
      <div className="grid md:grid-cols-2 gap-6">
        <Card className="bg-gray-900/50 border-gray-800">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Clock className="h-5 w-5 text-green-400" />
              Upcoming Market Events
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {events.slice(0, 5).map((event) => (
              <div 
                key={event.id}
                className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg"
              >
                <div>
                  <p className="text-white font-medium">{event.title}</p>
                  <p className="text-sm text-gray-400">{event.event_date}</p>
                </div>
                <Badge className="bg-green-600">{event.event_type}</Badge>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="bg-gray-900/50 border-gray-800">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Globe className="h-5 w-5 text-red-400" />
              Market Clock
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="p-4 bg-gray-800/50 rounded-lg">
              <p className="text-3xl font-bold text-white">
                {currentTime.toLocaleTimeString("en-IN")}
              </p>
              <p className="text-sm text-gray-400 mt-1">
                {currentTime.toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "short" })}
              </p>
            </div>
            <div className="text-sm text-gray-400">
              Streaming uses cached/polled quotes from the market data layer.
            </div>
          </CardContent>
        </Card>
      </div>

    </div>
  );
}
