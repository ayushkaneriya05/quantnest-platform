import React, { useRef, useEffect, useState } from 'react'
import { cn } from '@/lib/utils'

/**
 * LoadingSpinner component with various spinner types
 * @param {Object} props - Component props
 * @param {string} props.type - Spinner type ('dots', 'pulse', 'ring', 'bars', 'wave')
 * @param {string} props.size - Spinner size ('sm', 'md', 'lg', 'xl')
 * @param {string} props.color - Spinner color
 * @param {string} props.className - Additional CSS classes
 * @returns {JSX.Element} Loading spinner component
 */
export const LoadingSpinner = ({
  type = 'dots',
  size = 'md',
  color = 'text-indigo-500',
  className = '',
  ...props
}) => {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
    xl: 'w-16 h-16'
  }

  const dotSizes = {
    sm: 'w-1 h-1',
    md: 'w-2 h-2',
    lg: 'w-3 h-3',
    xl: 'w-4 h-4'
  }

  const renderSpinner = () => {
    switch (type) {
      case 'dots':
        return (
          <div className={cn('flex space-x-1', className)} {...props}>
            {[0, 1, 2].map((index) => (
              <div
                key={index}
                className={cn(
                  'rounded-full animate-pulse',
                  dotSizes[size],
                  color.replace('text-', 'bg-')
                )}
                style={{
                  animationDelay: `${index * 0.2}s`,
                  animationDuration: '1.4s'
                }}
              />
            ))}
          </div>
        )

      case 'pulse':
        return (
          <div className={cn('animate-pulse', className)} {...props}>
            <div className={cn('rounded-full', sizeClasses[size], color.replace('text-', 'bg-'))} />
          </div>
        )

      case 'ring':
        return (
          <div
            className={cn(
              'animate-spin rounded-full border-2 border-gray-300',
              sizeClasses[size],
              className
            )}
            style={{
              borderTopColor: 'currentColor'
            }}
            {...props}
          />
        )

      case 'bars':
        return (
          <div className={cn('flex space-x-1', className)} {...props}>
            {[0, 1, 2, 3].map((index) => (
              <div
                key={index}
                className={cn(
                  'w-1 animate-pulse',
                  color.replace('text-', 'bg-')
                )}
                style={{
                  height: size === 'sm' ? '16px' : size === 'md' ? '24px' : size === 'lg' ? '32px' : '40px',
                  animationDelay: `${index * 0.1}s`,
                  animationDuration: '1.2s'
                }}
              />
            ))}
          </div>
        )

      case 'wave':
        return (
          <div className={cn('flex space-x-1', className)} {...props}>
            {[0, 1, 2, 3, 4].map((index) => (
              <div
                key={index}
                className={cn(
                  'w-1 rounded-full animate-bounce',
                  color.replace('text-', 'bg-')
                )}
                style={{
                  height: size === 'sm' ? '12px' : size === 'md' ? '20px' : size === 'lg' ? '28px' : '36px',
                  animationDelay: `${index * 0.1}s`,
                  animationDuration: '1.0s'
                }}
              />
            ))}
          </div>
        )

      default:
        return renderSpinner()
    }
  }

  return renderSpinner()
}

/**
 * PageTransition component for smooth page transitions
 * @param {Object} props - Component props
 * @param {React.ReactNode} props.children - Page content
 * @param {string} props.type - Transition type ('fade', 'slide', 'scale', 'curtain')
 * @param {number} props.duration - Transition duration in ms
 * @param {string} props.className - Additional CSS classes
 * @returns {JSX.Element} Page transition component
 */
export const PageTransition = ({
  children,
  type = 'fade',
  duration = 600,
  className = '',
  ...props
}) => {
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsVisible(true)
    }, 50)
    return () => clearTimeout(timer)
  }, [])

  const getTransitionClasses = () => {
    const base = `transition-all ease-out`
    const durationClass = `duration-${duration}`

    switch (type) {
      case 'fade':
        return `${base} ${durationClass} ${isVisible ? 'opacity-100' : 'opacity-0'}`
      case 'slide':
        return `${base} ${durationClass} transform ${isVisible ? 'translate-x-0' : 'translate-x-full'}`
      case 'scale':
        return `${base} ${durationClass} transform ${isVisible ? 'scale-100' : 'scale-95'} ${isVisible ? 'opacity-100' : 'opacity-0'}`
      case 'curtain':
        return `${base} ${durationClass} transform ${isVisible ? 'translate-y-0' : '-translate-y-full'}`
      default:
        return `${base} ${durationClass}`
    }
  }

  return (
    <div className={cn(getTransitionClasses(), className)} {...props}>
      {children}
    </div>
  )
}

/**
 * SectionTransition component for animating section entrances
 * @param {Object} props - Component props
 * @param {React.ReactNode} props.children - Section content
 * @param {string} props.animation - Animation type ('fadeInUp', 'slideInLeft', 'scaleIn', 'rotateIn')
 * @param {number} props.delay - Animation delay in ms
 * @param {number} props.threshold - Intersection threshold
 * @param {string} props.className - Additional CSS classes
 * @returns {JSX.Element} Section transition component
 */
export const SectionTransition = ({
  children,
  animation = 'fadeInUp',
  delay = 0,
  threshold = 0.1,
  className = '',
  ...props
}) => {
  const sectionRef = useRef(null)
  const [hasAnimated, setHasAnimated] = useState(false)

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && !hasAnimated) {
            setTimeout(() => {
              entry.target.classList.add('animate-in')
              setHasAnimated(true)
            }, delay)
            observer.unobserve(entry.target)
          }
        })
      },
      { threshold }
    )

    if (sectionRef.current) {
      observer.observe(sectionRef.current)
    }

    return () => observer.disconnect()
  }, [delay, threshold, hasAnimated])

  const getInitialClasses = () => {
    switch (animation) {
      case 'fadeInUp':
        return 'opacity-0 translate-y-8'
      case 'fadeInDown':
        return 'opacity-0 -translate-y-8'
      case 'slideInLeft':
        return 'opacity-0 -translate-x-8'
      case 'slideInRight':
        return 'opacity-0 translate-x-8'
      case 'scaleIn':
        return 'opacity-0 scale-95'
      case 'rotateIn':
        return 'opacity-0 -rotate-3'
      default:
        return 'opacity-0'
    }
  }

  return (
    <div
      ref={sectionRef}
      className={cn(
        'transition-all duration-700 ease-out',
        getInitialClasses(),
        'animate-in:opacity-100 animate-in:translate-x-0 animate-in:translate-y-0 animate-in:scale-100 animate-in:rotate-0',
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
}

/**
 * SkeletonLoader component for content loading states
 * @param {Object} props - Component props
 * @param {string} props.variant - Skeleton variant ('text', 'card', 'avatar', 'custom')
 * @param {number} props.lines - Number of text lines (for text variant)
 * @param {string} props.className - Additional CSS classes
 * @returns {JSX.Element} Skeleton loader component
 */
export const SkeletonLoader = ({
  variant = 'text',
  lines = 3,
  className = '',
  ...props
}) => {
  const baseClasses = 'animate-pulse bg-gray-300 rounded'

  const renderSkeleton = () => {
    switch (variant) {
      case 'text':
        return (
          <div className={cn('space-y-2', className)} {...props}>
            {Array.from({ length: lines }).map((_, index) => (
              <div
                key={index}
                className={cn(
                  baseClasses,
                  'h-4',
                  index === lines - 1 ? 'w-3/4' : 'w-full'
                )}
              />
            ))}
          </div>
        )

      case 'card':
        return (
          <div className={cn('space-y-4', className)} {...props}>
            <div className={cn(baseClasses, 'h-48 w-full')} />
            <div className="space-y-2">
              <div className={cn(baseClasses, 'h-4 w-3/4')} />
              <div className={cn(baseClasses, 'h-4 w-1/2')} />
            </div>
          </div>
        )

      case 'avatar':
        return (
          <div className={cn('flex items-center space-x-4', className)} {...props}>
            <div className={cn(baseClasses, 'h-12 w-12 rounded-full')} />
            <div className="space-y-2 flex-1">
              <div className={cn(baseClasses, 'h-4 w-1/4')} />
              <div className={cn(baseClasses, 'h-4 w-1/3')} />
            </div>
          </div>
        )

      case 'custom':
        return <div className={cn(baseClasses, className)} {...props} />

      default:
        return renderSkeleton()
    }
  }

  return renderSkeleton()
}

/**
 * ProgressiveLoad component for progressive image/content loading
 * @param {Object} props - Component props
 * @param {React.ReactNode} props.children - Content to load
 * @param {React.ReactNode} props.fallback - Loading fallback
 * @param {number} props.delay - Loading delay in ms
 * @param {string} props.className - Additional CSS classes
 * @returns {JSX.Element} Progressive load component
 */
export const ProgressiveLoad = ({
  children,
  fallback,
  delay = 300,
  className = '',
  ...props
}) => {
  const [isLoaded, setIsLoaded] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsLoaded(true)
    }, delay)
    return () => clearTimeout(timer)
  }, [delay])

  return (
    <div className={cn('relative', className)} {...props}>
      {!isLoaded && (
        <div className="absolute inset-0 z-10 flex items-center justify-center">
          {fallback || <LoadingSpinner />}
        </div>
      )}
      <div
        className={cn(
          'transition-opacity duration-500',
          isLoaded ? 'opacity-100' : 'opacity-0'
        )}
      >
        {children}
      </div>
    </div>
  )
}

/**
 * CountdownTimer component with animated countdown
 * @param {Object} props - Component props
 * @param {number} props.seconds - Countdown duration in seconds
 * @param {Function} props.onComplete - Callback when countdown completes
 * @param {string} props.className - Additional CSS classes
 * @returns {JSX.Element} Countdown timer component
 */
export const CountdownTimer = ({
  seconds,
  onComplete,
  className = '',
  ...props
}) => {
  const [timeLeft, setTimeLeft] = useState(seconds)

  useEffect(() => {
    if (timeLeft <= 0) {
      if (onComplete) onComplete()
      return
    }

    const timer = setTimeout(() => {
      setTimeLeft(timeLeft - 1)
    }, 1000)

    return () => clearTimeout(timer)
  }, [timeLeft, onComplete])

  const progress = ((seconds - timeLeft) / seconds) * 100

  return (
    <div className={cn('text-center', className)} {...props}>
      <div className="relative w-24 h-24 mx-auto mb-4">
        <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
          <circle
            cx="50"
            cy="50"
            r="45"
            stroke="currentColor"
            strokeWidth="8"
            fill="none"
            className="text-gray-300"
          />
          <circle
            cx="50"
            cy="50"
            r="45"
            stroke="currentColor"
            strokeWidth="8"
            fill="none"
            strokeDasharray={`${progress * 2.83} 283`}
            className="text-indigo-500 transition-all duration-1000 ease-linear"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-2xl font-bold">{timeLeft}</span>
        </div>
      </div>
    </div>
  )
}

/**
 * TypewriterEffect component for typewriter text animation
 * @param {Object} props - Component props
 * @param {string[]} props.words - Array of words/sentences to type
 * @param {number} props.speed - Typing speed in ms per character
 * @param {number} props.deleteSpeed - Delete speed in ms per character
 * @param {number} props.delay - Delay between words in ms
 * @param {boolean} props.loop - Whether to loop the animation
 * @param {string} props.className - Additional CSS classes
 * @returns {JSX.Element} Typewriter effect component
 */
export const TypewriterEffect = ({
  words,
  speed = 100,
  deleteSpeed = 50,
  delay = 2000,
  loop = true,
  className = '',
  ...props
}) => {
  const [currentWordIndex, setCurrentWordIndex] = useState(0)
  const [currentText, setCurrentText] = useState('')
  const [isDeleting, setIsDeleting] = useState(false)
  const [isPaused, setIsPaused] = useState(false)

  useEffect(() => {
    if (!words.length) return

    const currentWord = words[currentWordIndex]

    if (isPaused) {
      const pauseTimer = setTimeout(() => {
        setIsPaused(false)
        setIsDeleting(true)
      }, delay)
      return () => clearTimeout(pauseTimer)
    }

    const timer = setTimeout(() => {
      if (!isDeleting) {
        // Typing
        if (currentText.length < currentWord.length) {
          setCurrentText(currentWord.slice(0, currentText.length + 1))
        } else {
          setIsPaused(true)
        }
      } else {
        // Deleting
        if (currentText.length > 0) {
          setCurrentText(currentText.slice(0, -1))
        } else {
          setIsDeleting(false)
          setCurrentWordIndex((prev) => {
            if (loop) {
              return (prev + 1) % words.length
            } else {
              return Math.min(prev + 1, words.length - 1)
            }
          })
        }
      }
    }, isDeleting ? deleteSpeed : speed)

    return () => clearTimeout(timer)
  }, [currentText, currentWordIndex, isDeleting, isPaused, words, speed, deleteSpeed, delay, loop])

  return (
    <span className={cn('inline-block', className)} {...props}>
      {currentText}
      <span className="animate-pulse">|</span>
    </span>
  )
}

/**
 * SlideInSection component for section slide-in animations
 * @param {Object} props - Component props
 * @param {React.ReactNode} props.children - Section content
 * @param {string} props.direction - Slide direction ('left', 'right', 'up', 'down')
 * @param {number} props.duration - Animation duration in ms
 * @param {number} props.delay - Animation delay in ms
 * @param {string} props.className - Additional CSS classes
 * @returns {JSX.Element} Slide in section component
 */
export const SlideInSection = ({
  children,
  direction = 'left',
  duration = 700,
  delay = 0,
  className = '',
  ...props
}) => {
  const sectionRef = useRef(null)
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

    if (sectionRef.current) {
      observer.observe(sectionRef.current)
    }

    return () => observer.disconnect()
  }, [delay])

  const getTransformClasses = () => {
    const transforms = {
      left: isVisible ? 'translate-x-0' : '-translate-x-full',
      right: isVisible ? 'translate-x-0' : 'translate-x-full',
      up: isVisible ? 'translate-y-0' : 'translate-y-full',
      down: isVisible ? 'translate-y-0' : '-translate-y-full'
    }

    return `transition-all duration-${duration} ease-out transform ${transforms[direction]} ${
      isVisible ? 'opacity-100' : 'opacity-0'
    }`
  }

  return (
    <div
      ref={sectionRef}
      className={cn(getTransformClasses(), className)}
      {...props}
    >
      {children}
    </div>
  )
}
