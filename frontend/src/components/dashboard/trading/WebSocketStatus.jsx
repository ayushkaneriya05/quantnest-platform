import React from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { 
  Wifi, 
  WifiOff, 
  RefreshCw, 
  AlertCircle, 
  CheckCircle,
  Clock,
  Zap
} from 'lucide-react';
import { useWebSocketContext } from '@/contexts/websocket-context';

export default function WebSocketStatus() {
  const { 
    isConnected, 
    connectionStatus, 
    connect, 
    useMockData,
    subscriptions 
  } = useWebSocketContext();

  const getStatusConfig = () => {
    switch (connectionStatus) {
      case 'connected':
        return {
          icon: Wifi,
          label: 'Live Data',
          variant: 'default',
          color: 'text-emerald-400',
          bgColor: 'bg-emerald-500/20',
          description: 'Real-time market data active'
        };
      case 'connecting':
      case 'reconnecting':
        return {
          icon: RefreshCw,
          label: 'Connecting',
          variant: 'secondary',
          color: 'text-blue-400',
          bgColor: 'bg-blue-500/20',
          description: 'Establishing connection...',
          animate: 'animate-spin'
        };
      case 'mock':
        return {
          icon: Zap,
          label: 'Simulation',
          variant: 'outline',
          color: 'text-yellow-400',
          bgColor: 'bg-yellow-500/20',
          description: 'Using simulated market data'
        };
      case 'error':
      case 'failed':
        return {
          icon: AlertCircle,
          label: 'Error',
          variant: 'destructive',
          color: 'text-red-400',
          bgColor: 'bg-red-500/20',
          description: 'Connection failed'
        };
      case 'disconnected':
      default:
        return {
          icon: WifiOff,
          label: 'Offline',
          variant: 'secondary',
          color: 'text-gray-400',
          bgColor: 'bg-gray-500/20',
          description: 'No market data connection'
        };
    }
  };

  const statusConfig = getStatusConfig();
  const StatusIcon = statusConfig.icon;

  const handleReconnect = () => {
    connect();
  };

  return (
    <div className="flex items-center gap-3">
      {/* Status Badge */}
      <Badge 
        variant={statusConfig.variant} 
        className={`flex items-center gap-2 px-3 py-1 ${statusConfig.bgColor} border-current/30`}
      >
        <StatusIcon 
          className={`h-3 w-3 ${statusConfig.color} ${statusConfig.animate || ''}`} 
        />
        <span className="text-xs font-medium">{statusConfig.label}</span>
      </Badge>

      {/* Subscription Count */}
      {subscriptions.length > 0 && (
        <Badge variant="outline" className="text-xs border-gray-600 text-gray-400">
          {subscriptions.length} symbols
        </Badge>
      )}

      {/* Reconnect Button for Error States */}
      {(connectionStatus === 'error' || connectionStatus === 'failed' || connectionStatus === 'disconnected') && (
        <Button
          onClick={handleReconnect}
          size="sm"
          variant="outline"
          className="h-6 px-2 text-xs border-gray-700 text-gray-300 hover:bg-gray-800"
        >
          <RefreshCw className="h-3 w-3 mr-1" />
          Retry
        </Button>
      )}

      {/* Tooltip-like description on hover */}
      <div className="group relative">
        <div className="h-4 w-4 rounded-full bg-gray-600 flex items-center justify-center cursor-help">
          <div className="h-1 w-1 bg-gray-400 rounded-full"></div>
        </div>
        <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-800 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-50">
          {statusConfig.description}
          {useMockData && (
            <div className="text-yellow-300 mt-1">
              Market data simulated for demo
            </div>
          )}
          <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-t-gray-800"></div>
        </div>
      </div>
    </div>
  );
}
