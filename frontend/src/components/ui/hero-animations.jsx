import React, { useRef, useEffect, useState } from 'react'
import { cn } from '@/lib/utils'

/**
 * ParallaxLayer component for creating parallax effects
 * @param {Object} props - Component props
 * @param {React.ReactNode} props.children - Content to parallax
 * @param {number} props.speed - Parallax speed (-1 to 1, negative for reverse)
 * @param {string} props.className - Additional CSS classes
 * @param {number} props.offset - Initial offset in pixels
 * @returns {JSX.Element} Parallax layer component
 */
export const ParallaxLayer = ({
  children,
  speed = 0.5,
  className = '',
  offset = 0,
  ...props
}) => {
  const elementRef = useRef(null)
  const [transform, setTransform] = useState('')

  useEffect(() => {
    const element = elementRef.current
    if (!element) return

    let ticking = false

    const updateTransform = () => {
      const scrolled = window.pageYOffset
      const yPos = -(scrolled * speed) + offset
      setTransform(`translate3d(0, ${yPos}px, 0)`)
      ticking = false
    }

    const handleScroll = () => {
      if (!ticking) {
        requestAnimationFrame(updateTransform)
        ticking = true
      }
    }

    window.addEventListener('scroll', handleScroll)
    updateTransform() // Initial call

    return () => {
      window.removeEventListener('scroll', handleScroll)
    }
  }, [speed, offset])

  return (
    <div
      ref={elementRef}
      className={cn('will-change-transform', className)}
      style={{ transform }}
      {...props}
    >
      {children}
    </div>
  )
}

/**
 * FloatingElement component for floating animations
 * @param {Object} props - Component props
 * @param {React.ReactNode} props.children - Content to float
 * @param {string} props.animation - Animation type ('float', 'breathe', 'rotate')
 * @param {number} props.duration - Animation duration in seconds
 * @param {number} props.delay - Animation delay in seconds
 * @param {string} props.className - Additional CSS classes
 * @returns {JSX.Element} Floating element component
 */
export const FloatingElement = ({
  children,
  animation = 'float',
  duration = 6,
  delay = 0,
  className = '',
  intensity = 'normal',
  ...props
}) => {
  const getAnimationIntensity = () => {
    switch (intensity) {
      case 'subtle':
        return { translateY: '5px', scale: '1.02' }
      case 'normal':
        return { translateY: '15px', scale: '1.05' }
      case 'strong':
        return { translateY: '25px', scale: '1.08' }
      default:
        return { translateY: '15px', scale: '1.05' }
    }
  }

  const { translateY, scale } = getAnimationIntensity()

  const getAnimationStyle = () => {
    const baseStyle = {
      animationDuration: `${duration}s`,
      animationDelay: `${delay}s`,
      animationIterationCount: 'infinite',
      animationTimingFunction: 'ease-in-out'
    }

    switch (animation) {
      case 'float':
        return {
          ...baseStyle,
          animationName: 'float',
          '--float-distance': translateY
        }
      case 'breathe':
        return {
          ...baseStyle,
          animationName: 'breathe',
          '--breathe-scale': scale
        }
      case 'rotate':
        return {
          ...baseStyle,
          animationName: 'rotate3D'
        }
      case 'pulse':
        return {
          ...baseStyle,
          animationName: 'neonGlow'
        }
      default:
        return baseStyle
    }
  }

  return (
    <div
      className={cn('will-change-transform', className)}
      style={getAnimationStyle()}
      {...props}
    >
      {children}
    </div>
  )
}

/**
 * Transform3D component for 3D transform effects
 * @param {Object} props - Component props
 * @param {React.ReactNode} props.children - Content to transform
 * @param {number} props.rotateX - X-axis rotation in degrees
 * @param {number} props.rotateY - Y-axis rotation in degrees
 * @param {number} props.rotateZ - Z-axis rotation in degrees
 * @param {number} props.perspective - Perspective value in pixels
 * @param {string} props.className - Additional CSS classes
 * @param {boolean} props.hover - Enable hover effects
 * @returns {JSX.Element} 3D transform component
 */
export const Transform3D = ({
  children,
  rotateX = 0,
  rotateY = 0,
  rotateZ = 0,
  perspective = 1000,
  className = '',
  hover = false,
  ...props
}) => {
  const [isHovered, setIsHovered] = useState(false)

  const baseTransform = `perspective(${perspective}px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) rotateZ(${rotateZ}deg)`
  const hoverTransform = `perspective(${perspective}px) rotateX(${rotateX + 10}deg) rotateY(${rotateY + 10}deg) rotateZ(${rotateZ}deg) scale(1.05)`

  return (
    <div
      className={cn(
        'will-change-transform transition-transform duration-300 ease-out',
        className
      )}
      style={{
        transform: hover && isHovered ? hoverTransform : baseTransform,
        transformStyle: 'preserve-3d'
      }}
      onMouseEnter={() => hover && setIsHovered(true)}
      onMouseLeave={() => hover && setIsHovered(false)}
      {...props}
    >
      {children}
    </div>
  )
}

/**
 * MouseParallax component for mouse-following parallax effects
 * @param {Object} props - Component props
 * @param {React.ReactNode} props.children - Content to animate
 * @param {number} props.strength - Parallax strength (0-1)
 * @param {string} props.className - Additional CSS classes
 * @param {boolean} props.invert - Invert the parallax direction
 * @returns {JSX.Element} Mouse parallax component
 */
export const MouseParallax = ({
  children,
  strength = 0.1,
  className = '',
  invert = false,
  ...props
}) => {
  const elementRef = useRef(null)
  const [transform, setTransform] = useState('')

  useEffect(() => {
    const element = elementRef.current
    if (!element) return

    const handleMouseMove = (e) => {
      const rect = element.getBoundingClientRect()
      const centerX = rect.left + rect.width / 2
      const centerY = rect.top + rect.height / 2
      
      const deltaX = (e.clientX - centerX) * strength
      const deltaY = (e.clientY - centerY) * strength
      
      const x = invert ? -deltaX : deltaX
      const y = invert ? -deltaY : deltaY
      
      setTransform(`translate3d(${x}px, ${y}px, 0)`)
    }

    const handleMouseLeave = () => {
      setTransform('translate3d(0, 0, 0)')
    }

    element.addEventListener('mousemove', handleMouseMove)
    element.addEventListener('mouseleave', handleMouseLeave)

    return () => {
      element.removeEventListener('mousemove', handleMouseMove)
      element.removeEventListener('mouseleave', handleMouseLeave)
    }
  }, [strength, invert])

  return (
    <div
      ref={elementRef}
      className={cn('will-change-transform transition-transform duration-200 ease-out', className)}
      style={{ transform }}
      {...props}
    >
      {children}
    </div>
  )
}

/**
 * MorphingGradient component for animated gradient backgrounds
 * @param {Object} props - Component props
 * @param {Array} props.colors - Array of color stops
 * @param {number} props.duration - Animation duration in seconds
 * @param {string} props.direction - Gradient direction
 * @param {string} props.className - Additional CSS classes
 * @returns {JSX.Element} Morphing gradient component
 */
export const MorphingGradient = ({
  colors = ['#667eea', '#764ba2', '#f093fb', '#f5576c'],
  duration = 8,
  direction = '-45deg',
  className = '',
  ...props
}) => {
  const gradientStyle = {
    background: `linear-gradient(${direction}, ${colors.join(', ')})`,
    backgroundSize: '400% 400%',
    animation: `gradientShift ${duration}s ease infinite`
  }

  return (
    <div
      className={cn('will-change-transform', className)}
      style={gradientStyle}
      {...props}
    />
  )
}

/**
 * ParticleField component for floating particle effects
 * @param {Object} props - Component props
 * @param {number} props.count - Number of particles
 * @param {string} props.color - Particle color
 * @param {number} props.size - Particle size range
 * @param {number} props.speed - Animation speed
 * @param {string} props.className - Additional CSS classes
 * @returns {JSX.Element} Particle field component
 */
export const ParticleField = ({
  count = 20,
  color = 'rgba(99, 102, 241, 0.3)',
  size = { min: 2, max: 8 },
  speed = { min: 10, max: 30 },
  className = '',
  ...props
}) => {
  const particles = Array.from({ length: count }, (_, i) => ({
    id: i,
    size: Math.random() * (size.max - size.min) + size.min,
    duration: Math.random() * (speed.max - speed.min) + speed.min,
    delay: Math.random() * 5,
    left: Math.random() * 100,
    opacity: Math.random() * 0.5 + 0.1
  }))

  return (
    <div className={cn('absolute inset-0 overflow-hidden pointer-events-none', className)} {...props}>
      {particles.map((particle) => (
        <div
          key={particle.id}
          className="absolute rounded-full animate-particle-float"
          style={{
            width: `${particle.size}px`,
            height: `${particle.size}px`,
            backgroundColor: color,
            left: `${particle.left}%`,
            bottom: '0%',
            opacity: particle.opacity,
            animationDuration: `${particle.duration}s`,
            animationDelay: `${particle.delay}s`
          }}
        />
      ))}
    </div>
  )
}

/**
 * TiltCard component for 3D tilt effects on hover
 * @param {Object} props - Component props
 * @param {React.ReactNode} props.children - Card content
 * @param {number} props.maxTilt - Maximum tilt angle in degrees
 * @param {number} props.perspective - Perspective value
 * @param {string} props.className - Additional CSS classes
 * @returns {JSX.Element} Tilt card component
 */
export const TiltCard = ({
  children,
  maxTilt = 15,
  perspective = 1000,
  className = '',
  ...props
}) => {
  const cardRef = useRef(null)
  const [transform, setTransform] = useState('')

  useEffect(() => {
    const card = cardRef.current
    if (!card) return

    const handleMouseMove = (e) => {
      const rect = card.getBoundingClientRect()
      const centerX = rect.left + rect.width / 2
      const centerY = rect.top + rect.height / 2
      
      const rotateX = ((e.clientY - centerY) / (rect.height / 2)) * maxTilt
      const rotateY = ((centerX - e.clientX) / (rect.width / 2)) * maxTilt
      
      setTransform(`perspective(${perspective}px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateZ(20px)`)
    }

    const handleMouseLeave = () => {
      setTransform('')
    }

    card.addEventListener('mousemove', handleMouseMove)
    card.addEventListener('mouseleave', handleMouseLeave)

    return () => {
      card.removeEventListener('mousemove', handleMouseMove)
      card.removeEventListener('mouseleave', handleMouseLeave)
    }
  }, [maxTilt, perspective])

  return (
    <div
      ref={cardRef}
      className={cn('will-change-transform transition-transform duration-200 ease-out', className)}
      style={{ 
        transform,
        transformStyle: 'preserve-3d'
      }}
      {...props}
    >
      {children}
    </div>
  )
}

/**
 * GlowingOrb component for glowing circular elements
 * @param {Object} props - Component props
 * @param {string} props.color - Orb color
 * @param {number} props.size - Orb size in pixels
 * @param {number} props.intensity - Glow intensity
 * @param {boolean} props.animate - Enable pulsing animation
 * @param {string} props.className - Additional CSS classes
 * @returns {JSX.Element} Glowing orb component
 */
export const GlowingOrb = ({
  color = '#667eea',
  size = 200,
  intensity = 0.8,
  animate = true,
  className = '',
  ...props
}) => {
  const orbStyle = {
    width: `${size}px`,
    height: `${size}px`,
    background: `radial-gradient(circle, ${color}${Math.round(intensity * 255).toString(16)}, transparent 70%)`,
    borderRadius: '50%',
    animation: animate ? 'breathe 4s ease-in-out infinite' : 'none'
  }

  return (
    <div
      className={cn('absolute will-change-transform', className)}
      style={orbStyle}
      {...props}
    />
  )
}

/**
 * HeroBackgroundEffects component combining multiple background effects
 * @param {Object} props - Component props
 * @param {string} props.className - Additional CSS classes
 * @returns {JSX.Element} Hero background effects component
 */
export const HeroBackgroundEffects = ({ className = '', ...props }) => {
  return (
    <div className={cn('absolute inset-0 overflow-hidden', className)} {...props}>
      {/* Animated gradient background */}
      <MorphingGradient
        colors={['rgba(99, 102, 241, 0.1)', 'rgba(139, 92, 246, 0.1)', 'rgba(236, 72, 153, 0.1)', 'rgba(59, 130, 246, 0.1)']}
        className="absolute inset-0"
        duration={12}
      />
      
      {/* Floating orbs */}
      <GlowingOrb
        color="rgba(99, 102, 241, 0.3)"
        size={300}
        className="top-10 -left-20 animate-float"
        animate={true}
      />
      <GlowingOrb
        color="rgba(236, 72, 153, 0.2)"
        size={200}
        className="top-1/2 -right-10 animate-float-reverse"
        animate={true}
      />
      <GlowingOrb
        color="rgba(139, 92, 246, 0.25)"
        size={150}
        className="bottom-20 left-1/3 animate-breathe"
        animate={true}
      />
      
      {/* Particle field */}
      <ParticleField
        count={30}
        color="rgba(255, 255, 255, 0.1)"
        size={{ min: 1, max: 4 }}
        speed={{ min: 15, max: 25 }}
      />
      
      {/* Geometric shapes */}
      <div className="absolute top-1/4 right-1/4 w-32 h-32 border border-indigo-500/20 rounded-2xl animate-rotate-3d transform rotate-45" />
      <div className="absolute bottom-1/3 left-1/4 w-24 h-24 border border-purple-500/20 rounded-full animate-breathe" />
    </div>
  )
}
