// Tokens stay in memory or HttpOnly cookies. Only non-secret tab events are stored.
export const AUTH_EVENT_KEY = "quantnest-auth-event";
let generation = 0;

export const getAuthGeneration = () => generation;
export const invalidateAuthRequests = () => { generation += 1; };

export class AuthChangedError extends Error {
  constructor() { super("Authentication changed while the request was running."); }
}

export class SessionEndedError extends Error {
  constructor() { super("Please sign in to continue."); }
}

export function announceAuthChange(type) {
  localStorage.setItem(AUTH_EVENT_KEY, JSON.stringify({ type, nonce: crypto.randomUUID() }));
}

export function withAuthLock(callback) {
  // Serializes cookie rotation, login and logout across tabs on the same origin.
  return navigator.locks ? navigator.locks.request("quantnest-auth", callback) : callback();
}

export function readAccessToken(token) {
  if (!token) return null;
  try {
    const part = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(atob(part));
  } catch {
    return null;
  }
}

export const authLifecycleMiddleware = ({ dispatch }) => (next) => (action) => {
  if (["auth/loginSuccess", "auth/logout"].includes(action.type)) {
    invalidateAuthRequests();
    if (!action.meta?.remote) announceAuthChange(action.type === "auth/logout" ? "logout" : "login");
    dispatch({ type: "notification/clearAllNotifications" });
    dispatch({ type: "websocket/clearPrivateUpdates" });
  }
  return next(action);
};
