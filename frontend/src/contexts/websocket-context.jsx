import React, { createContext, useContext, useEffect, useRef, useState, useCallback } from 'react';
import toast from 'react-hot-toast';

const WebSocketContext = createContext();

export const useWebSocketContext = () => {
  const context = useContext(WebSocketContext);
  if (!context) {
    // Provide a fallback object instead of throwing an error
    console.warn('useWebSocketContext must be used within a WebSocketProvider. Using fallback values.');
    return {
      isConnected: false,
      connectionStatus: 'disconnected',
      lastMessage: null,
      tickData: new Map(),
      orderUpdates: [],
      positionUpdates: [],
      connect: () => console.warn('WebSocket not available'),
      disconnect: () => console.warn('WebSocket not available'),
      sendMessage: () => false,
      subscribe: () => () => {},
      unsubscribe: () => {},
      getLatestPrice: () => null,
      getTickData: () => null,
      subscriptions: []
    };
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
  const [useMockData, setUseMockData] = useState(false);
  
  const ws = useRef(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 3; // Reduced attempts
  const reconnectInterval = useRef(null);
  const subscriptionCallbacks = useRef(new Map());
  const mockDataInterval = useRef(null);

  // Mock data generator for when WebSocket is not available
  const generateMockTickData = useCallback((symbol) => {
    const basePrices = {
      'RELIANCE': 2450.0,
      'TCS': 3200.0,
      'INFY': 1450.0,
      'HDFCBANK': 1650.0,
      'ICICIBANK': 920.0,
      'WIPRO': 410.0,
      'LT': 3400.0,
      'BHARTIARTL': 1180.0,
      'SBIN': 780.0,
      'ITC': 460.0,
    };

    const basePrice = basePrices[symbol] || 2000;
    const variation = (Math.random() - 0.5) * 0.02; // ±1% variation
    const currentPrice = basePrice * (1 + variation);

    return {
      symbol,
      ltp: currentPrice,
      type: 'tick',
      timestamp: Date.now(),
      volume: Math.floor(Math.random() * 100000) + 50000,
      change: currentPrice - basePrice,
      change_percent: (variation * 100).toFixed(2)
    };
  }, []);

  const startMockDataGeneration = useCallback(() => {
    if (mockDataInterval.current) return;

    console.log('Starting mock data generation for trading simulation');
    
    mockDataInterval.current = setInterval(() => {
      subscriptions.forEach(symbol => {
        const mockData = generateMockTickData(symbol);
        handleTickData(mockData);
        
        // Call subscription callbacks
        if (subscriptionCallbacks.current.has(symbol)) {
          subscriptionCallbacks.current.get(symbol).forEach(callback => {
            try {
              callback(mockData);
            } catch (error) {
              console.error('Error in mock data callback:', error);
            }
          });
        }
      });
    }, 2000); // Update every 2 seconds
  }, [subscriptions, generateMockTickData]);

  const stopMockDataGeneration = useCallback(() => {
    if (mockDataInterval.current) {
      clearInterval(mockDataInterval.current);
      mockDataInterval.current = null;
    }
  }, []);

  const getWebSocketUrl = () => {
    // Try to determine the correct WebSocket URL based on environment
    if (typeof window !== 'undefined') {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.hostname;
      
      // For development, try localhost first
      if (host === 'localhost' || host === '127.0.0.1') {
        return 'ws://localhost:8000/ws/marketdata/';
      }
      
      // For production or other environments
      const port = window.location.port ? `:${window.location.port}` : '';
      return `${protocol}//${host}${port}/ws/marketdata/`;
    }
    
    // Fallback
    return 'ws://localhost:8000/ws/marketdata/';
  };

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return;

    try {
      setConnectionStatus('connecting');
      
      // Check if WebSocket is available in the environment
      if (typeof WebSocket === 'undefined') {
        console.warn('WebSocket not available in this environment, using mock data');
        setConnectionStatus('mock');
        setUseMockData(true);
        startMockDataGeneration();
        return;
      }

      const wsUrl = getWebSocketUrl();
      console.log('Attempting to connect to WebSocket:', wsUrl);
      
      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        console.log('WebSocket connected successfully');
        setIsConnected(true);
        setConnectionStatus('connected');
        setUseMockData(false);
        reconnectAttempts.current = 0;
        stopMockDataGeneration();
        
        // Resubscribe to all previous subscriptions
        subscriptions.forEach(symbol => {
          ws.current?.send(JSON.stringify({
            type: 'subscribe',
            instrument: symbol
          }));
        });
        
        toast.success('Live market data connected', { duration: 3000 });
      };

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setLastMessage(data);
          
          // Route different types of messages
          if (data.type === 'tick' || data.symbol) {
            handleTickData(data);
          } else if (data.type === 'order_update') {
            handleOrderUpdate(data);
          } else if (data.type === 'position_update') {
            handlePositionUpdate(data);
          }
          
          // Call specific callbacks for subscriptions
          if (data.symbol && subscriptionCallbacks.current.has(data.symbol)) {
            subscriptionCallbacks.current.get(data.symbol).forEach(callback => {
              try {
                callback(data);
              } catch (callbackError) {
                console.error('Error in subscription callback:', callbackError);
              }
            });
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      ws.current.onclose = (event) => {
        console.log('WebSocket disconnected. Code:', event.code, 'Reason:', event.reason || 'Unknown');
        setIsConnected(false);
        setConnectionStatus('disconnected');
        
        // Handle different close codes
        if (event.code === 1006) {
          console.log('WebSocket connection failed - likely server not running');
        } else if (event.code === 1011) {
          console.log('WebSocket server error');
        } else if (event.code === 1001) {
          console.log('WebSocket endpoint unavailable');
        }
        
        // Only attempt reconnection for certain close codes and within retry limit
        if (event.code !== 1000 && reconnectAttempts.current < maxReconnectAttempts) {
          attemptReconnect();
        } else if (reconnectAttempts.current >= maxReconnectAttempts) {
          console.log('Max reconnection attempts reached, switching to mock data');
          setConnectionStatus('mock');
          setUseMockData(true);
          startMockDataGeneration();
          toast.error('Live data unavailable, using simulation mode', { duration: 4000 });
        }
      };

      ws.current.onerror = (error) => {
        console.error('WebSocket error details:', {
          error: error,
          readyState: ws.current?.readyState,
          url: wsUrl,
          timestamp: new Date().toISOString()
        });
        
        setConnectionStatus('error');
        
        // Only show error toast on first attempt to avoid spam
        if (reconnectAttempts.current === 0) {
          toast.error('Market data connection failed, will retry...', { duration: 3000 });
        }
      };

    } catch (error) {
      console.error('WebSocket connection setup error:', error);
      setConnectionStatus('error');
      
      // Fall back to mock data
      console.log('Falling back to mock data generation');
      setUseMockData(true);
      startMockDataGeneration();
      toast.error('Using simulated market data', { duration: 3000 });
    }
  }, [subscriptions, startMockDataGeneration, stopMockDataGeneration]);

  const attemptReconnect = useCallback(() => {
    if (reconnectAttempts.current >= maxReconnectAttempts) return;
    
    reconnectAttempts.current++;
    setConnectionStatus('reconnecting');
    
    const delay = Math.min(2000 * reconnectAttempts.current, 10000); // 2s, 4s, 6s max
    
    console.log(`Reconnection attempt ${reconnectAttempts.current}/${maxReconnectAttempts} in ${delay}ms`);
    
    reconnectInterval.current = setTimeout(() => {
      connect();
    }, delay);
  }, [connect]);

  const disconnect = useCallback(() => {
    if (reconnectInterval.current) {
      clearTimeout(reconnectInterval.current);
    }
    
    stopMockDataGeneration();
    
    if (ws.current) {
      ws.current.close(1000, 'Manual disconnect');
      ws.current = null;
    }
    
    setIsConnected(false);
    setConnectionStatus('disconnected');
    setUseMockData(false);
  }, [stopMockDataGeneration]);

  const sendMessage = useCallback((message) => {
    if (useMockData) {
      console.log('Mock mode - simulating message send:', message);
      return true;
    }
    
    if (ws.current?.readyState === WebSocket.OPEN) {
      try {
        ws.current.send(JSON.stringify(message));
        return true;
      } catch (error) {
        console.error('Error sending WebSocket message:', error);
        return false;
      }
    } else {
      console.warn('WebSocket not connected - message not sent:', message);
      return false;
    }
  }, [useMockData]);

  const subscribe = useCallback((symbol, callback) => {
    if (!symbol) return;

    console.log('Subscribing to symbol:', symbol);

    // Add to subscriptions set
    setSubscriptions(prev => new Set([...prev, symbol]));
    
    // Add callback for this symbol
    if (callback) {
      if (!subscriptionCallbacks.current.has(symbol)) {
        subscriptionCallbacks.current.set(symbol, new Set());
      }
      subscriptionCallbacks.current.get(symbol).add(callback);
    }
    
    // Send subscription message if connected or generate mock data
    if (useMockData) {
      // In mock mode, immediately generate some data
      setTimeout(() => {
        const mockData = generateMockTickData(symbol);
        handleTickData(mockData);
        if (callback) {
          try {
            callback(mockData);
          } catch (error) {
            console.error('Error in subscription callback:', error);
          }
        }
      }, 100);
    } else if (ws.current?.readyState === WebSocket.OPEN) {
      sendMessage({
        type: 'subscribe',
        instrument: symbol
      });
    }
    
    return () => unsubscribe(symbol, callback);
  }, [sendMessage, useMockData, generateMockTickData]);

  const unsubscribe = useCallback((symbol, callback) => {
    if (!symbol) return;

    console.log('Unsubscribing from symbol:', symbol);

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
      if (!useMockData && ws.current?.readyState === WebSocket.OPEN) {
        sendMessage({
          type: 'unsubscribe',
          instrument: symbol
        });
      }
    }
  }, [sendMessage, useMockData]);

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

  // Auto-connect on mount, but only if in browser environment
  useEffect(() => {
    if (typeof window !== 'undefined') {
      connect();
    }
    
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
      stopMockDataGeneration();
    };
  }, [stopMockDataGeneration]);

  const value = {
    // Connection state
    isConnected: isConnected || useMockData,
    connectionStatus: useMockData ? 'mock' : connectionStatus,
    
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
    subscriptions: Array.from(subscriptions),
    
    // Mock mode indicator
    useMockData
  };

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
};
