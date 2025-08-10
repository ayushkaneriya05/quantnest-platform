import { useEffect, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { useDispatch } from "react-redux";
import api from "@/services/api";
import { loginSuccess, fetchUserProfile } from "@/store/authSlice";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Chrome, CheckCircle, AlertCircle, Loader2 } from "lucide-react";
import MainHeader from "@/components/layout/main-header";

export default function SocialLoginHandler() {
  const [searchParams] = useSearchParams();
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const [status, setStatus] = useState("processing"); // 'processing', 'success', 'error'
  const [error, setError] = useState("");

  useEffect(() => {
    const accessToken = searchParams.get("access_token");
    console.log("Access Token from URL:", accessToken);
    const error = searchParams.get("error");

    if (error) {
      setStatus("error");
      setError("Google authentication was cancelled or failed.");
      return;
    }

    if (accessToken) {
      setStatus("processing");
      api
        .post(
          "users/auth/google/",
          { access_token: accessToken },
          { withCredentials: false }
        )
        .then(async (response) => {
          setStatus("success");
          dispatch(loginSuccess(response.data));
          await dispatch(fetchUserProfile());

          setTimeout(() => {
            navigate("/dashboard");
          }, 1000);
        })
        .catch((error) => {
          console.error("Google login failed on backend", error);
          setStatus("error");
          setError(
            error.response?.data?.detail ||
              "Google authentication failed. Please try again."
          );
        });
    } else {
      setStatus("error");
      setError("No authentication token received from Google.");
    }
  }, [searchParams, dispatch, navigate]);

  const handleRetry = () => {
    navigate("/login");
  };

  const renderContent = () => {
    switch (status) {
      case "processing":
        return (
          <>
            <div className="flex justify-center mb-4">
              <Loader2 className="h-12 w-12 text-indigo-400 animate-spin" />
            </div>
            <CardTitle className="text-2xl font-bold text-slate-100 text-center">
              Authenticating with Google
            </CardTitle>
            <CardDescription className="text-slate-400 mt-2 text-center">
              Please wait while we complete your authentication...
            </CardDescription>
          </>
        );

      case "success":
        return (
          <>
            <div className="flex justify-center mb-4">
              <CheckCircle className="h-12 w-12 text-green-400" />
            </div>
            <CardTitle className="text-2xl font-bold text-slate-100 text-center">
              Authentication Successful!
            </CardTitle>
            <CardDescription className="text-slate-400 mt-2 text-center">
              Redirecting you to your dashboard...
            </CardDescription>
          </>
        );

      case "error":
        return (
          <>
            <div className="flex justify-center mb-4">
              <AlertCircle className="h-12 w-12 text-red-400" />
            </div>
            <CardTitle className="text-2xl font-bold text-slate-100 text-center">
              Authentication Failed
            </CardTitle>
            <CardDescription className="text-slate-400 mt-2 text-center">
              {error}
            </CardDescription>
            <div className="flex gap-3 mt-6">
              <Button
                onClick={handleRetry}
                className="flex-1 bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white shadow-[0_8px_32px_rgba(99,102,241,0.3)]"
              >
                Try Again
              </Button>
            </div>
          </>
        );

      default:
        return null;
    }
  };

  return (
    <div className="flex flex-col min-h-screen bg-black">
      <MainHeader />
      <div className="flex flex-1 items-center justify-center container-padding py-6 sm:py-8 md:py-12 lg:py-16">
        <Card className="w-full max-w-md bg-gray-900/50 border border-gray-800/50 shadow-lg rounded-xl p-4 sm:p-6">
          <CardHeader className="text-center pb-6">
            {renderContent()}
          </CardHeader>
        </Card>
      </div>
    </div>
  );
}
