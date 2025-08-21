import React, { createContext, useContext, useEffect, useRef, useState, useCallback } from 'react';
import { useSelector } from 'react-redux';
import { toast } from 'react-hot-toast';

const WebSocketContext = createContext(null);

// WebSocket connection states
const WS_STATES = {
  CONNECTING: 'CONNECTING',
  CONNECTED: 'CONNECTED',
  DISCONNECTED: 'DISCONNECTED',
  ERROR: 'ERROR'
};

export const WebSocketProvider = ({ children }) => {
  const [connectionState, setConnectionState] = useState(WS_STATES.DISCONNECTED);
  const [subscriptions, setSubscriptions] = useState(new Set());
  const [marketData, setMarketData] = useState(new Map());
  const [lastHeartbeat, setLastHeartbeat] = useState(null);
  
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const heartbeatTimeoutRef = useRef(null);
  const subscriptionQueue = useRef([]);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;
  const baseReconnectDelay = 1000;
  
  const { token, isAuthenticated } = useSelector(state => state.auth);

  // Event listeners for market data updates
  const marketDataListeners = useRef(new Map());
  const orderUpdateListeners = useRef(new Map());
  const portfolioUpdateListeners = useRef(new Map());

  const getWebSocketUrl = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = import.meta.env.VITE_WS_HOST || window.location.host;
    return `${protocol}//${host}/ws/marketdata/`;
  }, []);

  const connect = useCallback(() => {
    if (!isAuthenticated || !token) {
      console.log('Cannot connect WebSocket: User not authenticated');
      return;
    }

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected');
      return;
    }

    try {
      setConnectionState(WS_STATES.CONNECTING);
      const wsUrl = getWebSocketUrl();
      
      console.log('Connecting to WebSocket:', wsUrl);
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        console.log('WebSocket connected successfully');
        setConnectionState(WS_STATES.CONNECTED);
        reconnectAttempts.current = 0;
        
        // Process queued subscriptions
        if (subscriptionQueue.current.length > 0) {
          subscriptionQueue.current.forEach(instrument => {
            subscribeToInstrument(instrument, false);
          });
          subscriptionQueue.current = [];
        }
        
        // Start heartbeat monitoring
        scheduleHeartbeatCheck();
      };

      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleWebSocketMessage(data);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      wsRef.current.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
        setConnectionState(WS_STATES.DISCONNECTED);
        clearTimeout(heartbeatTimeoutRef.current);
        
        // Attempt reconnection if not intentionally closed
        if (event.code !== 1000 && isAuthenticated) {
          scheduleReconnect();
        }
      };

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnectionState(WS_STATES.ERROR);
        toast.error('Connection error. Attempting to reconnect...');
      };

    } catch (error) {
      console.error('Error creating WebSocket connection:', error);
      setConnectionState(WS_STATES.ERROR);
      scheduleReconnect();
    }
  }, [isAuthenticated, token, getWebSocketUrl]);

  const disconnect = useCallback(() => {
    clearTimeout(reconnectTimeoutRef.current);
    clearTimeout(heartbeatTimeoutRef.current);
    
    if (wsRef.current) {
      wsRef.current.close(1000, 'User disconnect');
      wsRef.current = null;
    }
    
    setConnectionState(WS_STATES.DISCONNECTED);
    setSubscriptions(new Set());
    setMarketData(new Map());
    reconnectAttempts.current = 0;
  }, []);

  const scheduleReconnect = useCallback(() => {
    if (reconnectAttempts.current >= maxReconnectAttempts) {
      console.log('Max reconnection attempts reached');
      toast.error('Connection lost. Please refresh the page.');
      return;
    }

    const delay = baseReconnectDelay * Math.pow(2, reconnectAttempts.current);
    console.log(`Scheduling reconnect in ${delay}ms (attempt ${reconnectAttempts.current + 1})`);
    
    reconnectTimeoutRef.current = setTimeout(() => {
      reconnectAttempts.current++;
      connect();
    }, delay);
  }, [connect]);

  const scheduleHeartbeatCheck = useCallback(() => {
    heartbeatTimeoutRef.current = setTimeout(() => {
      if (connectionState === WS_STATES.CONNECTED) {
        sendMessage({ type: 'ping' });
        scheduleHeartbeatCheck();
      }
    }, 35000); // Check every 35 seconds (server sends every 30s)
  }, [connectionState]);

  const sendMessage = useCallback((message) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
      return true;
    }
    return false;
  }, []);

  const handleWebSocketMessage = useCallback((data) => {
    const { type } = data;

    switch (type) {
      case 'connection_status':
        if (data.status === 'connected') {
          console.log('WebSocket connection confirmed');
        }
        break;

      case 'heartbeat':
      case 'pong':
        setLastHeartbeat(new Date().toISOString());
        break;

      case 'market_data':
      case 'initial_price':
      case 'live_price':
        handleMarketDataUpdate(data);
        break;

      case 'order_update':
        handleOrderUpdate(data);
        break;

      case 'portfolio_update':
        handlePortfolioUpdate(data);
        break;

      case 'subscription_status':
        handleSubscriptionStatus(data);
        break;

      case 'error':
        console.error('WebSocket error message:', data.message);
        toast.error(data.message);
        break;

      default:
        console.log('Unknown WebSocket message type:', type);
    }
  }, []);

  const handleMarketDataUpdate = useCallback((data) => {
    const { instrument, data: priceData } = data;
    
    if (instrument && priceData) {
      setMarketData(prev => {
        const newData = new Map(prev);
        newData.set(instrument, {
          ...priceData,
          lastUpdate: new Date().toISOString()
        });
        return newData;
      });

      // Notify listeners
      const listeners = marketDataListeners.current.get(instrument) || [];
      listeners.forEach(callback => {
        try {
          callback(priceData);
        } catch (error) {
          console.error('Error in market data listener:', error);
        }
      });
    }
  }, []);

  const handleOrderUpdate = useCallback((data) => {
    const listeners = orderUpdateListeners.current.get('global') || [];
    listeners.forEach(callback => {
      try {
        callback(data.data);
      } catch (error) {
        console.error('Error in order update listener:', error);
      }
    });
  }, []);

  const handlePortfolioUpdate = useCallback((data) => {
    const listeners = portfolioUpdateListeners.current.get('global') || [];
    listeners.forEach(callback => {
      try {
        callback(data.data);
      } catch (error) {
        console.error('Error in portfolio update listener:', error);
      }
    });
  }, []);

  const handleSubscriptionStatus = useCallback((data) => {
    const { status, instrument } = data;
    
    if (status === 'subscribed') {
      setSubscriptions(prev => new Set(prev).add(instrument));
    } else if (status === 'unsubscribed') {
      setSubscriptions(prev => {
        const newSet = new Set(prev);
        newSet.delete(instrument);
        return newSet;
      });
    }
  }, []);

  const subscribeToInstrument = useCallback((instrument, queue = true) => {
    if (!instrument) return false;

    if (connectionState !== WS_STATES.CONNECTED) {
      if (queue) {
        subscriptionQueue.current.push(instrument);
      }
      return false;
    }

    return sendMessage({
      type: 'subscribe',
      instrument: instrument
    });
  }, [connectionState, sendMessage]);

  const unsubscribeFromInstrument = useCallback((instrument) => {
    if (!instrument) return false;

    // Remove from queue if present
    subscriptionQueue.current = subscriptionQueue.current.filter(i => i !== instrument);

    if (connectionState === WS_STATES.CONNECTED) {
      return sendMessage({
        type: 'unsubscribe',
        instrument: instrument
      });
    }

    // Remove from local state even if not connected
    setSubscriptions(prev => {
      const newSet = new Set(prev);
      newSet.delete(instrument);
      return newSet;
    });

    return true;
  }, [connectionState, sendMessage]);

  const getLivePrice = useCallback((instrument) => {
    if (!instrument) return false;

    return sendMessage({
      type: 'get_live_price',
      instrument: instrument
    });
  }, [sendMessage]);

  // Listener management functions
  const addMarketDataListener = useCallback((instrument, callback) => {
    if (!marketDataListeners.current.has(instrument)) {
      marketDataListeners.current.set(instrument, []);
    }
    marketDataListeners.current.get(instrument).push(callback);
    
    return () => {
      const listeners = marketDataListeners.current.get(instrument) || [];
      const index = listeners.indexOf(callback);
      if (index > -1) {
        listeners.splice(index, 1);
      }
    };
  }, []);

  const addOrderUpdateListener = useCallback((callback) => {
    if (!orderUpdateListeners.current.has('global')) {
      orderUpdateListeners.current.set('global', []);
    }
    orderUpdateListeners.current.get('global').push(callback);
    
    return () => {
      const listeners = orderUpdateListeners.current.get('global') || [];
      const index = listeners.indexOf(callback);
      if (index > -1) {
        listeners.splice(index, 1);
      }
    };
  }, []);

  const addPortfolioUpdateListener = useCallback((callback) => {
    if (!portfolioUpdateListeners.current.has('global')) {
      portfolioUpdateListeners.current.set('global', []);
    }
    portfolioUpdateListeners.current.get('global').push(callback);
    
    return () => {
      const listeners = portfolioUpdateListeners.current.get('global') || [];
      const index = listeners.indexOf(callback);
      if (index > -1) {
        listeners.splice(index, 1);
      }
    };
  }, []);

  // Auto-connect when authenticated
  useEffect(() => {
    if (isAuthenticated && token) {
      connect();
    } else {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [isAuthenticated, token, connect, disconnect]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      clearTimeout(reconnectTimeoutRef.current);
      clearTimeout(heartbeatTimeoutRef.current);
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const value = {
    connectionState,
    subscriptions,
    marketData,
    lastHeartbeat,
    connect,
    disconnect,
    subscribeToInstrument,
    unsubscribeFromInstrument,
    getLivePrice,
    addMarketDataListener,
    addOrderUpdateListener,
    addPortfolioUpdateListener,
    isConnected: connectionState === WS_STATES.CONNECTED,
    isConnecting: connectionState === WS_STATES.CONNECTING
  };

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocket = () => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};

export { WS_STATES };
