import { useSelector } from "react-redux";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Loader2 } from "lucide-react";
import React from "react";
function ProtectedRoute() {
  const { accessToken, isAuthenticated, isLoading } = useSelector(
    (state) => state.auth
  );
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-black">
        <Card className="p-8 bg-gray-900/50 border border-gray-800/50">
          <div className="flex items-center gap-3 text-slate-200">
            <Loader2 className="h-6 w-6 animate-spin" />
            <span>Loading...</span>
          </div>
        </Card>
      </div>
    );
  }

  if (!accessToken && !isAuthenticated) {
    // If the user is not authenticated, redirect them to the login page.
    // We also pass the original location they were trying to access,
    // so we can redirect them back after they log in.
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <Outlet />;
}

export default ProtectedRoute;
