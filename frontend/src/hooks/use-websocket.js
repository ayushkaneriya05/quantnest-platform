import { useState, useEffect, useRef, useCallback } from 'react';

export function useWebSocket(url) {
    const [lastMessage, setLastMessage] = useState(null);
    const [isConnected, setIsConnected] = useState(false);
    const ws = useRef(null);
    const reconnectTimeout = useRef(null);

    const connect = useCallback(() => {
        if (ws.current && ws.current.readyState === WebSocket.OPEN) return;
        
        const socket = new WebSocket(url);
        ws.current = socket;

        socket.onopen = () => {
            console.log('WebSocket connected');
            setIsConnected(true);
            if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
        };

        socket.onmessage = (event) => setLastMessage(event.data);
        socket.onclose = () => {
            console.log('WebSocket disconnected');
            setIsConnected(false);
            // Only reconnect if we were previously connected, to avoid spam
            if (isConnected) {
                reconnectTimeout.current = setTimeout(() => connect(), 10000);
            }
        };
        socket.onerror = (error) => {
            console.warn('WebSocket connection failed (this is expected if backend is not running):', error);
            // Don't close socket here as onclose will handle reconnection
        };
    }, [url]);

    useEffect(() => {
        connect();
        return () => {
            if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
            if (ws.current) ws.current.close();
        };
    }, [connect]);

    const sendMessage = useCallback((data) => {
        if (ws.current?.readyState === WebSocket.OPEN) {
            ws.current.send(JSON.stringify(data));
        }
    }, []);

    return { lastMessage, isConnected, sendMessage };
}
