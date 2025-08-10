import { createContext, useContext, useState, useEffect } from 'react'

const SidebarContext = createContext(undefined)

export function SidebarProvider({ children }) {
  const [isOpen, setIsOpen] = useState(false)

  // Set default state based on screen size
  useEffect(() => {
    const checkScreenSize = () => {
      setIsOpen(window.innerWidth >= 1024) // Open on desktop (lg breakpoint)
    }

    checkScreenSize()
    window.addEventListener('resize', checkScreenSize)
    return () => window.removeEventListener('resize', checkScreenSize)
  }, [])

  const toggle = () => setIsOpen(prev => !prev)
  const close = () => setIsOpen(false)
  const open = () => setIsOpen(true)

  return (
    <SidebarContext.Provider value={{ isOpen, toggle, close, open }}>
      {children}
    </SidebarContext.Provider>
  )
}

export function useSidebar() {
  const context = useContext(SidebarContext)
  if (context === undefined) {
    throw new Error('useSidebar must be used within a SidebarProvider')
  }
  return context
}
