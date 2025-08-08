import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import api from "../services/api";

function RegisterPage() {
  const [formData, setFormData] = useState({
    username: "",
    email: "",
    password1: "",
    password2: "",
  });
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (formData.password1 !== formData.password2) {
      setError({ detail: "Passwords do not match." });
      return;
    }

    setIsLoading(true);
    try {
      // We only need username, email, and password for the API
      const { username, email, password1, password2 } = formData;
      await api.post("users/auth/registration/", {
        username,
        email,
        password1,
        password2,
      });

      // Redirect to login page with a success message
      navigate("/login", {
        state: {
          message:
            "Registration successful! Please check your email to verify your account.",
        },
      });
    } catch (err) {
      // Handle various error formats from the backend
      const errorData = err.response?.data;
      if (errorData) {
        if (typeof errorData === "string") {
          setError({ detail: errorData });
        } else {
          // Combine all error messages into one string
          const messages = Object.values(errorData).flat().join(" ");
          setError({
            detail: messages || "An unknown registration error occurred.",
          });
        }
      } else {
        setError({ detail: "An unknown registration error occurred." });
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div>
      <h2>Create Your QuantNest Account</h2>
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: "10px" }}>
          <input
            type="text"
            name="username"
            placeholder="Username"
            onChange={handleChange}
            required
          />
        </div>
        <div style={{ marginBottom: "10px" }}>
          <input
            type="email"
            name="email"
            placeholder="Email Address"
            onChange={handleChange}
            required
          />
        </div>
        <div style={{ marginBottom: "10px" }}>
          <input
            type="password"
            name="password1"
            placeholder="Password"
            onChange={handleChange}
            required
          />
        </div>
        <div style={{ marginBottom: "10px" }}>
          <input
            type="password"
            name="password2"
            placeholder="Confirm Password"
            onChange={handleChange}
            required
          />
        </div>
        <button type="submit" disabled={isLoading}>
          {isLoading ? "Registering..." : "Register"}
        </button>
      </form>
      {error && <p style={{ color: "red" }}>{error.detail}</p>}
      <p>
        Already have an account? <Link to="/login">Login here</Link>.
      </p>
    </div>
  );
}

export default RegisterPage;
