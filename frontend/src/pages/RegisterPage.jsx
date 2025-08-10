import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
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
import { Checkbox } from "@/components/ui/checkbox";
import { User, Mail, Lock, ArrowLeft } from "lucide-react";
import EmailVerificationModal from "@/components/auth/email-verification-modal";
import GoogleLoginButton, {
  GoogleLoginFallback,
} from "@/components/auth/GoogleLoginButton";
import MainHeader from "@/components/layout/main-header";

export default function RegisterPage() {
  const [isEmailModalOpen, setIsEmailModalOpen] = useState(false);
  const [registeredEmail, setRegisteredEmail] = useState("");
  const [formData, setFormData] = useState({
    firstName: "",
    lastName: "",
    username: "",
    email: "",
    password1: "",
    password2: "",
  });
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [agreeToTerms, setAgreeToTerms] = useState(false);
  const navigate = useNavigate();

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (!agreeToTerms) {
      setError({
        detail: "You must agree to the Terms of Service and Privacy Policy.",
      });
      return;
    }

    if (formData.password1 !== formData.password2) {
      setError({ detail: "Passwords do not match." });
      return;
    }

    if (formData.password1.length < 8) {
      setError({ detail: "Password must be at least 8 characters long." });
      return;
    }

    setIsLoading(true);
    try {
      const { firstName, lastName, username, email, password1, password2 } =
        formData;
      await api.post("users/auth/registration/", {
        first_name: firstName,
        last_name: lastName,
        username,
        email,
        password1,
        password2,
      });

      // Show email verification modal
      setRegisteredEmail(email);
      setIsEmailModalOpen(true);
    } catch (err) {
      const errorData = err.response?.data;
      if (errorData) {
        if (typeof errorData === "string") {
          setError({ detail: errorData });
        } else {
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

  const handleGoogleError = (errorMessage) => {
    setError({ detail: errorMessage });
  };

  const handleEmailVerificationComplete = () => {
    setIsEmailModalOpen(false);
    navigate("/login", {
      state: {
        message:
          "Registration successful! Please check your email to verify your account before logging in.",
      },
    });
  };

  const googleClientId = import.meta.env.VITE_REACT_APP_GOOGLE_CLIENT_ID;

  return (
    <div className="flex flex-col min-h-screen bg-black">
      <MainHeader />
      <div className="flex flex-1 items-center justify-center container-padding py-6 sm:py-8 md:py-12 lg:py-16">
        <Card className="w-full max-w-md bg-gray-900/50 border border-gray-800/50 shadow-lg rounded-xl p-4 sm:p-6">
          <CardHeader className="text-center pb-6">
            <CardTitle className="text-2xl sm:text-3xl font-bold text-slate-100 leading-tight">
              Create Your QuantNest Account
            </CardTitle>
            <CardDescription className="text-slate-400 mt-2">
              Join the future of intelligent trading today.
            </CardDescription>
          </CardHeader>
          <CardContent className="content-spacing px-0">
            {/* Google registration section */}
            <div className="space-y-3 sm:space-y-4">
              {googleClientId ? (
                <GoogleLoginButton
                  onError={handleGoogleError}
                  isLoading={isLoading}
                  type="registration"
                />
              ) : (
                <GoogleLoginFallback type="registration" />
              )}
            </div>

            <div className="relative flex items-center my-6">
              <div className="flex-grow border-t border-gray-700" />
              <span className="mx-4 flex-shrink text-slate-400 text-sm">
                OR
              </span>
              <div className="flex-grow border-t border-gray-700" />
            </div>

            <form className="text-spacing" onSubmit={handleSubmit}>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="text-spacing-sm">
                  <Label
                    htmlFor="firstName"
                    className="text-slate-200 text-sm font-medium"
                  >
                    First Name
                  </Label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                    <Input
                      id="firstName"
                      name="firstName"
                      type="text"
                      placeholder="John"
                      className="pl-10 bg-gray-800/50 border-gray-700/50 text-slate-100 placeholder:text-slate-500 h-11"
                      value={formData.firstName}
                      onChange={handleChange}
                      required
                    />
                  </div>
                </div>
                <div className="text-spacing-sm">
                  <Label
                    htmlFor="lastName"
                    className="text-slate-200 text-sm font-medium"
                  >
                    Last Name
                  </Label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                    <Input
                      id="lastName"
                      name="lastName"
                      type="text"
                      placeholder="Doe"
                      className="pl-10 bg-gray-800/50 border-gray-700/50 text-slate-100 placeholder:text-slate-500 h-11"
                      value={formData.lastName}
                      onChange={handleChange}
                      required
                    />
                  </div>
                </div>
              </div>
              <div className="text-spacing-sm">
                <Label
                  htmlFor="username"
                  className="text-slate-200 text-sm font-medium"
                >
                  Username
                </Label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                  <Input
                    id="username"
                    name="username"
                    type="text"
                    placeholder="quant_trader"
                    className="pl-10 bg-gray-800/50 border-gray-700/50 text-slate-100 placeholder:text-slate-500 h-11"
                    value={formData.username}
                    onChange={handleChange}
                    required
                  />
                </div>
              </div>
              <div className="text-spacing-sm">
                <Label
                  htmlFor="email"
                  className="text-slate-200 text-sm font-medium"
                >
                  Email
                </Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                  <Input
                    id="email"
                    name="email"
                    type="email"
                    placeholder="you@example.com"
                    className="pl-10 bg-gray-800/50 border-gray-700/50 text-slate-100 placeholder:text-slate-500 h-11"
                    value={formData.email}
                    onChange={handleChange}
                    required
                  />
                </div>
              </div>
              <div className="text-spacing-sm">
                <Label
                  htmlFor="password"
                  className="text-slate-200 text-sm font-medium"
                >
                  Password
                </Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                  <Input
                    id="password"
                    name="password1"
                    type="password"
                    placeholder="••••••••"
                    className="pl-10 bg-gray-800/50 border-gray-700/50 text-slate-100 placeholder:text-slate-500 h-11"
                    value={formData.password1}
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
                  htmlFor="confirmPassword"
                  className="text-slate-200 text-sm font-medium"
                >
                  Confirm Password
                </Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                  <Input
                    id="confirmPassword"
                    name="password2"
                    type="password"
                    placeholder="••••••••"
                    className="pl-10 bg-gray-800/50 border-gray-700/50 text-slate-100 placeholder:text-slate-500 h-11"
                    value={formData.password2}
                    onChange={handleChange}
                    required
                  />
                </div>
              </div>
              <div className="flex items-start space-x-3 py-2">
                <Checkbox
                  id="terms"
                  checked={agreeToTerms}
                  onCheckedChange={setAgreeToTerms}
                  className="border-gray-600 data-[state=checked]:bg-indigo-500 data-[state=checked]:text-white mt-0.5"
                />
                <Label
                  htmlFor="terms"
                  className="text-sm text-slate-300 leading-relaxed"
                >
                  I agree to the{" "}
                  <Link
                    to="#"
                    className="underline text-indigo-400 hover:text-indigo-300"
                  >
                    Terms of Service
                  </Link>{" "}
                  and{" "}
                  <Link
                    to="#"
                    className="underline text-indigo-400 hover:text-indigo-300"
                  >
                    Privacy Policy
                  </Link>
                  .
                </Label>
              </div>

              {error && (
                <div className="mb-4 p-3 bg-red-900/50 border border-red-800 rounded-lg text-red-300 text-sm">
                  {error.detail}
                </div>
              )}

              <Button
                type="submit"
                disabled={isLoading || !agreeToTerms}
                className="w-full bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white shadow-[0_8px_32px_rgba(99,102,241,0.3)] h-11 mt-6 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? "Creating Account..." : "Create Account"}
              </Button>
            </form>
            <div className="text-center text-sm text-slate-400 pt-4 border-t border-gray-800/50">
              Already have an account?{" "}
              <Link
                to="/login"
                className="underline text-indigo-400 hover:text-indigo-300 font-medium"
              >
                Log In
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

      <EmailVerificationModal
        isOpen={isEmailModalOpen}
        onClose={handleEmailVerificationComplete}
        email={registeredEmail}
      />
    </div>
  );
}
