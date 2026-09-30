import { useEffect, useRef } from "react";
import { useDispatch, useSelector } from "react-redux";
import { setPaperLastMessage } from "../store/websocketSlice";

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

    const connect = () => {
      if (!activeRef.current || socketRef.current?.readyState === WebSocket.OPEN || socketRef.current?.readyState === WebSocket.CONNECTING) return;
      const token = localStorage.getItem("accessToken");
      if (!token) return;

      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const host = window.location.hostname === "localhost" ? "localhost:8000" : window.location.host;
      const socket = new WebSocket(`${protocol}//${host}/ws/paper/?token=${token}`);
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

      socket.onclose = () => {
        if (!activeRef.current || socketRef.current !== socket) return;
        const delay = Math.min(1000 * 2 ** attemptsRef.current, 30000);
        attemptsRef.current += 1;
        reconnectTimerRef.current = setTimeout(connect, delay);
      };
    };

    connect();
    return () => {
      activeRef.current = false;
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
      if (socketRef.current) socketRef.current.close(1000, "Paper updates consumer unmounted");
      socketRef.current = null;
    };
  }, [dispatch, enabled]);
}
