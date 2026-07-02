/* eslint-disable react/prop-types */
import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import { ArrowUpRight, LogOut, Menu, Moon, Sun, X } from "lucide-react";

import { Button } from "@/shared/components/ui/button";
import { logout, logoutUser } from "@/shared/store/authSlice";

const navItems = [
  { label: "Workflow", target: "workflow" },
  { label: "Platform", target: "platform" },
  { label: "Intelligence", target: "intelligence" },
  { label: "Ecosystem", target: "ecosystem" },
];

export default function MainHeader({
  theme = "dark",
  onThemeToggle = null,
  authPage = null,
}) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { accessToken } = useSelector((state) => state.auth);
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const isLight = theme === "light";

  const headerClass = isLight
    ? "sticky top-0 z-[100] w-full border-b border-amber-900/10 bg-[#fffaf0]/88 text-[#19140a] backdrop-blur-2xl"
    : "sticky top-0 z-[100] w-full border-b border-white/10 bg-[#050505]/90 text-white backdrop-blur-2xl";
  const navClass = isLight
    ? "text-stone-600 hover:text-[#9f7830]"
    : "text-zinc-400 hover:text-[#f1d889]";
  const ghostButtonClass = isLight
    ? "rounded-full px-5 text-stone-700 hover:bg-amber-900/5 hover:text-[#9f7830]"
    : "rounded-full px-5 text-zinc-300 hover:bg-white/5 hover:text-white";
  const iconButtonClass = isLight
    ? "rounded-full text-stone-500 hover:bg-amber-900/5 hover:text-[#9f7830]"
    : "rounded-full text-zinc-500 hover:bg-white/5 hover:text-white";

  const scrollToSection = (sectionId) => {
    setMobileOpen(false);
    document
      .getElementById(sectionId)
      ?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const handleLogout = async () => {
    try {
      await dispatch(logoutUser());
    } catch (error) {
      console.error("Logout failed", error);
    } finally {
      dispatch(logout());
      navigate("/");
    }
  };

  return (
    <header className={headerClass}>
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:h-[72px] lg:px-8">
        <Link
          to="/"
          className="group flex items-center"
          aria-label="QuantNest home"
        >
          <img
            src="/logo_1-wordmark.png"
            alt="QuantNest"
            className="h-auto w-[168px] object-contain transition-opacity duration-300 group-hover:opacity-85 sm:w-[190px]"
          />
        </Link>

        <nav className="hidden items-center gap-7 lg:flex" aria-label="Primary">
          {navItems.map((item) => (
            <button
              key={item.target}
              type="button"
              onClick={() => scrollToSection(item.target)}
              className={`text-sm font-medium transition-colors ${navClass}`}
            >
              {item.label}
            </button>
          ))}
        </nav>

        <div className="hidden items-center gap-2 sm:flex">
          {onThemeToggle && (
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={onThemeToggle}
              className={iconButtonClass}
              aria-label={`Switch to ${isLight ? "dark" : "light"} theme`}
            >
              {isLight ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
            </Button>
          )}
          {accessToken ? (
            <>
              <Button
                asChild
                variant="ghost"
                className={ghostButtonClass}
              >
                <Link to="/dashboard">
                  Open dashboard
                  <ArrowUpRight className="h-4 w-4" />
                </Link>
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={handleLogout}
                className={iconButtonClass}
                aria-label="Log out"
              >
                <LogOut className="h-4 w-4" />
              </Button>
            </>
          ) : (
            <>
              {authPage !== "login" && (
                <Button
                  asChild
                  variant="ghost"
                  className={ghostButtonClass}
                >
                  <Link to="/login">Sign in</Link>
                </Button>
              )}
              {authPage !== "register" && (
                <Button
                  asChild
                  className="h-10 rounded-full border border-[#e5c461]/40 bg-[#e5c461] px-5 font-semibold text-black shadow-[0_0_30px_rgba(229,196,97,0.16)] hover:bg-[#f1d889]"
                >
                  <Link to="/register">
                    Start building
                    <ArrowUpRight className="h-4 w-4" />
                  </Link>
                </Button>
              )}
            </>
          )}
        </div>

        <button
          type="button"
          onClick={() => setMobileOpen((open) => !open)}
          className={`flex h-10 w-10 items-center justify-center rounded-full transition-colors sm:hidden ${
            isLight
              ? "border border-amber-900/15 text-stone-600 hover:border-[#d8b557]/50 hover:text-[#9f7830]"
              : "border border-white/10 text-zinc-300 hover:border-[#e5c461]/40 hover:text-[#f1d889]"
          }`}
          aria-expanded={mobileOpen}
          aria-label="Toggle navigation"
        >
          {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {mobileOpen && (
        <div
          className={`border-t px-4 py-4 sm:hidden ${
            isLight
              ? "border-amber-900/10 bg-[#fffaf0]"
              : "border-white/10 bg-[#080808]"
          }`}
        >
          <nav className="mx-auto flex max-w-7xl flex-col gap-1" aria-label="Mobile">
            {navItems.map((item) => (
              <button
                key={item.target}
                type="button"
                onClick={() => scrollToSection(item.target)}
                className={`rounded-xl px-3 py-3 text-left text-sm font-medium transition-colors ${
                  isLight
                    ? "text-stone-700 hover:bg-amber-900/5 hover:text-[#9f7830]"
                    : "text-zinc-300 hover:bg-white/5 hover:text-[#f1d889]"
                }`}
              >
                {item.label}
              </button>
            ))}
            <div
              className={`mt-3 grid grid-cols-2 gap-2 border-t pt-4 ${
                isLight ? "border-amber-900/10" : "border-white/10"
              }`}
            >
              {onThemeToggle && (
                <Button
                  type="button"
                  variant="outline"
                  onClick={onThemeToggle}
                  className={`col-span-2 rounded-full ${
                    isLight
                      ? "border-amber-900/15 bg-white text-stone-800"
                      : "border-white/10 bg-white/5 text-white"
                  }`}
                >
                  {isLight ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
                  {isLight ? "Dark theme" : "Light theme"}
                </Button>
              )}
              {accessToken ? (
                <>
                  <Button asChild variant="outline" className="rounded-full border-white/10 bg-white/5 text-white">
                    <Link to="/dashboard">Dashboard</Link>
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={handleLogout}
                    className="rounded-full text-zinc-300"
                  >
                    Log out
                  </Button>
                </>
              ) : (
                <>
                  {authPage !== "login" && (
                    <Button asChild variant="outline" className="rounded-full border-white/10 bg-white/5 text-white">
                      <Link to="/login">Sign in</Link>
                    </Button>
                  )}
                  {authPage !== "register" && (
                    <Button asChild className="rounded-full bg-[#e5c461] text-black hover:bg-[#f1d889]">
                      <Link to="/register">Get started</Link>
                    </Button>
                  )}
                </>
              )}
            </div>
          </nav>
        </div>
      )}
    </header>
  );
}
