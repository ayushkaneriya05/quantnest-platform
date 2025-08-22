import React, { useRef, useEffect, useState } from 'react'
import { cn } from '@/lib/utils'

/**
 * InteractiveButton component with advanced hover effects
 * @param {Object} props - Component props
 * @param {React.ReactNode} props.children - Button content
 * @param {string} props.variant - Button variant ('glow', 'lift', 'ripple', 'magnetic', 'morph')
 * @param {string} props.className - Additional CSS classes
 * @param {Function} props.onClick - Click handler
 * @returns {JSX.Element} Interactive button component
 */
export const InteractiveButton = ({
  children,
  variant = 'glow',
  className = '',
  onClick,
  ...props
}) => {
  const buttonRef = useRef(null)
  const [isPressed, setIsPressed] = useState(false)
  const [ripples, setRipples] = useState([])

  const handleClick = (e) => {
    if (variant === 'ripple') {
      const rect = buttonRef.current.getBoundingClientRect()
      const size = Math.max(rect.width, rect.height)
      const x = e.clientX - rect.left - size / 2
      const y = e.clientY - rect.top - size / 2
      
      const newRipple = {
        id: Date.now(),
        x,
        y,
        size
      }
      
      setRipples(prev => [...prev, newRipple])
      
      setTimeout(() => {
        setRipples(prev => prev.filter(ripple => ripple.id !== newRipple.id))
      }, 600)
    }
    
    setIsPressed(true)
    setTimeout(() => setIsPressed(false), 150)
    
    if (onClick) onClick(e)
  }

  const getVariantClasses = () => {
    switch (variant) {
      case 'glow':
        return 'hover:shadow-2xl hover:shadow-indigo-500/25 hover:scale-105 transition-all duration-300 ease-out'
      case 'lift':
        return 'hover:-translate-y-2 hover:shadow-xl transition-all duration-300 ease-out'
      case 'magnetic':
        return 'transition-all duration-200 ease-out'
      case 'morph':
        return 'hover:rounded-2xl transition-all duration-500 ease-out'
      default:
        return 'transition-all duration-300 ease-out'
    }
  }

  const handleMouseMove = (e) => {
    if (variant === 'magnetic') {
      const rect = buttonRef.current.getBoundingClientRect()
      const centerX = rect.left + rect.width / 2
      const centerY = rect.top + rect.height / 2
      const deltaX = (e.clientX - centerX) * 0.1
      const deltaY = (e.clientY - centerY) * 0.1
      
      buttonRef.current.style.transform = `translate(${deltaX}px, ${deltaY}px)`
    }
  }

  const handleMouseLeave = () => {
    if (variant === 'magnetic') {
      buttonRef.current.style.transform = 'translate(0, 0)'
    }
  }

  return (
    <button
      ref={buttonRef}
      className={cn(
        'relative overflow-hidden',
        getVariantClasses(),
        isPressed && 'scale-95',
        className
      )}
      onClick={handleClick}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      {...props}
    >
      {children}
      
      {variant === 'ripple' && (
        <div className="absolute inset-0 pointer-events-none">
          {ripples.map(ripple => (
            <div
              key={ripple.id}
              className="absolute bg-white/30 rounded-full animate-ping"
              style={{
                left: ripple.x,
                top: ripple.y,
                width: ripple.size,
                height: ripple.size,
                animationDuration: '600ms'
              }}
            />
          ))}
        </div>
      )}
    </button>
  )
}

/**
 * HoverCard component with various hover effects
 * @param {Object} props - Component props
 * @param {React.ReactNode} props.children - Card content
 * @param {string} props.effect - Hover effect ('lift', 'tilt', 'glow', 'scale', 'rotate')
 * @param {string} props.className - Additional CSS classes
 * @returns {JSX.Element} Hover card component
 */
export const HoverCard = ({
  children,
  effect = 'lift',
  className = '',
  ...props
}) => {
  const cardRef = useRef(null)
  const [transform, setTransform] = useState('')

  const handleMouseMove = (e) => {
    if (effect === 'tilt') {
      const rect = cardRef.current.getBoundingClientRect()
      const centerX = rect.left + rect.width / 2
      const centerY = rect.top + rect.height / 2
      
      const rotateX = ((e.clientY - centerY) / (rect.height / 2)) * 10
      const rotateY = ((centerX - e.clientX) / (rect.width / 2)) * 10
      
      setTransform(`perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateZ(20px)`)
    }
  }

  const handleMouseLeave = () => {
    if (effect === 'tilt') {
      setTransform('')
    }
  }

  const getEffectClasses = () => {
    switch (effect) {
      case 'lift':
        return 'hover:-translate-y-4 hover:shadow-2xl transition-all duration-300 ease-out'
      case 'glow':
        return 'hover:shadow-2xl hover:shadow-indigo-500/20 transition-all duration-300 ease-out'
      case 'scale':
        return 'hover:scale-105 transition-all duration-300 ease-out'
      case 'rotate':
        return 'hover:rotate-1 hover:scale-105 transition-all duration-300 ease-out'
      case 'tilt':
        return 'transition-all duration-200 ease-out'
      default:
        return 'transition-all duration-300 ease-out'
    }
  }

  return (
    <div
      ref={cardRef}
      className={cn(
        'will-change-transform',
        getEffectClasses(),
        className
      )}
      style={{ transform, transformStyle: 'preserve-3d' }}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      {...props}
    >
      {children}
    </div>
  )
}

/**
 * AnimatedIcon component with hover and click animations
 * @param {Object} props - Component props
 * @param {React.ReactNode} props.icon - Icon component
 * @param {string} props.animation - Animation type ('bounce', 'spin', 'pulse', 'shake')
 * @param {string} props.trigger - Animation trigger ('hover', 'click', 'both')
 * @param {string} props.className - Additional CSS classes
 * @returns {JSX.Element} Animated icon component
 */
export const AnimatedIcon = ({
  icon,
  animation = 'bounce',
  trigger = 'hover',
  className = '',
  ...props
}) => {
  const [isAnimating, setIsAnimating] = useState(false)

  const handleClick = () => {
    if (trigger === 'click' || trigger === 'both') {
      setIsAnimating(true)
      setTimeout(() => setIsAnimating(false), 600)
    }
  }

  const getAnimationClasses = () => {
    const animations = {
      bounce: 'animate-bounce',
      spin: 'animate-spin',
      pulse: 'animate-pulse',
      shake: 'animate-shake'
    }
    
    const hoverClasses = {
      bounce: 'hover:animate-bounce',
      spin: 'hover:animate-spin',
      pulse: 'hover:animate-pulse',
      shake: 'hover:animate-shake'
    }

    let classes = ''
    
    if (trigger === 'hover' || trigger === 'both') {
      classes += ` ${hoverClasses[animation]}`
    }
    
    if (isAnimating) {
      classes += ` ${animations[animation]}`
    }
    
    return classes
  }

  return (
    <div
      className={cn(
        'inline-flex items-center justify-center transition-all duration-300',
        getAnimationClasses(),
        className
      )}
      onClick={handleClick}
      {...props}
    >
      {icon}
    </div>
  )
}

/**
 * GlitchText component for glitch text effects
 * @param {Object} props - Component props
 * @param {string} props.text - Text to glitch
 * @param {boolean} props.hover - Enable on hover only
 * @param {string} props.className - Additional CSS classes
 * @returns {JSX.Element} Glitch text component
 */
export const GlitchText = ({
  text,
  hover = true,
  className = '',
  ...props
}) => {
  const [isGlitching, setIsGlitching] = useState(false)

  const triggerGlitch = () => {
    setIsGlitching(true)
    setTimeout(() => setIsGlitching(false), 2000)
  }

  return (
    <span
      className={cn(
        'relative inline-block',
        hover && 'hover:animate-glitch cursor-default',
        isGlitching && 'animate-glitch',
        className
      )}
      onMouseEnter={hover ? undefined : triggerGlitch}
      onClick={!hover ? triggerGlitch : undefined}
      {...props}
    >
      <span className="relative z-10">{text}</span>
      <span 
        className="absolute top-0 left-0 z-0 text-red-500 opacity-70"
        style={{ 
          clipPath: 'polygon(0 0, 100% 0, 100% 45%, 0 45%)',
          transform: 'translateX(-2px)'
        }}
      >
        {text}
      </span>
      <span 
        className="absolute top-0 left-0 z-0 text-blue-500 opacity-70"
        style={{ 
          clipPath: 'polygon(0 55%, 100% 55%, 100% 100%, 0 100%)',
          transform: 'translateX(2px)'
        }}
      >
        {text}
      </span>
    </span>
  )
}

/**
 * MagneticElement component that follows mouse movement
 * @param {Object} props - Component props
 * @param {React.ReactNode} props.children - Content to make magnetic
 * @param {number} props.strength - Magnetic strength (0-1)
 * @param {string} props.className - Additional CSS classes
 * @returns {JSX.Element} Magnetic element component
 */
export const MagneticElement = ({
  children,
  strength = 0.3,
  className = '',
  ...props
}) => {
  const elementRef = useRef(null)
  const [transform, setTransform] = useState('')

  const handleMouseMove = (e) => {
    const rect = elementRef.current.getBoundingClientRect()
    const centerX = rect.left + rect.width / 2
    const centerY = rect.top + rect.height / 2
    
    const deltaX = (e.clientX - centerX) * strength
    const deltaY = (e.clientY - centerY) * strength
    
    setTransform(`translate(${deltaX}px, ${deltaY}px)`)
  }

  const handleMouseLeave = () => {
    setTransform('translate(0, 0)')
  }

  return (
    <div
      ref={elementRef}
      className={cn('will-change-transform transition-transform duration-200 ease-out', className)}
      style={{ transform }}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      {...props}
    >
      {children}
    </div>
  )
}

/**
 * ScrollReveal component that reveals content on scroll
 * @param {Object} props - Component props
 * @param {React.ReactNode} props.children - Content to reveal
 * @param {string} props.direction - Reveal direction ('up', 'down', 'left', 'right', 'scale')
 * @param {number} props.delay - Animation delay in ms
 * @param {string} props.className - Additional CSS classes
 * @returns {JSX.Element} Scroll reveal component
 */
export const ScrollReveal = ({
  children,
  direction = 'up',
  delay = 0,
  className = '',
  ...props
}) => {
  const elementRef = useRef(null)
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setTimeout(() => {
              setIsVisible(true)
            }, delay)
            observer.unobserve(entry.target)
          }
        })
      },
      { threshold: 0.1 }
    )

    if (elementRef.current) {
      observer.observe(elementRef.current)
    }

    return () => observer.disconnect()
  }, [delay])

  const getDirectionClasses = () => {
    const base = 'transition-all duration-700 ease-out'
    const hidden = {
      up: 'opacity-0 translate-y-8',
      down: 'opacity-0 -translate-y-8',
      left: 'opacity-0 translate-x-8',
      right: 'opacity-0 -translate-x-8',
      scale: 'opacity-0 scale-95'
    }
    const visible = 'opacity-100 translate-x-0 translate-y-0 scale-100'

    return `${base} ${isVisible ? visible : hidden[direction]}`
  }

  return (
    <div
      ref={elementRef}
      className={cn(getDirectionClasses(), className)}
      {...props}
    >
      {children}
    </div>
  )
}

/**
 * CounterAnimation component for animated numbers
 * @param {Object} props - Component props
 * @param {number} props.end - End number
 * @param {number} props.start - Start number
 * @param {number} props.duration - Animation duration in ms
 * @param {string} props.suffix - Text suffix (e.g., '+', '%', 'K')
 * @param {string} props.className - Additional CSS classes
 * @returns {JSX.Element} Counter animation component
 */
export const CounterAnimation = ({
  end,
  start = 0,
  duration = 2000,
  suffix = '',
  className = '',
  ...props
}) => {
  const elementRef = useRef(null)
  const [count, setCount] = useState(start)
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && !isVisible) {
            setIsVisible(true)
            
            const startTime = Date.now()
            const animate = () => {
              const elapsed = Date.now() - startTime
              const progress = Math.min(elapsed / duration, 1)
              
              // Easing function
              const easeOutCubic = 1 - Math.pow(1 - progress, 3)
              const currentCount = Math.floor(start + (end - start) * easeOutCubic)
              
              setCount(currentCount)
              
              if (progress < 1) {
                requestAnimationFrame(animate)
              }
            }
            
            requestAnimationFrame(animate)
            observer.unobserve(entry.target)
          }
        })
      },
      { threshold: 0.5 }
    )

    if (elementRef.current) {
      observer.observe(elementRef.current)
    }

    return () => observer.disconnect()
  }, [start, end, duration, isVisible])

  return (
    <span
      ref={elementRef}
      className={cn('tabular-nums', className)}
      {...props}
    >
      {count.toLocaleString()}{suffix}
    </span>
  )
}

/**
 * ProgressBar component with animated progress
 * @param {Object} props - Component props
 * @param {number} props.progress - Progress value (0-100)
 * @param {string} props.color - Progress bar color
 * @param {boolean} props.animated - Enable animation
 * @param {string} props.className - Additional CSS classes
 * @returns {JSX.Element} Progress bar component
 */
export const ProgressBar = ({
  progress,
  color = 'bg-indigo-500',
  animated = true,
  className = '',
  ...props
}) => {
  const [animatedProgress, setAnimatedProgress] = useState(0)

  useEffect(() => {
    if (animated) {
      const timer = setTimeout(() => {
        setAnimatedProgress(progress)
      }, 100)
      return () => clearTimeout(timer)
    } else {
      setAnimatedProgress(progress)
    }
  }, [progress, animated])

  return (
    <div
      className={cn('w-full bg-gray-200 rounded-full h-2 overflow-hidden', className)}
      {...props}
    >
      <div
        className={cn(
          'h-full rounded-full transition-all duration-1000 ease-out',
          color
        )}
        style={{ width: `${animatedProgress}%` }}
      />
    </div>
  )
}

// Additional CSS for shake animation (add to global CSS)
const shakeKeyframes = `
@keyframes shake {
  0%, 100% { transform: translateX(0); }
  10%, 30%, 50%, 70%, 90% { transform: translateX(-2px); }
  20%, 40%, 60%, 80% { transform: translateX(2px); }
}

.animate-shake {
  animation: shake 0.6s ease-in-out;
}
`

// Export the CSS for use in global styles
export const microInteractionStyles = shakeKeyframes
