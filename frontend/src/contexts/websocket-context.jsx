import React, { createContext, useContext, useEffect, useRef, useState, useCallback } from 'react';
import toast from 'react-hot-toast';

const WebSocketContext = createContext();

export const useWebSocketContext = () => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocketContext must be used within a WebSocketProvider');
  }
  return context;
};

export const WebSocketProvider = ({ children }) => {
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [lastMessage, setLastMessage] = useState(null);
  const [subscriptions, setSubscriptions] = useState(new Set());
  const [tickData, setTickData] = useState(new Map());
  const [orderUpdates, setOrderUpdates] = useState([]);
  const [positionUpdates, setPositionUpdates] = useState([]);
  
  const ws = useRef(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;
  const reconnectInterval = useRef(null);
  const subscriptionCallbacks = useRef(new Map());

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return;

    try {
      setConnectionStatus('connecting');
      ws.current = new WebSocket('ws://localhost:8000/ws/marketdata/');

      ws.current.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        setConnectionStatus('connected');
        reconnectAttempts.current = 0;
        
        // Resubscribe to all previous subscriptions
        subscriptions.forEach(symbol => {
          ws.current?.send(JSON.stringify({
            action: 'subscribe',
            symbol: symbol
          }));
        });
        
        toast.success('Market data connected');
      };

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setLastMessage(data);
          
          // Route different types of messages
          if (data.type === 'tick') {
            handleTickData(data);
          } else if (data.type === 'order_update') {
            handleOrderUpdate(data);
          } else if (data.type === 'position_update') {
            handlePositionUpdate(data);
          }
          
          // Call specific callbacks for subscriptions
          if (data.symbol && subscriptionCallbacks.current.has(data.symbol)) {
            subscriptionCallbacks.current.get(data.symbol).forEach(callback => {
              callback(data);
            });
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      ws.current.onclose = (event) => {
        console.log('WebSocket disconnected', event.code, event.reason);
        setIsConnected(false);
        setConnectionStatus('disconnected');
        
        // Only attempt reconnection if it wasn't a clean close
        if (event.code !== 1000 && reconnectAttempts.current < maxReconnectAttempts) {
          attemptReconnect();
        } else if (reconnectAttempts.current >= maxReconnectAttempts) {
          toast.error('Connection failed after multiple attempts');
          setConnectionStatus('failed');
        }
      };

      ws.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnectionStatus('error');
        toast.error('Market data connection error');
      };

    } catch (error) {
      console.error('WebSocket connection error:', error);
      setConnectionStatus('error');
    }
  }, [subscriptions]);

  const attemptReconnect = useCallback(() => {
    if (reconnectAttempts.current >= maxReconnectAttempts) return;
    
    reconnectAttempts.current++;
    setConnectionStatus('reconnecting');
    
    const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
    
    reconnectInterval.current = setTimeout(() => {
      console.log(`Reconnection attempt ${reconnectAttempts.current}/${maxReconnectAttempts}`);
      connect();
    }, delay);
  }, [connect]);

  const disconnect = useCallback(() => {
    if (reconnectInterval.current) {
      clearTimeout(reconnectInterval.current);
    }
    
    if (ws.current) {
      ws.current.close(1000, 'Manual disconnect');
      ws.current = null;
    }
    
    setIsConnected(false);
    setConnectionStatus('disconnected');
  }, []);

  const sendMessage = useCallback((message) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
      return true;
    } else {
      console.warn('WebSocket not connected');
      return false;
    }
  }, []);

  const subscribe = useCallback((symbol, callback) => {
    if (!symbol) return;

    // Add to subscriptions set
    setSubscriptions(prev => new Set([...prev, symbol]));
    
    // Add callback for this symbol
    if (callback) {
      if (!subscriptionCallbacks.current.has(symbol)) {
        subscriptionCallbacks.current.set(symbol, new Set());
      }
      subscriptionCallbacks.current.get(symbol).add(callback);
    }
    
    // Send subscription message if connected
    if (ws.current?.readyState === WebSocket.OPEN) {
      sendMessage({
        action: 'subscribe',
        symbol: symbol
      });
    }
    
    return () => unsubscribe(symbol, callback);
  }, [sendMessage]);

  const unsubscribe = useCallback((symbol, callback) => {
    if (!symbol) return;

    // Remove callback
    if (callback && subscriptionCallbacks.current.has(symbol)) {
      subscriptionCallbacks.current.get(symbol).delete(callback);
      if (subscriptionCallbacks.current.get(symbol).size === 0) {
        subscriptionCallbacks.current.delete(symbol);
      }
    }
    
    // Remove from subscriptions if no more callbacks
    if (!subscriptionCallbacks.current.has(symbol)) {
      setSubscriptions(prev => {
        const newSet = new Set(prev);
        newSet.delete(symbol);
        return newSet;
      });
      
      // Send unsubscribe message if connected
      if (ws.current?.readyState === WebSocket.OPEN) {
        sendMessage({
          action: 'unsubscribe',
          symbol: symbol
        });
      }
    }
  }, [sendMessage]);

  const handleTickData = useCallback((data) => {
    if (data.symbol) {
      setTickData(prev => new Map(prev.set(data.symbol, {
        ...data,
        timestamp: Date.now()
      })));
    }
  }, []);

  const handleOrderUpdate = useCallback((data) => {
    setOrderUpdates(prev => [data, ...prev.slice(0, 99)]); // Keep last 100 updates
  }, []);

  const handlePositionUpdate = useCallback((data) => {
    setPositionUpdates(prev => [data, ...prev.slice(0, 99)]); // Keep last 100 updates
  }, []);

  const getLatestPrice = useCallback((symbol) => {
    return tickData.get(symbol)?.ltp || null;
  }, [tickData]);

  const getTickData = useCallback((symbol) => {
    return tickData.get(symbol) || null;
  }, [tickData]);

  // Auto-connect on mount
  useEffect(() => {
    connect();
    
    return () => {
      disconnect();
    };
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (reconnectInterval.current) {
        clearTimeout(reconnectInterval.current);
      }
    };
  }, []);

  const value = {
    // Connection state
    isConnected,
    connectionStatus,
    
    // Data
    lastMessage,
    tickData,
    orderUpdates,
    positionUpdates,
    
    // Methods
    connect,
    disconnect,
    sendMessage,
    subscribe,
    unsubscribe,
    getLatestPrice,
    getTickData,
    
    // Subscription info
    subscriptions: Array.from(subscriptions)
  };

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
};
