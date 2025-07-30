import React from "react";
import { Link, useNavigate } from "react-router-dom";
import { useSelector, useDispatch } from "react-redux";
import { logout } from "../store/authSlice";
import api from "../services/api";

function Navbar() {
  const { accessToken, user } = useSelector((state) => state.auth);
  const dispatch = useDispatch();
  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      await api.post("/users/auth/logout/");
    } catch (error) {
      console.error("Logout failed", error);
    } finally {
      dispatch(logout());
      navigate("/login");
    }
  };

  return (
    <nav
      style={{
        display: "flex",
        gap: "1rem",
        padding: "1rem",
        background: "#f0f0f0",
      }}
    >
      <Link to="/">QuantNest</Link>
      {accessToken ? (
        <>
          <Link to="/dashboard">Dashboard</Link>
          <Link to="/profile">Profile ({user?.email})</Link>
          <button onClick={handleLogout}>Logout</button>
        </>
      ) : (
        <>
          <Link to="/login">Login</Link>
          <Link to="/register">Register</Link>
        </>
      )}
    </nav>
  );
}

export default Navbar;
