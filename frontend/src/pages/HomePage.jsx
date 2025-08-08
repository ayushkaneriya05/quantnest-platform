import React from "react";
import { useSelector } from "react-redux";
import { Link } from "react-router-dom";

function HomePage() {
  const { accessToken, user } = useSelector((state) => state.auth);

  return (
    <div style={{ textAlign: "center", marginTop: "50px" }}>
      <h1>Welcome to QuantNest</h1>
      <p>Your intelligent, AI-powered trading and investment platform.</p>
      <div style={{ marginTop: "30px" }}>
        {accessToken ? (
          <div>
            <p>Hello, {user?.username || "Trader"}! You are logged in.</p>
            <Link to="/dashboard">
              <button>Go to Your Dashboard</button>
            </Link>
          </div>
        ) : (
          <div>
            <p>
              Join our community to start building and testing your trading
              strategies today.
            </p>
            <Link to="/register" style={{ marginRight: "10px" }}>
              <button>Get Started</button>
            </Link>
            <Link to="/login">
              <button>Login</button>
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}

export default HomePage;
