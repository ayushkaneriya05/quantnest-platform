import { Link, useNavigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import { ArrowUpRight, LogOut, Menu } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator } from "@/shared/components/ui/dropdown-menu";
import ThemeSwitch from "@/shared/components/ThemeSwitch";
import BrandLogo from "@/shared/components/BrandLogo";
import { logoutUser } from "@/shared/store/authSlice";
import { useNotifications } from "@/shared/hooks/useNotifications";

const navItems = [
  ["Product", "/product/"], ["Features", "/features/"], ["Pricing", "/pricing/"],
  ["Documentation", "/docs/"], ["Services", "/custom-development/"],
];

export default function MainHeader({ authPage }) {
  const { accessToken } = useSelector((state) => state.auth);
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { notify } = useNotifications();
  const logout = async () => {
    try { await dispatch(logoutUser()).unwrap(); navigate("/"); }
    catch (error) { notify.error(typeof error === "string" ? error : "Could not sign out. Please retry."); }
  };
  return <header className="sticky top-0 z-40 w-full border-b bg-card/95 text-foreground backdrop-blur-xl">
    <div className="mx-auto flex min-h-16 w-[calc(100%_-_2rem)] max-w-7xl items-center justify-between gap-2">
      <Link to="/" aria-label="QuantNest home" className="min-w-0 shrink"><BrandLogo animated className="w-40 sm:w-48" /></Link>
      <nav aria-label="Primary" className="hidden items-center gap-6 xl:flex">
        {navItems.map(([label,id]) => <Link key={id} to={id} className="py-3 text-sm text-muted-foreground transition-colors hover:text-brand focus-ring">{label}</Link>)}
      </nav>
      <div className="flex shrink-0 items-center gap-1 sm:gap-2">
        <ThemeSwitch />
        <div className="hidden items-center gap-2 sm:flex">
          {accessToken ? <><Button asChild variant="outline"><Link to="/overview">Open workspace<ArrowUpRight className="h-4 w-4" /></Link></Button><Button variant="ghost" size="icon" onClick={logout} aria-label="Log out"><LogOut className="h-4 w-4" /></Button></> : <>
            {authPage !== "login" && <Button asChild variant="ghost"><Link to="/login">Sign in</Link></Button>}
            {authPage !== "register" && <Button asChild className="rounded-full bg-[#e5c461] text-black hover:bg-[#f1d889]"><Link to="/register">Start building<ArrowUpRight className="h-4 w-4" /></Link></Button>}
          </>}
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild><Button variant="ghost" size="icon" className="touch-target xl:hidden" aria-label="Open navigation"><Menu className="h-5 w-5" /></Button></DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-64 max-w-[calc(100vw_-_2rem)]">
            {navItems.map(([label,id]) => <DropdownMenuItem key={id} asChild className="min-h-11"><Link to={id}>{label}</Link></DropdownMenuItem>)}
            <DropdownMenuSeparator />
            {accessToken ? <><DropdownMenuItem asChild className="min-h-11"><Link to="/overview">Open workspace</Link></DropdownMenuItem><DropdownMenuItem onSelect={logout} className="min-h-11">Log out</DropdownMenuItem></> : <><DropdownMenuItem asChild className="min-h-11"><Link to="/login">Sign in</Link></DropdownMenuItem><DropdownMenuItem asChild className="min-h-11"><Link to="/register">Create account</Link></DropdownMenuItem></>}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  </header>;
}
MainHeader.propTypes = { authPage: PropTypes.string };
