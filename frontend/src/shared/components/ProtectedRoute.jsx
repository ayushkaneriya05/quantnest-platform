import { useSelector } from "react-redux";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { Card } from "@/shared/components/ui/card";
import { Loader2 } from "lucide-react";
import { useDispatch } from "react-redux";
import { initializeAuth } from "../store/authSlice";
function ProtectedRoute() {
  const { accessToken, isAuthenticated, isInitializing, initialized, error } = useSelector(
    (state) => state.auth
  );
  const location = useLocation();
  const dispatch = useDispatch();

  if (!initialized || isInitializing) {
    return (
      <div className="flex items-center justify-center min-h-dvh bg-background">
        <Card className="p-8 bg-card/50 border border-border/50">
          <div className="flex items-center gap-3 text-foreground">
            <Loader2 className="h-6 w-6 animate-spin" />
            <span>Loading...</span>
          </div>
        </Card>
      </div>
    );
  }

  if (!isAuthenticated && error) {
    return <div className="flex min-h-dvh flex-col items-center justify-center gap-4 text-foreground">
      <p>{error}</p>
      <button onClick={() => dispatch(initializeAuth())} className="rounded-md bg-indigo-600 px-4 py-2 text-white">Retry connection</button>
    </div>;
  }

  if (!accessToken || !isAuthenticated) {
    // If the user is not authenticated, redirect them to the login page.
    // We also pass the original location they were trying to access,
    // so we can redirect them back after they log in.
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <Outlet />;
}

export default ProtectedRoute;
