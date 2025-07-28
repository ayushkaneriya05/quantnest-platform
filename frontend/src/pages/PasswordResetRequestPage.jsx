import React, { useState } from "react";
import api from "../services/api";

function PasswordResetRequestPage() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setMessage("");
    try {
      await api.post("/auth/password/reset/", { email });
      setMessage(
        "If an account with that email exists, a password reset link has been sent."
      );
    } catch (error) {
      setMessage("An error occurred. Please try again.");
    }
  };

  return (
    <div>
      <h2>Reset Password</h2>
      <p>
        Enter your email address and we will send you a link to reset your
        password.
      </p>
      <form onSubmit={handleSubmit}>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="Email"
          required
        />
        <button type="submit">Send Reset Link</button>
      </form>
      {message && <p>{message}</p>}
    </div>
  );
}

export default PasswordResetRequestPage;
