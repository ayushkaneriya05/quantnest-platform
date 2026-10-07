import { useEffect, useRef } from "react";
import { useDispatch, useSelector } from "react-redux";
import { setPaperLastMessage } from "../store/websocketSlice";
import { ensureFreshAccessToken, getWebSocketUrl } from "../services/api";

export function usePaperTradingUpdate() {
  return useSelector((state) => state.websocket.paperLastMessage);
}

export function usePaperTradingWebSocket({ enabled = true } = {}) {
  const dispatch = useDispatch();
  const socketRef = useRef(null);
  const reconnectTimerRef = useRef(null);
  const attemptsRef = useRef(0);
  const activeRef = useRef(false);

  useEffect(() => {
    if (!enabled) return undefined;
    activeRef.current = true;
    let disposed = false;

    const retry = () => {
      if (!activeRef.current || disposed) return;
      const attempts = attemptsRef.current++;
      reconnectTimerRef.current = setTimeout(connect, Math.min(1000 * 2 ** Math.min(attempts, 5), 30000));
    };
    const connect = async () => {
      if (!activeRef.current || socketRef.current?.readyState === WebSocket.OPEN || socketRef.current?.readyState === WebSocket.CONNECTING) return;
      try { await ensureFreshAccessToken(); } catch { retry(); return; }
      if (!activeRef.current || disposed) return;
      const socket = new WebSocket(getWebSocketUrl("/ws/paper/"));
      socketRef.current = socket;

      socket.onopen = () => {
        attemptsRef.current = 0;
        if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      };

      socket.onmessage = (event) => {
        if (socketRef.current !== socket) return;
        try {
          const message = JSON.parse(event.data);
          if (["ORDER_UPDATE", "POSITION_UPDATE"].includes(message?.event_type)) {
            dispatch(setPaperLastMessage(message));
          }
        } catch (error) {
          console.error("Paper WebSocket parse error:", error);
        }
      };

      socket.onclose = (event) => {
        if (!activeRef.current || socketRef.current !== socket || event.code === 4401) return;
        retry();
      };
    };

    connect();
    return () => {
      activeRef.current = false;
      disposed = true;
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
      if (socketRef.current) {
        socketRef.current.onopen = null;
        socketRef.current.onmessage = null;
        socketRef.current.onclose = null;
        socketRef.current.close(1000, "Paper updates consumer unmounted");
      }
      socketRef.current = null;
    };
  }, [dispatch, enabled]);
}
