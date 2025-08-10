import { useState } from "react";
import { Link } from "react-router-dom";
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
import { Mail, ArrowLeft } from "lucide-react";
import MainHeader from "@/components/layout/main-header";

export default function PasswordResetRequestPage() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setMessage("");
    setIsLoading(true);

    try {
      await api.post("users/auth/password/reset/", { email });
      setMessage("Password reset email sent. Please check your inbox.");
    } catch (err) {
      setError(
        err.response?.data?.detail || "Failed to send password reset email."
      );
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
              Reset Your Password
            </CardTitle>
            <CardDescription className="text-slate-400 mt-2">
              Enter your email address and we will send you a link to reset your
              password.
            </CardDescription>
          </CardHeader>
          <CardContent className="content-spacing px-0">
            {message && (
              <div className="mb-4 p-3 bg-green-900/50 border border-green-800 rounded-lg text-green-300 text-sm">
                {message}
              </div>
            )}

            <form className="text-spacing" onSubmit={handleSubmit}>
              <div className="text-spacing-sm">
                <Label
                  htmlFor="email"
                  className="text-slate-200 text-sm font-medium"
                >
                  Email Address
                </Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                  <Input
                    id="email"
                    name="email"
                    type="email"
                    placeholder="you@example.com"
                    className="pl-10 bg-gray-800/50 border-gray-700/50 text-slate-100 placeholder:text-slate-500 h-11"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
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
                {isLoading ? "Sending..." : "Send Reset Email"}
              </Button>
            </form>

            <div className="text-center text-sm text-slate-400 pt-4 border-t border-gray-800/50">
              Remember your password?{" "}
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
