import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { Provider } from "react-redux";
import { store } from "./shared/store";
import App from "./app/App.jsx";
import "./index.css";
import ThemeProvider from "./shared/context/ThemeProvider";

ReactDOM.createRoot(document.getElementById("root")).render(
  <Provider store={store}>
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <ThemeProvider><App /></ThemeProvider>
    </BrowserRouter>
  </Provider>
);
