import { useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import api from "@/services/api";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Lock, ArrowLeft } from "lucide-react";
import MainHeader from "@/components/layout/main-header";

export default function PasswordResetConfirmPage() {
  const { uid, token } = useParams();
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    new_password1: "",
    new_password2: "",
  });
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (formData.new_password1 !== formData.new_password2) {
      setError("Passwords do not match.");
      return;
    }

    if (formData.new_password1.length < 8) {
      setError("Password must be at least 8 characters long.");
      return;
    }

    setIsLoading(true);
    try {
      await api.post("users/auth/password/reset/confirm/", {
        uid,
        token,
        new_password1: formData.new_password1,
        new_password2: formData.new_password2,
      });

      navigate("/login", {
        state: {
          message:
            "Password reset successful. Please log in with your new password.",
        },
      });
    } catch (err) {
      const errorData = err.response?.data;
      if (errorData) {
        if (typeof errorData === "string") {
          setError(errorData);
        } else {
          const messages = Object.values(errorData).flat().join(" ");
          setError(messages || "Password reset failed.");
        }
      } else {
        setError("Password reset failed. The link may be expired or invalid.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col min-h-screen bg-black">
      <MainHeader />
      <div className="flex flex-1 items-center justify-center container-padding py-6 sm:py-8 md:py-12 lg:py-16">
        <Card className="w-full max-w-md bg-gray-900/50 border border-gray-800/50 shadow-lg rounded-xl p-4 sm:p-6">
          <CardHeader className="text-center pb-6">
            <CardTitle className="text-2xl sm:text-3xl font-bold text-slate-100">
              Set New Password
            </CardTitle>
            <CardDescription className="text-slate-400 mt-2">
              Enter your new password below.
            </CardDescription>
          </CardHeader>
          <CardContent className="content-spacing px-0">
            <form className="text-spacing" onSubmit={handleSubmit}>
              <div className="text-spacing-sm">
                <Label
                  htmlFor="new_password1"
                  className="text-slate-200 text-sm font-medium"
                >
                  New Password
                </Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                  <Input
                    id="new_password1"
                    name="new_password1"
                    type="password"
                    placeholder="••••••••"
                    className="pl-10 bg-gray-800/50 border-gray-700/50 text-slate-100 placeholder:text-slate-500 h-11"
                    value={formData.new_password1}
                    onChange={handleChange}
                    required
                  />
                </div>
                <p className="text-xs text-slate-500 mt-2 leading-relaxed">
                  Password must be at least 8 characters long, include an
                  uppercase letter, a lowercase letter, a number, and a symbol.
                </p>
              </div>

              <div className="text-spacing-sm">
                <Label
                  htmlFor="new_password2"
                  className="text-slate-200 text-sm font-medium"
                >
                  Confirm New Password
                </Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                  <Input
                    id="new_password2"
                    name="new_password2"
                    type="password"
                    placeholder="••••••••"
                    className="pl-10 bg-gray-800/50 border-gray-700/50 text-slate-100 placeholder:text-slate-500 h-11"
                    value={formData.new_password2}
                    onChange={handleChange}
                    required
                  />
                </div>
              </div>

              {error && (
                <div className="mb-4 p-3 bg-red-900/50 border border-red-800 rounded-lg text-red-300 text-sm">
                  {error}
                </div>
              )}

              <Button
                type="submit"
                disabled={isLoading}
                className="w-full bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white shadow-[0_8px_32px_rgba(99,102,241,0.3)] h-11 mt-6"
              >
                {isLoading ? "Resetting..." : "Reset Password"}
              </Button>
            </form>

            <div className="text-center text-sm text-slate-400 pt-4 border-t border-gray-800/50">
              <Link
                to="/login"
                className="underline text-indigo-400 hover:text-indigo-300 font-medium"
              >
                Back to Login
              </Link>
            </div>
            <div className="text-center text-sm pt-3">
              <Link
                to="/"
                className="text-slate-400 hover:text-slate-200 flex items-center justify-center gap-1 transition-colors"
              >
                <ArrowLeft className="h-4 w-4" />
                Back to Landing Page
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
