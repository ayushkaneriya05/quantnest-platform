import React, { useState } from "react";
import { useSelector, useDispatch } from "react-redux";
// import { QRCode } from "qrcode.react";
import api from "../services/api";
import { fetchUserProfile } from "../store/authSlice";

function Enable2FA() {
  const [qrCode, setQrCode] = useState("");
  const [secretKey, setSecretKey] = useState("");
  const [token, setToken] = useState("");
  const [message, setMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false); // Add loading state
  const [error, setError] = useState(""); // Add error state
  const dispatch = useDispatch();

  const handleCreate2FA = async () => {
    setIsLoading(true); // Set loading to true
    setError("");
    setMessage("");
    try {
      const response = await api.get("users/2fa/create/");
      // Convert the SVG string to a Base64 Data URI
      const svgBase64 = btoa(response.data.qr_code);
      setQrCode(`data:image/svg+xml;base64,${svgBase64}`);
      setSecretKey(response.data.secret_key);
      setMessage("Scan the QR code with your authenticator app.");
    } catch (err) {
      setError("Error creating 2FA setup. Please try again.");
      console.error(err);
    } finally {
      setIsLoading(false); // Set loading to false
    }
  };

  const handleVerify2FA = async () => {
    setIsLoading(true);
    setError("");
    try {
      await api.post("users/2fa/verify/", { token });
      setMessage("2FA has been successfully enabled!");
      dispatch(fetchUserProfile());
      setQrCode(""); // Clear setup details on success
      setSecretKey("");
      setToken("");
    } catch (err) {
      setError("Verification failed. The token may be invalid.");
      console.error("Verification failed:", err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div>
      <h4>Enable Two-Factor Authentication</h4>
      <button onClick={handleCreate2FA} disabled={isLoading}>
        {isLoading ? "Generating..." : "Start 2FA Setup"}
      </button>

      {error && <p style={{ color: "red" }}>{error}</p>}

      {qrCode && (
        <div>
          <p>{message}</p>
          {/* Use a standard <img> tag with the Data URI */}
          <img src={qrCode} alt="2FA QR Code" />
          <p>
            Or manually enter this key: <strong>{secretKey}</strong>
          </p>
          <input
            type="text"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="Enter 6-digit code"
            maxLength="6"
          />
          <button onClick={handleVerify2FA} disabled={isLoading}>
            {isLoading ? "Verifying..." : "Verify & Enable"}
          </button>
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
        await api.post("users/2fa/disable/");
        setMessage("2FA has been disabled.");
        dispatch(fetchUserProfile());
      } catch (error) {
        setMessage("Failed to disable 2FA.", error);
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
      {!user.is_2fa_enabled ? (
        <>
          <hr />
          <Enable2FA />
        </>
      ) : (
        <>
          <hr />
          <h4>Disable Two-Factor Authentication</h4>
          <button onClick={handleDisable2FA}>Disable 2FA</button>
        </>
      )}
      {message && <p>{message}</p>}
    </div>
  );
}

export default ProfilePage;
