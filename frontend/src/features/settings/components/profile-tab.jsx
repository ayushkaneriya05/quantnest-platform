import { getApiErrorDetails, getApiErrorMessage } from "@/shared/utils/apiErrors";
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
import ThemeSwitch from "@/shared/components/ThemeSwitch";
import { User, Upload, CheckCircle, AlertCircle, Loader2 } from "lucide-react";
import api from "@/shared/services/api";
import { updateUser } from "@/shared/store/authSlice";

export default function ProfileTab() {
  const { user } = useSelector((state) => state.auth);
  const dispatch = useDispatch();

  const [formData, setFormData] = useState({
    first_name: "",
    last_name: "",
    username: "",
    email: "",
    bio: "",
  });

  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [errors, setErrors] = useState({});
  const [avatarPreview, setAvatarPreview] = useState(null);
  const [avatarFile, setAvatarFile] = useState(null);
  const [removeAvatar, setRemoveAvatar] = useState(false);

  // Load user data on component mount
  useEffect(() => {
    if (user) {
      setFormData({
        first_name: user.first_name || "",
        last_name: user.last_name || "",
        username: user.username || "",
        email: user.email || "",
        bio: user.bio || "",
      });
      setAvatarFile(null);
      setRemoveAvatar(false);
    }
  }, [user]);

  useEffect(() => {
    const preview = avatarFile ? URL.createObjectURL(avatarFile) : null;
    setAvatarPreview(preview || (removeAvatar ? null : user?.avatar));
    return () => { if (preview) URL.revokeObjectURL(preview); };
  }, [avatarFile, removeAvatar, user?.avatar]);

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

  const handleAvatarChange = (e) => {
    const file = e.target.files[0];
    e.target.value = "";
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

    setAvatarFile(file);
    setRemoveAvatar(false);

    // Clear avatar error
    if (errors.avatar) {
      setErrors((prev) => ({
        ...prev,
        avatar: null,
      }));
    }
  };
  const handleRemoveAvatar = () => {
    if (!avatarPreview) return;
    setMessage(null);
    setAvatarFile(null);
    setRemoveAvatar(true);
    setErrors((prev) => ({ ...prev, avatar: null }));
  };


  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setMessage(null);
    setErrors({});

    try {
      const submitData = new FormData();

      // Add text fields
      for (const key of ["first_name", "last_name", "username", "bio"]) {
        submitData.append(key, formData[key]);
      }

      // Add avatar if selected
      if (avatarFile) {
        submitData.append("avatar", avatarFile);
      } else if (removeAvatar) {
        submitData.append("avatar", "");
      }

      const response = await api.patch("/users/profile/", submitData);

      // Update Redux store with new user data
      dispatch(updateUser(response.data));

      setMessage({
        type: "success",
        text: "Profile updated successfully!",
      });

    } catch (err) {
      console.error("Profile update error:", err);

      if (err.response?.data) {
        const serverErrors = getApiErrorDetails(err);
        if (Object.keys(serverErrors).length) {
          setErrors(serverErrors);
        } else {
          setMessage({ type: "error", text: getApiErrorMessage(err, "Failed to update profile") });
        }
      } else {
        setMessage({
          type: "error",
          text: getApiErrorMessage(err, "Network error. Please try again."),
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
              ? "bg-green-50 dark:bg-green-900/40 border-green-800/50 text-green-700 dark:text-green-300"
              : "bg-red-50 dark:bg-red-900/40 border-red-800/50 text-red-700 dark:text-red-300"
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
          <Card className="bg-card/50 border-border/50 overflow-hidden">
            <CardHeader className="border-b border-border/50 pb-4">
              <CardTitle className="text-lg font-semibold text-foreground">Avatar</CardTitle>
            </CardHeader>
            <CardContent className="pt-6 flex flex-col items-center text-center">
              <div className="relative group">
                <Avatar className="w-32 h-32 border-2 border-indigo-500/30 group-hover:border-indigo-500 transition-colors duration-300">
                  {avatarPreview && <AvatarImage src={avatarPreview} alt="Profile picture" className="object-cover" />}
                  <AvatarFallback className="bg-secondary text-foreground">
                    <User className="h-12 w-12" />
                  </AvatarFallback>
                </Avatar>
                <Label
                  htmlFor="avatar-upload"
                  className="absolute bottom-0 right-0 p-2 bg-indigo-600 text-white rounded-full cursor-pointer shadow-lg hover:bg-indigo-700 transition-transform active:scale-95 border-2 border-border"
                >
                  <Upload className="h-4 w-4" />
                  <Input id="avatar-upload" type="file" accept="image/*" onChange={handleAvatarChange} className="hidden" />
                </Label>
              </div>
              <div className="mt-4 space-y-2">
                <h3 className="font-bold text-foreground">{formData.first_name || "New"}{" "}{formData.last_name || "User"}</h3>
                <p className="text-sm text-muted-foreground">@{formData.username || "username"}</p>
                {getFieldError("avatar") && <p className="text-red-700 dark:text-red-400 text-xs mt-2">{getFieldError("avatar")}</p>}
                <div className="pt-4">
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={handleRemoveAvatar}
                    disabled={isLoading || !avatarPreview}
                    className="text-xs text-red-700 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300 hover:bg-red-900/20"
                  >
                    Remove Profile Picture
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-card/50 border-border/50">
            <CardContent className="p-6 space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Account Type</span>
                <Badge variant="outline" className="bg-indigo-500/10 text-indigo-700 dark:text-indigo-300 border-indigo-500/20">Starter</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Member Since</span>
                <span className="text-sm text-foreground">Apr 2024</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Verified</span>
                {user?.is_email_verified ? (
                  <CheckCircle className="h-4 w-4 text-emerald-700 dark:text-emerald-400" />
                ) : (
                  <AlertCircle className="h-4 w-4 text-orange-700 dark:text-orange-400" />
                )}
              </div>
            </CardContent>
          </Card>

          <Card className="bg-card/50 border-border/50">
            <CardHeader>
              <CardTitle className="text-lg font-semibold text-foreground">Appearance</CardTitle>
              <CardDescription>Choose Light, Dark, or follow your device settings.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <span className="text-sm font-medium">Theme</span>
                <ThemeSwitch showLabel />
              </div>
              <p className="text-xs text-muted-foreground">Applied immediately and saved on this device.</p>
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Form Fields */}
        <div className="lg:col-span-8 space-y-6">
          <Card className="bg-card/50 border-border/50">
            <CardHeader className="border-b border-border/50">
              <CardTitle className="text-lg font-semibold text-foreground">Basic Information</CardTitle>
              <CardDescription className="text-muted-foreground">Your first and last names will be used for official communications.</CardDescription>
            </CardHeader>
            <CardContent className="p-6 space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label htmlFor="first_name" className="text-foreground">First Name</Label>
                  <Input
                    id="first_name"
                    name="first_name"
                    value={formData.first_name}
                    onChange={handleInputChange}
                    className="bg-secondary/40 border-border/50 focus:border-indigo-500/50 text-foreground"
                    placeholder="John"
                  />
                  {getFieldError("first_name") && <p className="text-red-700 dark:text-red-400 text-xs">{getFieldError("first_name")}</p>}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="last_name" className="text-foreground">Last Name</Label>
                  <Input
                    id="last_name"
                    name="last_name"
                    value={formData.last_name}
                    onChange={handleInputChange}
                    className="bg-secondary/40 border-border/50 focus:border-indigo-500/50 text-foreground"
                    placeholder="Doe"
                  />
                  {getFieldError("last_name") && <p className="text-red-700 dark:text-red-400 text-xs">{getFieldError("last_name")}</p>}
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label htmlFor="username" className="text-foreground">Username</Label>
                  <Input
                    id="username"
                    name="username"
                    value={formData.username}
                    onChange={handleInputChange}
                    className="bg-secondary/40 border-border/50 focus:border-indigo-500/50 text-foreground"
                    placeholder="johndoe"
                  />
                  {getFieldError("username") && <p className="text-red-700 dark:text-red-400 text-xs">{getFieldError("username")}</p>}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email" className="text-foreground">Email Address</Label>
                  <Input
                    id="email"
                    name="email"
                    value={formData.email}
                    disabled
                    className="bg-secondary/20 border-border/30 text-muted-foreground opacity-80"
                  />
                  <p className="text-[10px] text-muted-foreground italic">Contact support to change your verified email.</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-card/50 border-border/50">
            <CardHeader className="border-b border-border/50">
              <CardTitle className="text-lg font-semibold text-foreground">Biography</CardTitle>
              <CardDescription className="text-muted-foreground">A brief description for your personal profile.</CardDescription>
            </CardHeader>
            <CardContent className="p-6">
              <div className="space-y-2">
                <Textarea
                  id="bio"
                  name="bio"
                  value={formData.bio}
                  onChange={handleInputChange}
                  placeholder="Tell us about your trading journey..."
                  className="min-h-[150px] bg-secondary/40 border-border/50 focus:border-indigo-500/50 text-foreground resize-none"
                />
                {getFieldError("bio") && <p className="text-red-700 dark:text-red-400 text-xs">{getFieldError("bio")}</p>}
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
