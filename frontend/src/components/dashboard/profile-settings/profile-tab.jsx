import { useState, useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
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
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import {
  Twitter,
  Linkedin,
  Github,
  User,
  Upload,
  CheckCircle,
  AlertCircle,
  Loader2,
} from "lucide-react";
import api from "@/services/api";
import { updateUser } from "@/store/authSlice";
import axios from "axios";

export default function ProfileTab() {
  const { user } = useSelector((state) => state.auth);
  const dispatch = useDispatch();

  const [formData, setFormData] = useState({
    first_name: "",
    last_name: "",
    username: "",
    email: "",
    bio: "",
    twitter_url: "",
    linkedin_url: "",
    github_url: "",
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
        twitter_url: user.profile?.twitter_url || "",
        linkedin_url: user.profile?.linkedin_url || "",
        github_url: user.profile?.github_url || "",
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

  // Add this function in your component file
  async function uploadToCloudinary(file) {
    const data = new FormData();
    data.append("file", file);
    data.append("upload_preset", import.meta.env.VITE_CLOUDINARY_UPLOAD_PRESET); // Set this in Cloudinary settings

    const res = await axios.post(
      `https://api.cloudinary.com/v1_1/${
        import.meta.env.VITE_CLOUDINARY_CLOUD_NAME
      }/image/upload`,
      data
    );
    const image = await res.data;
    return image.secure_url;
  }

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
        try {
          // submitData.append("avatar", formData.avatar);
          const url = await uploadToCloudinary(formData.newAvatar);
          submitData.append("avatar", url);
        } catch (err) {
          setMessage("Failed to upload avatar.");
        }
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
    <Card className="bg-gray-900/50 border border-gray-800/50 rounded-xl p-4 sm:p-6">
      <CardHeader className="mb-4 sm:mb-6 px-0 pt-0">
        <CardTitle className="text-xl sm:text-2xl font-bold text-slate-100">
          Profile Information
        </CardTitle>
        <CardDescription className="text-slate-400 text-sm sm:text-base">
          Manage your personal and public-facing details.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-6 sm:space-y-8 px-0 pb-0">
        {/* Message Display */}
        {message && (
          <div
            className={`p-3 rounded-lg border ${
              message.type === "success"
                ? "bg-green-900/50 border-green-800 text-green-300"
                : "bg-red-900/50 border-red-800 text-red-300"
            } flex items-center gap-2 text-sm`}
          >
            {message.type === "success" ? (
              <CheckCircle className="h-4 w-4" />
            ) : (
              <AlertCircle className="h-4 w-4" />
            )}
            {message.text}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6 sm:space-y-8">
          {/* Avatar Section */}
          <div className="space-y-4 sm:space-y-6">
            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
              <Avatar className="w-20 h-20 sm:w-24 sm:h-24 border border-gray-700">
                <AvatarImage
                  src={
                    avatarPreview ||
                    "/placeholder.svg?height=96&width=96&text=Avatar"
                  }
                  alt="User Avatar"
                  className="object-cover"
                />
                <AvatarFallback className="bg-gray-800 text-slate-300">
                  <User className="h-8 w-8 sm:h-10 sm:w-10" />
                </AvatarFallback>
              </Avatar>
              <div className="space-y-2">
                <Label htmlFor="avatar-upload" className="cursor-pointer">
                  <Button
                    type="button"
                    variant="outline"
                    className="bg-gray-800/50 border-gray-700/50 text-slate-200 hover:bg-gray-700/50 text-sm"
                    asChild
                  >
                    <span>
                      <Upload className="h-4 w-4 mr-2" />
                      Change Avatar
                    </span>
                  </Button>
                </Label>
                <Input
                  id="avatar-upload"
                  type="file"
                  accept="image/*"
                  onChange={handleAvatarChange}
                  className="hidden"
                />
                {getFieldError("avatar") && (
                  <p className="text-red-400 text-xs">
                    {getFieldError("avatar")}
                  </p>
                )}
              </div>
              <Button
                type="button"
                variant="destructive"
                className="mt-2"
                onClick={handleRemoveAvatar}
                disabled={isLoading}
              >
                Remove Avatar
              </Button>
            </div>
          </div>

          {/* Basic Information */}
          <div className="grid gap-4 sm:gap-6 sm:grid-cols-2">
            <div className="space-y-2">
              <Label
                htmlFor="first_name"
                className="text-slate-200 text-sm sm:text-base"
              >
                First Name
              </Label>
              <Input
                id="first_name"
                name="first_name"
                value={formData.first_name}
                onChange={handleInputChange}
                className="bg-gray-800/50 border-gray-700/50 text-slate-100 placeholder:text-slate-500"
                placeholder="Enter your first name"
              />
              {getFieldError("first_name") && (
                <p className="text-red-400 text-xs">
                  {getFieldError("first_name")}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label
                htmlFor="last_name"
                className="text-slate-200 text-sm sm:text-base"
              >
                Last Name
              </Label>
              <Input
                id="last_name"
                name="last_name"
                value={formData.last_name}
                onChange={handleInputChange}
                className="bg-gray-800/50 border-gray-700/50 text-slate-100 placeholder:text-slate-500"
                placeholder="Enter your last name"
              />
              {getFieldError("last_name") && (
                <p className="text-red-400 text-xs">
                  {getFieldError("last_name")}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label
                htmlFor="username"
                className="text-slate-200 text-sm sm:text-base"
              >
                Username
              </Label>
              <Input
                id="username"
                name="username"
                value={formData.username}
                onChange={handleInputChange}
                className="bg-gray-800/50 border-gray-700/50 text-slate-100 placeholder:text-slate-500"
                placeholder="Enter your username"
              />
              {getFieldError("username") && (
                <p className="text-red-400 text-xs">
                  {getFieldError("username")}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label
                htmlFor="email"
                className="text-slate-200 text-sm sm:text-base"
              >
                Email
              </Label>
              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-2">
                <Input
                  id="email"
                  name="email"
                  type="email"
                  value={formData.email}
                  onChange={handleInputChange}
                  disabled
                  className="bg-gray-800/50 border-gray-700/50 text-slate-100 placeholder:text-slate-500 disabled:opacity-100 flex-1"
                />
                {user?.is_email_verified ? (
                  <Badge className="bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-xs sm:text-sm shrink-0">
                    Verified
                  </Badge>
                ) : (
                  <Badge className="bg-orange-500/20 text-orange-300 border border-orange-500/30 text-xs sm:text-sm shrink-0">
                    Unverified
                  </Badge>
                )}
              </div>
              {getFieldError("email") && (
                <p className="text-red-400 text-xs">{getFieldError("email")}</p>
              )}
            </div>
          </div>

          {/* Bio Section */}
          <div className="space-y-2">
            <Label
              htmlFor="bio"
              className="text-slate-200 text-sm sm:text-base"
            >
              Bio
            </Label>
            <Textarea
              id="bio"
              name="bio"
              value={formData.bio}
              onChange={handleInputChange}
              placeholder="Tell us about yourself..."
              className="min-h-[80px] sm:min-h-[100px] bg-gray-800/50 border-gray-700/50 text-slate-100 placeholder:text-slate-500 text-sm sm:text-base"
            />
            {getFieldError("bio") && (
              <p className="text-red-400 text-xs">{getFieldError("bio")}</p>
            )}
          </div>

          {/* Social Links */}
          <div className="space-y-4 sm:space-y-6">
            <h3 className="text-lg sm:text-xl font-bold text-slate-100">
              Social Links
            </h3>
            <div className="grid gap-4 sm:gap-6 lg:grid-cols-2 xl:grid-cols-3">
              <div className="space-y-2">
                <Label
                  htmlFor="twitter_url"
                  className="text-slate-200 text-sm sm:text-base"
                >
                  Twitter
                </Label>
                <div className="relative">
                  <Twitter className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                  <Input
                    id="twitter_url"
                    name="twitter_url"
                    value={formData.twitter_url}
                    onChange={handleInputChange}
                    placeholder="https://twitter.com/yourhandle"
                    className="pl-10 bg-gray-800/50 border-gray-700/50 text-slate-100 placeholder:text-slate-500 text-sm sm:text-base"
                  />
                </div>
                {getFieldError("twitter_url") && (
                  <p className="text-red-400 text-xs">
                    {getFieldError("twitter_url")}
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label
                  htmlFor="linkedin_url"
                  className="text-slate-200 text-sm sm:text-base"
                >
                  LinkedIn
                </Label>
                <div className="relative">
                  <Linkedin className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                  <Input
                    id="linkedin_url"
                    name="linkedin_url"
                    value={formData.linkedin_url}
                    onChange={handleInputChange}
                    placeholder="https://linkedin.com/in/yourprofile"
                    className="pl-10 bg-gray-800/50 border-gray-700/50 text-slate-100 placeholder:text-slate-500 text-sm sm:text-base"
                  />
                </div>
                {getFieldError("linkedin_url") && (
                  <p className="text-red-400 text-xs">
                    {getFieldError("linkedin_url")}
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label
                  htmlFor="github_url"
                  className="text-slate-200 text-sm sm:text-base"
                >
                  GitHub
                </Label>
                <div className="relative">
                  <Github className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                  <Input
                    id="github_url"
                    name="github_url"
                    value={formData.github_url}
                    onChange={handleInputChange}
                    placeholder="https://github.com/yourusername"
                    className="pl-10 bg-gray-800/50 border-gray-700/50 text-slate-100 placeholder:text-slate-500 text-sm sm:text-base"
                  />
                </div>
                {getFieldError("github_url") && (
                  <p className="text-red-400 text-xs">
                    {getFieldError("github_url")}
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Submit Button */}
          <div className="flex flex-col sm:flex-row justify-end gap-3 pt-4 border-t border-gray-800/50">
            <Button
              type="submit"
              disabled={isLoading}
              className="bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white shadow-[0_8px_32px_rgba(99,102,241,0.3)] rounded-xl border-0 w-full sm:w-auto px-6 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Saving Changes...
                </>
              ) : (
                "Save Changes"
              )}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
