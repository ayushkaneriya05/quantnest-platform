import { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import {
  setSocketConnected,
  upsertOrder,
  upsertPosition,
} from "../store/paperTradingSlice";

const usePaperTradingSocket = () => {
  const dispatch = useDispatch();
  const { accessToken } = useSelector((state) => state.auth);

  useEffect(() => {
    if (!accessToken) return;

    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const apiHost = import.meta.env.VITE_REACT_APP_API_URL
      ? new URL(import.meta.env.VITE_REACT_APP_API_URL).host
      : window.location.host;
    
    // Connect to the MarketData consumer, which multiplexes paper trading updates
    // for the user via the user_{user_id} group.
    const socket = new WebSocket(
      `${protocol}://${apiHost}/ws/marketdata/?token=${accessToken}`
    );

    socket.onopen = () => {
      console.log("Paper Trading WebSocket connected (via MarketData)");
      dispatch(setSocketConnected(true));
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "order_update" && data.data) {
          dispatch(upsertOrder(data.data));
        } else if (data.type === "position_update" && data.data) {
          dispatch(upsertPosition(data.data));
        }
      } catch (err) {
        console.error("Failed to parse paper trading ws message", err);
      }
    };

    socket.onclose = () => {
      console.log("Paper Trading WebSocket disconnected");
      dispatch(setSocketConnected(false));
    };

    socket.onerror = (error) => {
      console.error("Paper Trading WebSocket error:", error);
    };

    // Cleanup on component unmount
    return () => {
      socket.close();
    };
  }, [accessToken, dispatch]);
};

export default usePaperTradingSocket;
