import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { Provider } from "react-redux";
import { GoogleOAuthProvider } from "@react-oauth/google";
import { store } from "./store";
import App from "./App.jsx";
import "./index.css";
import { WebSocketProvider } from "@/contexts/websocket-context";

const googleClientId = import.meta.env.VITE_REACT_APP_GOOGLE_CLIENT_ID;

export const AppWithAuth = () => {
  if (googleClientId) {
    return (
      <GoogleOAuthProvider clientId={googleClientId}>
        <BrowserRouter>
          <WebSocketProvider>
            <App />
          </WebSocketProvider>
        </BrowserRouter>
      </GoogleOAuthProvider>
    );
  }

  return (
    <BrowserRouter>
      <App />
    </BrowserRouter>
  );
};

ReactDOM.createRoot(document.getElementById("root")).render(
  <Provider store={store}>
    <AppWithAuth />
  </Provider>
);
