import { useEffect, useRef, useState, useCallback } from 'react'

/**
 * Custom hook for scroll-triggered animations using Intersection Observer API
 * @param {Object} options - Configuration options for the animation
 * @param {string} options.animationClass - CSS class to apply when element is in view
 * @param {number} options.threshold - Intersection threshold (0-1)
 * @param {string} options.rootMargin - Root margin for intersection observer
 * @param {boolean} options.triggerOnce - Whether to trigger animation only once
 * @param {number} options.delay - Delay before animation starts (in ms)
 * @returns {Array} [ref, isInView, trigger] - Reference for element, visibility state, manual trigger
 */
export const useScrollAnimation = ({
  animationClass = 'animate-fadeInUp',
  threshold = 0.1,
  rootMargin = '0px 0px -50px 0px',
  triggerOnce = true,
  delay = 0
} = {}) => {
  const elementRef = useRef(null)
  const [isInView, setIsInView] = useState(false)
  const [hasTriggered, setHasTriggered] = useState(false)
  const observerRef = useRef(null)

  const trigger = useCallback(() => {
    if (elementRef.current && (!triggerOnce || !hasTriggered)) {
      const element = elementRef.current
      
      const applyAnimation = () => {
        element.classList.add(animationClass)
        setIsInView(true)
        setHasTriggered(true)
      }

      if (delay > 0) {
        setTimeout(applyAnimation, delay)
      } else {
        applyAnimation()
      }
    }
  }, [animationClass, triggerOnce, hasTriggered, delay])

  useEffect(() => {
    const element = elementRef.current
    if (!element) return

    // Check if Intersection Observer is supported
    if (!window.IntersectionObserver) {
      // Fallback for browsers without Intersection Observer support
      trigger()
      return
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            trigger()
            
            // If triggerOnce is true, stop observing after first trigger
            if (triggerOnce) {
              observer.unobserve(element)
            }
          } else if (!triggerOnce) {
            // Remove animation class when element goes out of view
            element.classList.remove(animationClass)
            setIsInView(false)
          }
        })
      },
      {
        threshold,
        rootMargin
      }
    )

    observerRef.current = observer
    observer.observe(element)

    // Cleanup function
    return () => {
      if (observer) {
        observer.unobserve(element)
        observer.disconnect()
      }
    }
  }, [animationClass, threshold, rootMargin, triggerOnce, trigger])

  return [elementRef, isInView, trigger]
}

/**
 * Hook for staggered animations - animates children with delays
 * @param {Object} options - Configuration options
 * @param {number} options.staggerDelay - Delay between each child animation (in ms)
 * @param {string} options.animationClass - CSS class to apply to children
 * @param {number} options.threshold - Intersection threshold
 * @returns {Array} [ref, isInView, childRefs] - Parent ref, visibility state, child refs array
 */
export const useStaggeredAnimation = ({
  staggerDelay = 100,
  animationClass = 'animate-fadeInUp',
  threshold = 0.1
} = {}) => {
  const containerRef = useRef(null)
  const [isInView, setIsInView] = useState(false)
  const [childRefs, setChildRefs] = useState([])

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    // Get all direct children
    const children = Array.from(container.children)
    setChildRefs(children)

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setIsInView(true)
            
            // Animate children with stagger delay
            children.forEach((child, index) => {
              setTimeout(() => {
                child.classList.add(animationClass)
              }, index * staggerDelay)
            })

            observer.unobserve(container)
          }
        })
      },
      { threshold }
    )

    observer.observe(container)

    return () => {
      observer.unobserve(container)
      observer.disconnect()
    }
  }, [staggerDelay, animationClass, threshold])

  return [containerRef, isInView, childRefs]
}

/**
 * Hook for parallax scrolling effects
 * @param {Object} options - Configuration options
 * @param {number} options.speed - Parallax speed multiplier (0-1 for slower, >1 for faster)
 * @param {string} options.direction - Direction of parallax ('up', 'down', 'left', 'right')
 * @returns {Array} [ref, transform] - Element ref and current transform value
 */
export const useParallax = ({
  speed = 0.5,
  direction = 'up'
} = {}) => {
  const elementRef = useRef(null)
  const [transform, setTransform] = useState('')

  useEffect(() => {
    const element = elementRef.current
    if (!element) return

    const handleScroll = () => {
      const elementTop = element.offsetTop
      const elementHeight = element.offsetHeight
      const windowHeight = window.innerHeight
      const scrollY = window.scrollY

      // Calculate if element is in viewport
      const elementBottom = elementTop + elementHeight
      const inView = scrollY < elementBottom && (scrollY + windowHeight) > elementTop

      if (inView) {
        const scrolled = scrollY - elementTop + windowHeight
        const rate = scrolled * speed

        let transformValue = ''
        switch (direction) {
          case 'up':
            transformValue = `translateY(-${rate}px)`
            break
          case 'down':
            transformValue = `translateY(${rate}px)`
            break
          case 'left':
            transformValue = `translateX(-${rate}px)`
            break
          case 'right':
            transformValue = `translateX(${rate}px)`
            break
          default:
            transformValue = `translateY(-${rate}px)`
        }

        setTransform(transformValue)
      }
    }

    // Throttle scroll events for better performance
    let ticking = false
    const throttledScrollHandler = () => {
      if (!ticking) {
        requestAnimationFrame(() => {
          handleScroll()
          ticking = false
        })
        ticking = true
      }
    }

    window.addEventListener('scroll', throttledScrollHandler)
    
    // Initial call
    handleScroll()

    return () => {
      window.removeEventListener('scroll', throttledScrollHandler)
    }
  }, [speed, direction])

  return [elementRef, transform]
}

/**
 * Hook for counting animations (numbers)
 * @param {Object} options - Configuration options
 * @param {number} options.end - End number to count to
 * @param {number} options.start - Start number (default: 0)
 * @param {number} options.duration - Animation duration in ms
 * @param {Function} options.formatter - Function to format the number
 * @returns {Array} [ref, count, isAnimating] - Element ref, current count, animation state
 */
export const useCountUp = ({
  end,
  start = 0,
  duration = 2000,
  formatter = (num) => Math.floor(num).toLocaleString()
} = {}) => {
  const elementRef = useRef(null)
  const [count, setCount] = useState(start)
  const [isAnimating, setIsAnimating] = useState(false)
  const animationRef = useRef(null)

  const startAnimation = useCallback(() => {
    if (isAnimating) return

    setIsAnimating(true)
    const startTime = Date.now()
    const startValue = start
    const endValue = end

    const animate = () => {
      const now = Date.now()
      const elapsed = now - startTime
      const progress = Math.min(elapsed / duration, 1)

      // Easing function (ease-out)
      const easedProgress = 1 - Math.pow(1 - progress, 3)
      const currentValue = startValue + (endValue - startValue) * easedProgress

      setCount(currentValue)

      if (progress < 1) {
        animationRef.current = requestAnimationFrame(animate)
      } else {
        setIsAnimating(false)
      }
    }

    animationRef.current = requestAnimationFrame(animate)
  }, [start, end, duration, isAnimating])

  // Set up intersection observer to trigger animation
  useEffect(() => {
    const element = elementRef.current
    if (!element) return

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            startAnimation()
            observer.unobserve(element)
          }
        })
      },
      { threshold: 0.5 }
    )

    observer.observe(element)

    return () => {
      observer.unobserve(element)
      observer.disconnect()
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }
  }, [startAnimation])

  return [elementRef, formatter(count), isAnimating]
}

/**
 * Hook for typewriter text animation
 * @param {string} text - Text to animate
 * @param {number} speed - Typing speed in ms per character
 * @param {number} delay - Delay before starting animation
 * @returns {Array} [ref, displayText, isTyping] - Element ref, current display text, typing state
 */
export const useTypewriter = (text, speed = 100, delay = 0) => {
  const elementRef = useRef(null)
  const [displayText, setDisplayText] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [hasStarted, setHasStarted] = useState(false)

  const startTyping = useCallback(() => {
    if (hasStarted) return

    setHasStarted(true)
    setIsTyping(true)

    const typeText = () => {
      let index = 0
      const timer = setInterval(() => {
        if (index <= text.length) {
          setDisplayText(text.slice(0, index))
          index++
        } else {
          clearInterval(timer)
          setIsTyping(false)
        }
      }, speed)
    }

    if (delay > 0) {
      setTimeout(typeText, delay)
    } else {
      typeText()
    }
  }, [text, speed, delay, hasStarted])

  useEffect(() => {
    const element = elementRef.current
    if (!element) return

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            startTyping()
            observer.unobserve(element)
          }
        })
      },
      { threshold: 0.5 }
    )

    observer.observe(element)

    return () => {
      observer.unobserve(element)
      observer.disconnect()
    }
  }, [startTyping])

  return [elementRef, displayText, isTyping]
}
