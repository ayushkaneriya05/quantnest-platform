import React, { useEffect } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { useDispatch } from "react-redux";
import api from "../services/api";
import { loginSuccess } from "../store/authSlice";

function SocialLoginHandler() {
  const [searchParams] = useSearchParams();
  const dispatch = useDispatch();
  const navigate = useNavigate();

  useEffect(() => {
    const accessToken = searchParams.get("access_token");
    if (accessToken) {
      api
        .post("/auth/google/", { access_token: accessToken })
        .then((response) => {
          dispatch(loginSuccess(response.data));
          navigate("/dashboard");
        })
        .catch((error) => {
          console.error("Google login failed on backend", error);
          navigate("/login");
        });
    }
  }, [searchParams, dispatch, navigate]);

  return <div>Loading...</div>;
}

export default SocialLoginHandler;
