import { useState, useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import { Button } from "@/shared/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import { Textarea } from "@/shared/components/ui/textarea";
import { Badge } from "@/shared/components/ui/badge";
import { Avatar, AvatarImage, AvatarFallback } from "@/shared/components/ui/avatar";
import { User, Upload, CheckCircle, AlertCircle, Loader2 } from "lucide-react";
import api from "@/shared/services/api";
import { updateUser } from "@/shared/store/authSlice";
import React from "react";

export default function ProfileTab() {
  const { user } = useSelector((state) => state.auth);
  const dispatch = useDispatch();

  const [formData, setFormData] = useState({
    first_name: "",
    last_name: "",
    username: "",
    email: "",
    bio: "",
    avatar: "",
    newAvatar: "",
  });

  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [errors, setErrors] = useState({});
  const [avatarPreview, setAvatarPreview] = useState(null);
  const [isUploadingAvatar, setIsUploadingAvatar] = useState(false);

  // Load user data on component mount
  useEffect(() => {
    if (user) {
      setFormData({
        first_name: user.first_name || "",
        last_name: user.last_name || "",
        username: user.username || "",
        email: user.email || "",
        bio: user.bio || "",
        avatar: user.avatar || "",
        newAvatar: user.avatar || "",
      });
      if (user.avatar) {
        setAvatarPreview(user.avatar);
      }
    }
  }, [user]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
    // Clear field-specific error when user starts typing
    if (errors[name]) {
      setErrors((prev) => ({
        ...prev,
        [name]: null,
      }));
    }
  };

  const handleAvatarChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Validate file type and size
    const allowedTypes = ["image/jpeg", "image/png", "image/webp"];
    if (!allowedTypes.includes(file.type)) {
      setErrors((prev) => ({
        ...prev,
        avatar: "Please select a valid image file (JPEG, PNG, or WebP)",
      }));
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      // 5MB limit
      setErrors((prev) => ({
        ...prev,
        avatar: "File size must be less than 5MB",
      }));
      return;
    }

    // Create preview
    const previewUrl = URL.createObjectURL(file);
    setAvatarPreview(previewUrl);
    setFormData((prev) => ({
      ...prev,
      newAvatar: file,
    }));

    // Clear avatar error
    if (errors.avatar) {
      setErrors((prev) => ({
        ...prev,
        avatar: null,
      }));
    }
  };
  const handleRemoveAvatar = async () => {
    if (!avatarPreview) return;
    setIsLoading(true);
    setMessage(null);
    try {
      setFormData((prev) => ({
        ...prev,
        newAvatar: null,
      }));

      // Clear avatar error
      if (errors.avatar) {
        setErrors((prev) => ({
          ...prev,
          avatar: null,
        }));
      }
      setAvatarPreview(null);
    } catch (err) {
      setMessage({ type: "error", text: "Failed to remove avatar." });
    } finally {
      setIsLoading(false);
    }
  };


  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setMessage(null);
    setErrors({});

    try {
      const submitData = new FormData();

      // Add text fields
      Object.keys(formData).forEach((key) => {
        if (
          key !== "avatar" &&
          formData[key] !== null &&
          formData[key] !== undefined
        ) {
          submitData.append(key, formData[key]);
        }
      });

      // Add avatar if selected
      if (formData.newAvatar) {
        submitData.append("avatar", formData.newAvatar);
      } else if (!formData.newAvatar && formData.avatar) {
        await api.post("/users/avatar/delete/");
        submitData.append("avatar", "");
      }

      const response = await api.patch("/users/profile/", submitData);

      // Update Redux store with new user data
      dispatch(updateUser(response.data));

      setMessage({
        type: "success",
        text: "Profile updated successfully!",
      });

      // Clear avatar file input
      setFormData((prev) => ({
        ...prev,
        avatar: null,
      }));
    } catch (err) {
      console.error("Profile update error:", err);

      if (err.response?.data) {
        const serverErrors = err.response.data;
        if (typeof serverErrors === "object") {
          setErrors(serverErrors);
        } else {
          setMessage({
            type: "error",
            text: serverErrors.detail || "Failed to update profile",
          });
        }
      } else {
        setMessage({
          type: "error",
          text: "Network error. Please try again.",
        });
      }
    } finally {
      setIsLoading(false);
    }
  };

  const getFieldError = (fieldName) => {
    if (errors[fieldName]) {
      if (Array.isArray(errors[fieldName])) {
        return errors[fieldName][0];
      }
      return errors[fieldName];
    }
    return null;
  };

  return (
    <div className="w-full space-y-6 max-w-full overflow-hidden pb-10">
      {/* Dynamic Status Message - Top-level alert */}
      {message && (
        <div
          className={`flex-1 xl:flex-none px-4 py-3 rounded-2xl border ${
            message.type === "success"
              ? "bg-green-900/40 border-green-800/50 text-green-300"
              : "bg-red-900/40 border-red-800/50 text-red-300"
          } flex items-center gap-3 text-sm animate-in fade-in slide-in-from-top-4 duration-300 shadow-lg mb-2`}
        >
          {message.type === "success" ? (
            <CheckCircle className="h-5 w-5 shrink-0" />
          ) : (
            <AlertCircle className="h-5 w-5 shrink-0" />
          )}
          <span className="font-medium">{message.text}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start pb-10">
        {/* Left Column: Avatar & Quick Info (Sticky on Desktop) */}
        <div className="lg:col-span-4 space-y-6 lg:sticky lg:top-6">
          <Card className="bg-gray-900/50 border-gray-800/50 overflow-hidden">
            <CardHeader className="border-b border-gray-800/50 pb-4">
              <CardTitle className="text-lg font-semibold text-slate-200">Avatar</CardTitle>
            </CardHeader>
            <CardContent className="pt-6 flex flex-col items-center text-center">
              <div className="relative group">
                <Avatar className="w-32 h-32 border-2 border-indigo-500/30 group-hover:border-indigo-500 transition-colors duration-300">
                  <AvatarImage
                    src={avatarPreview || "/placeholder.svg?height=128&width=128&text=Avatar"}
                    className="object-cover"
                  />
                  <AvatarFallback className="bg-gray-800 text-slate-300">
                    <User className="h-12 w-12" />
                  </AvatarFallback>
                </Avatar>
                <Label
                  htmlFor="avatar-upload"
                  className="absolute bottom-0 right-0 p-2 bg-indigo-600 rounded-full cursor-pointer shadow-lg hover:bg-indigo-700 transition-transform active:scale-95 border-2 border-gray-900"
                >
                  <Upload className="h-4 w-4 text-white" />
                  <Input id="avatar-upload" type="file" accept="image/*" onChange={handleAvatarChange} className="hidden" />
                </Label>
              </div>
              <div className="mt-4 space-y-2">
                <h3 className="font-bold text-slate-100">{formData.first_name || "New"}{" "}{formData.last_name || "User"}</h3>
                <p className="text-sm text-slate-400">@{formData.username || "username"}</p>
                {getFieldError("avatar") && <p className="text-red-400 text-xs mt-2">{getFieldError("avatar")}</p>}
                <div className="pt-4">
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={handleRemoveAvatar}
                    disabled={isLoading || !avatarPreview}
                    className="text-xs text-red-400 hover:text-red-300 hover:bg-red-900/20"
                  >
                    Remove Profile Picture
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gray-900/50 border-gray-800/50">
            <CardContent className="p-6 space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-400">Account Type</span>
                <Badge variant="outline" className="bg-indigo-500/10 text-indigo-300 border-indigo-500/20">Starter</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-400">Member Since</span>
                <span className="text-sm text-slate-200">Apr 2024</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-400">Verified</span>
                {user?.is_email_verified ? (
                  <CheckCircle className="h-4 w-4 text-emerald-400" />
                ) : (
                  <AlertCircle className="h-4 w-4 text-orange-400" />
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Form Fields */}
        <div className="lg:col-span-8 space-y-6">
          <Card className="bg-gray-900/50 border-gray-800/50">
            <CardHeader className="border-b border-gray-800/50">
              <CardTitle className="text-lg font-semibold text-slate-200">Basic Information</CardTitle>
              <CardDescription className="text-slate-400">Your first and last names will be used for official communications.</CardDescription>
            </CardHeader>
            <CardContent className="p-6 space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label htmlFor="first_name" className="text-slate-300">First Name</Label>
                  <Input
                    id="first_name"
                    name="first_name"
                    value={formData.first_name}
                    onChange={handleInputChange}
                    className="bg-gray-800/40 border-gray-700/50 focus:border-indigo-500/50 text-slate-100"
                    placeholder="John"
                  />
                  {getFieldError("first_name") && <p className="text-red-400 text-xs">{getFieldError("first_name")}</p>}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="last_name" className="text-slate-300">Last Name</Label>
                  <Input
                    id="last_name"
                    name="last_name"
                    value={formData.last_name}
                    onChange={handleInputChange}
                    className="bg-gray-800/40 border-gray-700/50 focus:border-indigo-500/50 text-slate-100"
                    placeholder="Doe"
                  />
                  {getFieldError("last_name") && <p className="text-red-400 text-xs">{getFieldError("last_name")}</p>}
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label htmlFor="username" className="text-slate-300">Username</Label>
                  <Input
                    id="username"
                    name="username"
                    value={formData.username}
                    onChange={handleInputChange}
                    className="bg-gray-800/40 border-gray-700/50 focus:border-indigo-500/50 text-slate-100"
                    placeholder="johndoe"
                  />
                  {getFieldError("username") && <p className="text-red-400 text-xs">{getFieldError("username")}</p>}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email" className="text-slate-300">Email Address</Label>
                  <Input
                    id="email"
                    name="email"
                    value={formData.email}
                    disabled
                    className="bg-gray-800/20 border-gray-700/30 text-slate-500 opacity-80"
                  />
                  <p className="text-[10px] text-slate-500 italic">Contact support to change your verified email.</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gray-900/50 border-gray-800/50">
            <CardHeader className="border-b border-gray-800/50">
              <CardTitle className="text-lg font-semibold text-slate-200">Biography</CardTitle>
              <CardDescription className="text-slate-400">A brief description about yourself to share with the community.</CardDescription>
            </CardHeader>
            <CardContent className="p-6">
              <div className="space-y-2">
                <Textarea
                  id="bio"
                  name="bio"
                  value={formData.bio}
                  onChange={handleInputChange}
                  placeholder="Tell us about your trading journey..."
                  className="min-h-[150px] bg-gray-800/40 border-gray-700/50 focus:border-indigo-500/50 text-slate-100 resize-none"
                />
                {getFieldError("bio") && <p className="text-red-400 text-xs">{getFieldError("bio")}</p>}
              </div>
            </CardContent>
          </Card>

          <div className="flex justify-end pt-4">
            <Button
              type="submit"
              disabled={isLoading}
              className="bg-indigo-600 hover:bg-indigo-700 text-white min-w-[160px] h-12 rounded-xl border-0 shadow-lg shadow-indigo-500/20 active:scale-95 transition-all"
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Saving Changes
                </>
              ) : (
                "Save Changes"
              )}
            </Button>
          </div>
        </div>
      </form>
    </div>
  );
}
