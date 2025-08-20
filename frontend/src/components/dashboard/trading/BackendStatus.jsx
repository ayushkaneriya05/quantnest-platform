import React, { useState, useEffect } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { 
  Server, 
  ServerOff, 
  RefreshCw, 
  AlertCircle,
  CheckCircle,
  Clock
} from 'lucide-react';
import api from '@/services/api';

export default function BackendStatus() {
  const [status, setStatus] = useState({ available: true, checking: false });
  const [lastChecked, setLastChecked] = useState(null);

  const checkBackendStatus = async () => {
    setStatus(prev => ({ ...prev, checking: true }));
    
    try {
      const isAvailable = await api.checkBackendHealth();
      setStatus({ available: isAvailable, checking: false });
      setLastChecked(new Date());
    } catch (error) {
      setStatus({ available: false, checking: false });
      setLastChecked(new Date());
    }
  };

  useEffect(() => {
    // Initial check
    checkBackendStatus();
    
    // Check every 30 seconds
    const interval = setInterval(checkBackendStatus, 30000);
    
    return () => clearInterval(interval);
  }, []);

  const getStatusConfig = () => {
    if (status.checking) {
      return {
        icon: RefreshCw,
        label: 'Checking...',
        variant: 'secondary',
        color: 'text-blue-400',
        bgColor: 'bg-blue-500/20',
        animate: 'animate-spin'
      };
    }
    
    if (status.available) {
      return {
        icon: Server,
        label: 'Backend Online',
        variant: 'default',
        color: 'text-emerald-400',
        bgColor: 'bg-emerald-500/20'
      };
    }
    
    return {
      icon: ServerOff,
      label: 'Demo Mode',
      variant: 'outline',
      color: 'text-yellow-400',
      bgColor: 'bg-yellow-500/20'
    };
  };

  const statusConfig = getStatusConfig();
  const StatusIcon = statusConfig.icon;

  return (
    <div className="flex items-center gap-2">
      <Badge 
        variant={statusConfig.variant} 
        className={`flex items-center gap-2 px-3 py-1 ${statusConfig.bgColor} border-current/30`}
      >
        <StatusIcon 
          className={`h-3 w-3 ${statusConfig.color} ${statusConfig.animate || ''}`} 
        />
        <span className="text-xs font-medium">{statusConfig.label}</span>
      </Badge>

      {!status.available && !status.checking && (
        <Button
          onClick={checkBackendStatus}
          size="sm"
          variant="outline"
          className="h-6 px-2 text-xs border-gray-700 text-gray-300 hover:bg-gray-800"
        >
          <RefreshCw className="h-3 w-3 mr-1" />
          Retry
        </Button>
      )}

      {/* Status tooltip */}
      <div className="group relative">
        <div className="h-4 w-4 rounded-full bg-gray-600 flex items-center justify-center cursor-help">
          <div className="h-1 w-1 bg-gray-400 rounded-full"></div>
        </div>
        <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-800 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-50">
          {status.available ? (
            <div>
              <div className="text-emerald-300">✓ Backend services active</div>
              <div className="text-gray-300">Real-time data & trading</div>
            </div>
          ) : (
            <div>
              <div className="text-yellow-300">⚠ Backend unavailable</div>
              <div className="text-gray-300">Using simulated data</div>
            </div>
          )}
          {lastChecked && (
            <div className="text-gray-400 text-xs mt-1">
              Last checked: {lastChecked.toLocaleTimeString()}
            </div>
          )}
          <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-t-gray-800"></div>
        </div>
      </div>
    </div>
  );
}
