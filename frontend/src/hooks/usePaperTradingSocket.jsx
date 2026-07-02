import { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import {
  setSocketConnected,
  setInitialState,
  updatePortfolio,
} from "../store/paperTradingSlice";

const usePaperTradingSocket = () => {
  const dispatch = useDispatch();
  const { accessToken } = useSelector((state) => state.auth);

  useEffect(() => {
    if (!accessToken) return;

    const socket = new WebSocket(
      `ws://localhost:8001/ws/paper-trading/?token=${accessToken}`
    );

    socket.onopen = () => {
      console.log("WebSocket connected");
      dispatch(setSocketConnected(true));
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "initial_state") {
        dispatch(setInitialState(data.payload));
      } else if (data.type === "portfolio_update") {
        dispatch(updatePortfolio(data.payload));
      }
    };

    socket.onclose = () => {
      console.log("WebSocket disconnected");
      dispatch(setSocketConnected(false));
    };

    socket.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    // Cleanup on component unmount
    return () => {
      socket.close();
    };
  }, [accessToken, dispatch]);
};

export default usePaperTradingSocket;
