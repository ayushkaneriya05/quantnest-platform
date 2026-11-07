import { Button } from "@/shared/components/ui/button";
import { GlobalLoader } from '@/shared/components/ui/global-loader';
import { useSelector } from "react-redux";
import { Navigate, Outlet, useLocation } from "react-router-dom";
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
        <GlobalLoader text="Opening your workspace…" />
      </div>
    );
  }

  if (!isAuthenticated && error) {
    return <div className="flex min-h-dvh flex-col items-center justify-center gap-4 text-foreground">
      <p>{error}</p>
      <Button type="button" onClick={() => dispatch(initializeAuth())}>Retry connection</Button>
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
