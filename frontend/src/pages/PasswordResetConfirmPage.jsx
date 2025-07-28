import React, { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from "../services/api";

function PasswordResetConfirmPage() {
  const { uid, token } = useParams();
  const navigate = useNavigate();
  const [new_password1, setNewPassword1] = useState("");
  const [new_password2, setNewPassword2] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setMessage("");
    if (new_password1 !== new_password2) {
      setError("Passwords do not match.");
      return;
    }

    try {
      await api.post("/auth/password/reset/confirm/", {
        uid,
        token,
        new_password1,
        new_password2,
      });
      setMessage("Your password has been reset successfully. Please log in.");
      setTimeout(() => navigate("/login"), 3000);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Failed to reset password. The link may be invalid or expired."
      );
    }
  };

  return (
    <div>
      <h2>Set a New Password</h2>
      <form onSubmit={handleSubmit}>
        <input
          type="password"
          value={new_password1}
          onChange={(e) => setNewPassword1(e.target.value)}
          placeholder="New Password"
          required
        />
        <input
          type="password"
          value={new_password2}
          onChange={(e) => setNewPassword2(e.g.et.value)}
          placeholder="Confirm New Password"
          required
        />
        <button type="submit">Reset Password</button>
      </form>
      {message && <p style={{ color: "green" }}>{message}</p>}
      {error && <p style={{ color: "red" }}>{error}</p>}
    </div>
  );
}

export default PasswordResetConfirmPage;
