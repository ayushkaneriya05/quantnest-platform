import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";
import { useGoogleLogin } from "@react-oauth/google";
import api from "../services/api";
import {
  loginSuccess,
  set2FARequired,
  fetchUserProfile,
} from "../store/authSlice";

function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [otpToken, setOtpToken] = useState("");
  const { is2FARequired } = useSelector((state) => state.auth);
  const [error, setError] = useState("");
  const dispatch = useDispatch();
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setError("");
    try {
      const payload = { username, password };
      if (is2FARequired && otpToken) {
        payload.otp_token = otpToken;
      }

      const response = await api.post("/users/auth/login/", payload);
      console.log(response);
      if (
        response.status === 200 &&
        response.data.access &&
        response.data.refresh
      ) {
        // Full login success
        dispatch(loginSuccess(response.data));
        // dispatch(fetchUserProfile());
        navigate("/dashboard");
      } else if (response.status === 200) {
        // 2FA is required
        dispatch(set2FARequired(true));
      }
    } catch (err) {
      setError(err.response?.data?.detail || "Login failed.");
      console.error(err.response.data);
    }
  };

  const handleGoogleLogin = useGoogleLogin({
    onSuccess: (tokenResponse) => {
      // Pass the Google token to our social login handler page
      navigate(`/google-callback?access_token=${tokenResponse.access_token}`);
    },
    onError: () => {
      setError("Google login failed.");
    },
  });

  return (
    <div>
      <h2>Login</h2>
      <form onSubmit={handleLogin}>
        {!is2FARequired ? (
          <>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="username"
              required
            />
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password"
              required
            />
          </>
        ) : (
          <>
            <p>Enter the code from your authenticator app.</p>
            <input
              type="text"
              value={otpToken}
              onChange={(e) => setOtpToken(e.target.value)}
              placeholder="6-Digit Code"
              required
            />
          </>
        )}
        <button type="submit">{is2FARequired ? "Verify Code" : "Login"}</button>
      </form>
      <hr />
      <button onClick={() => handleGoogleLogin()}>Login with Google</button>
      {error && <p style={{ color: "red" }}>{error}</p>}
      <p>
        <a href="/password-reset">Forgot Password?</a>
      </p>
    </div>
  );
}

export default LoginPage;
