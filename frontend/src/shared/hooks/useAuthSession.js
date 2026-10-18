import { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { initializeAuth, logout, fetchUserProfile } from "../store/authSlice";
import { ensureFreshAccessToken } from "../services/api";
import { AUTH_EVENT_KEY, invalidateAuthRequests } from "../services/authSession";

export function useAuthSession() {
  const dispatch = useDispatch();
  const accessToken = useSelector((state) => state.auth.accessToken);
  const signedIn = Boolean(accessToken);

  useEffect(() => { dispatch(initializeAuth()); }, [dispatch]);

  useEffect(() => {
    const handleTabEvent = (event) => {
      if (event.key !== AUTH_EVENT_KEY || !event.newValue) return;
      const { type } = JSON.parse(event.newValue);
      invalidateAuthRequests();
      if (type === "logout") dispatch({ ...logout(), meta: { remote: true } });
      else dispatch(initializeAuth({ force: true }));
    };
    window.addEventListener("storage", handleTabEvent);
    return () => window.removeEventListener("storage", handleTabEvent);
  }, [dispatch]);

  useEffect(() => {
    if (!signedIn) return;
    let profileRefreshedAt = Date.now();
    const refresh = () => {
      if (document.visibilityState === "visible") {
        // Network failures keep the current session; the next interval retries.
        ensureFreshAccessToken().catch(() => {});
        if (Date.now() - profileRefreshedAt >= 25 * 60000) {
          profileRefreshedAt = Date.now();
          dispatch(fetchUserProfile());
        }
      }
    };
    const timer = setInterval(refresh, 30000);
    document.addEventListener("visibilitychange", refresh);
    window.addEventListener("focus", refresh);
    return () => {
      clearInterval(timer);
      document.removeEventListener("visibilitychange", refresh);
      window.removeEventListener("focus", refresh);
    };
  }, [signedIn, dispatch]);
}
