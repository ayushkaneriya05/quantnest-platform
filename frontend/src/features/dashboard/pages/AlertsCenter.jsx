/**
 * Alerts Center - notifications and trading alerts
 */
import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import { Badge } from "@/shared/components/ui/badge";
import { Input } from "@/shared/components/ui/input";
import { 
  Bell, AlertTriangle, CheckCircle, Info, 
  Clock, Trash2, Search, Filter, Settings
} from 'lucide-react';

// Mock data
const MOCK_ALERTS = [
  { 
    id: 1, 
    type: 'trade', 
    severity: 'success',
    title: 'Order Executed', 
    message: 'RELIANCE bought at ₹2,480.00 (50 qty)',
    strategy: 'EMA Crossover',
    time: '10:32 AM',
    read: false 
  },
  { 
    id: 2, 
    type: 'risk', 
    severity: 'warning',
    title: 'Position Size Warning', 
    message: 'Position in TATASTEEL exceeds 5% of portfolio',
    strategy: 'RSI Divergence',
    time: '10:15 AM',
    read: false 
  },
  { 
    id: 3, 
    type: 'system', 
    severity: 'error',
    title: 'Stop Loss Hit', 
    message: 'ICICIBANK position closed at ₹976.50 (SL triggered)',
    strategy: 'VWAP Scalper',
    time: '09:58 AM',
    read: true 
  },
  { 
    id: 4, 
    type: 'info', 
    severity: 'info',
    title: 'Strategy Started', 
    message: 'EMA Crossover strategy is now active',
    strategy: 'EMA Crossover',
    time: '09:15 AM',
    read: true 
  },
  { 
    id: 5, 
    type: 'trade', 
    severity: 'success',
    title: 'Target Hit', 
    message: 'HDFC target reached! Profit: ₹3,200',
    strategy: 'Momentum Play',
    time: 'Yesterday',
    read: true 
  },
];

const SEVERITY_STYLES = {
  success: { bg: 'bg-green-900/20', border: 'border-green-800/50', icon: CheckCircle, color: 'text-green-400' },
  warning: { bg: 'bg-yellow-900/20', border: 'border-yellow-800/50', icon: AlertTriangle, color: 'text-yellow-400' },
  error: { bg: 'bg-red-900/20', border: 'border-red-800/50', icon: AlertTriangle, color: 'text-red-400' },
  info: { bg: 'bg-blue-900/20', border: 'border-blue-800/50', icon: Info, color: 'text-blue-400' },
};

export default function AlertsCenter() {
  const [alerts, setAlerts] = useState(MOCK_ALERTS);
  const [filter, setFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

  const unreadCount = alerts.filter(a => !a.read).length;

  const markAsRead = (id) => {
    setAlerts(alerts.map(a => a.id === id ? { ...a, read: true } : a));
  };

  const markAllRead = () => {
    setAlerts(alerts.map(a => ({ ...a, read: true })));
  };

  const deleteAlert = (id) => {
    setAlerts(alerts.filter(a => a.id !== id));
  };

  const clearAll = () => {
    if (confirm('Clear all alerts?')) {
      setAlerts([]);
    }
  };

  const filteredAlerts = alerts.filter(a => {
    if (filter === 'unread' && a.read) return false;
    if (filter !== 'all' && filter !== 'unread' && a.type !== filter) return false;
    if (searchQuery && !a.title.toLowerCase().includes(searchQuery.toLowerCase()) && 
        !a.message.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="container-padding py-6 lg:py-8 space-y-6">
      {/* Filters */}
      <div className="flex gap-4 items-center">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search alerts..."
            className="pl-9 bg-gray-800 border-gray-700 text-white"
          />
        </div>
        <div className="flex gap-2">
          {['all', 'unread', 'trade', 'risk', 'system'].map((f) => (
            <Button
              key={f}
              variant={filter === f ? 'default' : 'outline'}
              size="sm"
              onClick={() => setFilter(f)}
              className={filter === f ? 'bg-indigo-600' : 'border-gray-700'}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </Button>
          ))}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'Total', count: alerts.length, color: 'text-white' },
          { label: 'Trades', count: alerts.filter(a => a.type === 'trade').length, color: 'text-green-400' },
          { label: 'Warnings', count: alerts.filter(a => a.severity === 'warning').length, color: 'text-yellow-400' },
          { label: 'Errors', count: alerts.filter(a => a.severity === 'error').length, color: 'text-red-400' },
        ].map((stat) => (
          <Card key={stat.label} className="bg-gray-900/50 border-gray-800">
            <CardContent className="py-3 text-center">
              <p className={`text-2xl font-bold ${stat.color}`}>{stat.count}</p>
              <p className="text-xs text-gray-400">{stat.label}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Alerts List */}
      {filteredAlerts.length === 0 ? (
        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-12 text-center">
            <Bell className="h-12 w-12 text-gray-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-300">No alerts</h3>
            <p className="text-gray-500 mt-1">
              {filter !== 'all' ? 'Try a different filter' : 'You\'re all caught up!'}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {filteredAlerts.map((alert) => {
            const style = SEVERITY_STYLES[alert.severity];
            const Icon = style.icon;
            return (
              <Card 
                key={alert.id}
                className={`${style.bg} border ${style.border} ${!alert.read ? 'ring-1 ring-indigo-500/50' : ''}`}
                onClick={() => markAsRead(alert.id)}
              >
                <CardContent className="py-4">
                  <div className="flex items-start gap-4">
                    <div className={`p-2 rounded-lg ${style.bg}`}>
                      <Icon className={`h-5 w-5 ${style.color}`} />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h4 className="text-white font-medium">{alert.title}</h4>
                        {!alert.read && (
                          <Badge className="bg-indigo-600 text-xs">New</Badge>
                        )}
                      </div>
                      <p className="text-sm text-gray-400 mt-1">{alert.message}</p>
                      <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
                        <span>{alert.strategy}</span>
                        <span>•</span>
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {alert.time}
                        </span>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteAlert(alert.id);
                      }}
                      className="text-gray-500 hover:text-red-400"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
