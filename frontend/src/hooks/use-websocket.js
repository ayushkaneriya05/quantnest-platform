import { useState, useEffect, useRef, useCallback } from 'react';
import MockWebSocket, { shouldUseMockWebSocket } from '../services/mockWebSocket';

export function useWebSocket(url) {
    const [lastMessage, setLastMessage] = useState(null);
    const [isConnected, setIsConnected] = useState(false);
    const [connectionError, setConnectionError] = useState(null);
    const ws = useRef(null);
    const reconnectTimeout = useRef(null);
    const useMock = useRef(shouldUseMockWebSocket(url));

    const connect = useCallback(() => {
        if (ws.current && ws.current.readyState === WebSocket.OPEN) return;
        
        try {
            // Try real WebSocket first, fall back to mock if it fails
            const SocketClass = useMock.current ? MockWebSocket : WebSocket;
            const socket = new SocketClass(url);
            ws.current = socket;

            socket.onopen = () => {
                console.log(`${useMock.current ? 'Mock ' : ''}WebSocket connected to ${url}`);
                setIsConnected(true);
                setConnectionError(null);
                if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
            };

            socket.onmessage = (event) => {
                setLastMessage(event.data);
            };

            socket.onclose = (event) => {
                console.log(`${useMock.current ? 'Mock ' : ''}WebSocket disconnected`);
                setIsConnected(false);
                
                // If real WebSocket failed and we haven't tried mock yet, try mock
                if (!useMock.current && event.code !== 1000) {
                    console.warn('🔄 Real WebSocket failed, falling back to Mock WebSocket');
                    useMock.current = true;
                    reconnectTimeout.current = setTimeout(() => connect(), 1000);
                } else {
                    // Reconnect with exponential backoff
                    reconnectTimeout.current = setTimeout(() => connect(), 5000);
                }
            };

            socket.onerror = (error) => {
                console.error(`${useMock.current ? 'Mock ' : ''}WebSocket error:`, error);
                setConnectionError(error);
                
                // If real WebSocket fails, try mock WebSocket
                if (!useMock.current) {
                    console.warn('🔄 Real WebSocket error, falling back to Mock WebSocket');
                    useMock.current = true;
                    socket.close();
                }
            };
        } catch (error) {
            console.error('Failed to create WebSocket:', error);
            setConnectionError(error);
            
            // Fall back to mock WebSocket
            if (!useMock.current) {
                console.warn('🔄 WebSocket creation failed, using Mock WebSocket');
                useMock.current = true;
                reconnectTimeout.current = setTimeout(() => connect(), 1000);
            }
        }
    }, [url]);

    useEffect(() => {
        connect();
        return () => {
            if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
            if (ws.current) {
                ws.current.close();
            }
        };
    }, [connect]);

    const sendMessage = useCallback((data) => {
        if (ws.current?.readyState === WebSocket.OPEN) {
            try {
                ws.current.send(JSON.stringify(data));
            } catch (error) {
                console.error('Failed to send WebSocket message:', error);
                setConnectionError(error);
            }
        } else {
            console.warn('WebSocket not connected, cannot send message:', data);
        }
    }, []);

    return { 
        lastMessage, 
        isConnected, 
        sendMessage, 
        connectionError,
        isMockConnection: useMock.current
    };
}
