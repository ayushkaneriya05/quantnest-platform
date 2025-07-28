import React from "react";
import { useSelector } from "react-redux";
import { Navigate, Outlet, useLocation } from "react-router-dom";

function ProtectedRoute() {
  // Get the access token from the Redux store
  const { accessToken } = useSelector((state) => state.auth);
  const location = useLocation();

  if (!accessToken) {
    // If the user is not authenticated, redirect them to the login page.
    // We also pass the original location they were trying to access,
    // so we can redirect them back after they log in.
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // If the user is authenticated, render the child component(s)
  // that are nested inside this route (e.g., <DashboardPage />).
  return <Outlet />;
}

export default ProtectedRoute;
