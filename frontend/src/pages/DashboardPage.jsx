import React from "react";
import { useSelector } from "react-redux";
import { Link } from "react-router-dom";

function DashboardPage() {
  const { user, isLoading } = useSelector((state) => state.auth);

  if (isLoading || !user) {
    return <div>Loading your dashboard...</div>;
  }

  return (
    <div>
      <h1>Dashboard</h1>
      <h2>Welcome back, {user.username}!</h2>
      <p>
        This is your personal dashboard. From here you can manage your
        strategies, view analytics, and access all of QuantNest's features.
      </p>

      <div
        style={{ marginTop: "2rem", padding: "1rem", border: "1px solid #ccc" }}
      >
        <h3>Quick Actions</h3>
        <ul>
          <li>
            <Link to="/strategy-builder">Create a New Trading Strategy</Link>
          </li>
          <li>
            <Link to="/paper-trading">Go to Paper Trading Terminal</Link>
          </li>
          <li>
            <Link to="/profile">View and Update Your Profile</Link>
          </li>
        </ul>
      </div>
    </div>
  );
}

export default DashboardPage;
