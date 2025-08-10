import { Link, useNavigate } from "react-router-dom"
import { useSelector, useDispatch } from 'react-redux'
import { logout, logoutUser } from '@/store/authSlice'
import { Button } from "@/components/ui/button"
import { TrendingUp, User, LogOut } from 'lucide-react'

export default function MainHeader() {
  const { accessToken, user } = useSelector((state) => state.auth)
  const dispatch = useDispatch()
  const navigate = useNavigate()

  const scrollToSection = (sectionId) => {
    const element = document.getElementById(sectionId)
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' })
    }
  }

  const handleLogout = async () => {
    try {
      dispatch(logoutUser())
    } catch (error) {
      console.error('Logout failed', error)
    } finally {
      dispatch(logout())
      navigate('/')
    }
  }

  return (
    <header className="sticky top-0 z-50 w-full border-b border-gray-800 bg-black/80 backdrop-blur-xl">
      <div className="container flex h-14 sm:h-16 items-center px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
        <div className="mr-4 flex items-center">
          <Link to="/" className="mr-4 sm:mr-6 flex items-center space-x-2">
            <div className="flex h-8 w-8 sm:h-9 sm:w-9 md:h-10 md:w-10 items-center justify-center rounded-xl sm:rounded-2xl bg-gradient-to-br from-indigo-500/20 to-purple-600/20 shadow-[inset_0_2px_4px_rgba(255,255,255,0.1),inset_0_-2px_4px_rgba(0,0,0,0.2)] border border-gray-700/50">
              <TrendingUp className="h-4 w-4 sm:h-5 sm:w-5 text-indigo-300" />
            </div>
            <span className="hidden font-bold sm:inline-block text-lg sm:text-xl text-slate-100 font-heading">QuantNest</span>
          </Link>
          <nav className="hidden md:flex items-center space-x-4 lg:space-x-6 xl:space-x-8 text-sm font-medium">
            <button 
              onClick={() => scrollToSection('features')} 
              className="transition-colors hover:text-indigo-300 text-slate-300 py-2"
            >
              Features
            </button>
            <button 
              onClick={() => scrollToSection('pricing')} 
              className="transition-colors hover:text-indigo-300 text-slate-300 py-2"
            >
              Pricing
            </button>
            <button 
              onClick={() => scrollToSection('about')} 
              className="transition-colors hover:text-indigo-300 text-slate-300 py-2"
            >
              About
            </button>
            <button 
              onClick={() => scrollToSection('contact')} 
              className="transition-colors hover:text-indigo-300 text-slate-300 py-2"
            >
              Contact
            </button>
          </nav>
        </div>
        <div className="flex flex-1 items-center justify-end space-x-2 sm:space-x-3">
          {accessToken ? (
            <>
              <Button
                asChild
                variant="ghost"
                size="sm"
                className="text-slate-300 hover:text-slate-100 hover:bg-slate-800/50 rounded-lg px-3 py-1.5 sm:px-4 sm:py-2 text-sm flex items-center gap-1"
              >
                <Link to="/dashboard">
                  <User className="h-4 w-4" />
                  <span className="hidden sm:inline">{user?.username || 'Dashboard'}</span>
                  <span className="sm:hidden">Dashboard</span>
                </Link>
              </Button>
              <Button
                onClick={handleLogout}
                variant="ghost"
                size="sm"
                className="text-slate-300 hover:text-slate-100 hover:bg-slate-800/50 rounded-lg px-3 py-1.5 sm:px-4 sm:py-2 text-sm flex items-center gap-1"
              >
                <LogOut className="h-4 w-4" />
                <span className="hidden sm:inline">Logout</span>
              </Button>
            </>
          ) : (
            <>
              <Button
                asChild
                variant="ghost"
                size="sm"
                className="text-slate-300 hover:text-slate-100 hover:bg-slate-800/50 rounded-lg px-3 py-1.5 sm:px-4 sm:py-2 text-sm"
              >
                <Link to="/login">Sign In</Link>
              </Button>
              <Button
                asChild
                size="sm"
                className="bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white shadow-[0_8px_32px_rgba(99,102,241,0.3)] rounded-lg border-0 px-3 py-1.5 sm:px-4 sm:py-2 text-sm"
              >
                <Link to="/register">Get Started</Link>
              </Button>
            </>
          )}
        </div>
      </div>
    </header>
  )
}
