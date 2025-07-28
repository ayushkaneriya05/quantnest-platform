import React, { useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import QRCode from "qrcode.react";
import api from "../services/api";
import { fetchUserProfile } from "../store/authSlice";

function Enable2FA() {
  const [qrCode, setQrCode] = useState("");
  const [secretKey, setSecretKey] = useState("");
  const [token, setToken] = useState("");
  const [message, setMessage] = useState("");

  const handleCreate2FA = async () => {
    try {
      const response = await api.get("/auth/2fa/create/");
      setQrCode(response.data.qr_code);
      setSecretKey(response.data.secret_key);
      setMessage("Scan the QR code with your authenticator app.");
    } catch (error) {
      setMessage("Error creating 2FA setup.");
    }
  };

  const handleVerify2FA = async () => {
    try {
      await api.post("/auth/2fa/verify/", { token });
      setMessage("2FA has been successfully enabled!");
      setQrCode(""); // Clear setup details
    } catch (error) {
      setMessage("Verification failed. Invalid token.");
    }
  };

  return (
    <div>
      <h4>Enable Two-Factor Authentication</h4>
      <button onClick={handleCreate2FA}>Start 2FA Setup</button>
      {qrCode && (
        <div>
          <p>{message}</p>
          <div dangerouslySetInnerHTML={{ __html: qrCode }} />
          <p>
            Or manually enter this key: <strong>{secretKey}</strong>
          </p>
          <input
            type="text"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="Enter 6-digit code"
          />
          <button onClick={handleVerify2FA}>Verify & Enable</button>
        </div>
      )}
    </div>
  );
}

function ProfilePage() {
  const { user } = useSelector((state) => state.auth);
  const dispatch = useDispatch();
  const [message, setMessage] = useState("");
  // You would typically have a more complex form state here

  if (!user) {
    return <div>Loading profile...</div>;
  }

  const handleDisable2FA = async () => {
    if (window.confirm("Are you sure you want to disable 2FA?")) {
      try {
        await api.post("/auth/2fa/disable/");
        setMessage("2FA has been disabled.");
      } catch (error) {
        setMessage("Failed to disable 2FA.");
      }
    }
  };

  // In a real app, you would have inputs to update bio, username, etc.
  // and a form submission handler that makes a PUT request to /users/profile/.

  return (
    <div>
      <h2>My Profile</h2>
      <p>
        <strong>Email:</strong> {user.email}
      </p>
      <p>
        <strong>Username:</strong> {user.username}
      </p>
      <p>
        <strong>Bio:</strong> {user.bio || "Not set"}
      </p>
      <hr />
      <Enable2FA />
      <hr />
      <h4>Disable Two-Factor Authentication</h4>
      <button onClick={handleDisable2FA}>Disable 2FA</button>
      {message && <p>{message}</p>}
    </div>
  );
}

export default ProfilePage;
