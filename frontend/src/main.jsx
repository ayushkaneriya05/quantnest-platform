import ReactDOM from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { Provider } from "react-redux";
import { store } from "./shared/store";
import App from "./app/App.jsx";
import "./index.css";
import ThemeProvider from "./shared/context/ThemeProvider";

// A data router provides navigation blockers; page routes stay in AppRoutes.
const router = createBrowserRouter([
  { path: "*", element: <ThemeProvider><App /></ThemeProvider> },
], { future: { v7_relativeSplatPath: true } });

ReactDOM.createRoot(document.getElementById("root")).render(
  <Provider store={store}>
    <RouterProvider router={router} future={{ v7_startTransition: true }} />
  </Provider>
);
