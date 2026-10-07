import axios from "axios";
import { tokenRefreshed, logout } from "../store/authSlice";
import { store } from "../store/index";
import { AuthChangedError, SessionEndedError, getAuthGeneration, readAccessToken, withAuthLock } from "./authSession";

const api = axios.create({
  baseURL: import.meta.env.VITE_REACT_APP_API_URL,
  withCredentials: true,
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

let csrfToken = null;
let hasRefreshCookie = false;
let csrfPromise = null;
let refreshPromise = null;
let refreshGeneration = null;
const authUrl = (path) => `${(api.defaults.baseURL || "").replace(/\/$/, "")}/users/auth/${path}/`;
const isAuthAction = (url = "") => /users\/(?:auth\/(?:login\/|google\/|verify-2fa\/|registration\/|logout\/|password\/)|2fa\/backup-codes\/verify\/)/.test(url);
const isPublicAuth = (url = "") => isAuthAction(url) && !url.includes("password/change/");
export const isAuthFailure = (error) => error instanceof SessionEndedError || [401, 403].includes(error.response?.status);

async function loadCSRFToken(force = false) {
  if (force) csrfToken = null;
  if (!csrfToken && !csrfPromise) {
    csrfPromise = axios.get(authUrl("csrf"), { withCredentials: true, timeout: 10000 })
      .then(({ data }) => {
        if (!data.csrf_token || typeof data.has_refresh_cookie !== "boolean") throw new Error("Could not initialize secure authentication.");
        csrfToken = data.csrf_token;
        hasRefreshCookie = data.has_refresh_cookie;
        return csrfToken;
      }).finally(() => { csrfPromise = null; });
  }
  return csrfToken || csrfPromise;
}

export async function refreshAccessToken() {
  if (refreshPromise && refreshGeneration !== getAuthGeneration()) {
    try { await refreshPromise; } catch { /* Wait for the previous cookie action to finish. */ }
    return refreshAccessToken();
  }
  if (!refreshPromise) {
    const generation = getAuthGeneration();
    refreshGeneration = generation;
    refreshPromise = withAuthLock(async () => {
      const csrf = await loadCSRFToken(true);
      if (!hasRefreshCookie) throw new SessionEndedError();
      const { data } = await axios.post(authUrl("token/refresh"), {}, {
        withCredentials: true, timeout: 10000, headers: { "X-CSRFToken": csrf },
      });
      if (generation !== getAuthGeneration()) throw new AuthChangedError();
      if (!data.access) throw new Error("Token refresh did not return an access token.");
      csrfToken = data.csrf_token || csrfToken;
      store.dispatch(tokenRefreshed(data));
      return data.access;
    }).catch((error) => {
      if (generation === getAuthGeneration() && isAuthFailure(error)) store.dispatch(logout());
      throw error;
    }).finally(() => { refreshPromise = null; });
  }
  return refreshPromise;
}

export async function ensureFreshAccessToken() {
  const token = store.getState().auth.accessToken;
  const claims = readAccessToken(token);
  if (!claims || claims.exp * 1000 < Date.now() + 60000) return refreshAccessToken();
  return token;
}

export function getWebSocketUrl(path) {
  const url = new URL(api.defaults.baseURL || "/api/v1/", window.location.origin);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = path;
  url.search = "";
  url.hash = "";
  return url.toString();
}

api.interceptors.request.use(async (config) => {
  config._authGeneration ??= getAuthGeneration();
  const token = store.getState().auth.accessToken;
  if (token && !config.publicRequest && !isPublicAuth(config.url)) config.headers.Authorization = `Bearer ${token}`;
  if (config.data instanceof FormData) delete config.headers["Content-Type"];
  if (!["get", "head", "options"].includes(config.method)) {
    if (isAuthAction(config.url)) {
      config._authAdapter ??= axios.getAdapter(config.adapter);
      config.adapter = (request) => withAuthLock(async () => {
        if (!isPublicAuth(request.url) && request._authGeneration !== getAuthGeneration()) throw new AuthChangedError();
        request.headers["X-CSRFToken"] = await loadCSRFToken(true);
        return config._authAdapter(request);
      });
    } else {
      config.headers["X-CSRFToken"] = await loadCSRFToken();
    }
  }
  return config;
});

api.interceptors.response.use(
  (response) => {
    if (!response.config.publicRequest && !isPublicAuth(response.config.url) && response.config._authGeneration !== getAuthGeneration()) throw new AuthChangedError();
    if (response.data?.csrf_token) csrfToken = response.data.csrf_token;
    return response;
  },
  async (error) => {
    const request = error.config;
    if (request && !request.publicRequest && request._authGeneration !== getAuthGeneration()) throw new AuthChangedError();
    if (request && error.response?.status === 401 && !request.publicRequest && !isPublicAuth(request.url)) {
      if (request._retry) {
        store.dispatch(logout());
      } else {
        request._retry = true;
        const current = store.getState().auth.accessToken;
        const access = current && request.headers.Authorization !== `Bearer ${current}`
          ? current : await refreshAccessToken();
        request.headers.Authorization = `Bearer ${access}`;
        return api(request);
      }
    }
    return Promise.reject(error);
  },
);

export default api;
