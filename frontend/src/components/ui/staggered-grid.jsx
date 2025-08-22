import React, { useRef, useEffect, useState } from 'react'
import { cn } from '@/lib/utils'

/**
 * StaggeredGrid component for animating grid items with staggered delays
 * @param {Object} props - Component props
 * @param {React.ReactNode} props.children - Grid items to animate
 * @param {string} props.className - Additional CSS classes
 * @param {number} props.staggerDelay - Delay between each item animation (ms)
 * @param {string} props.animationType - Type of animation ('fadeInUp', 'fadeInLeft', 'scaleIn', etc.)
 * @param {number} props.threshold - Intersection threshold for triggering animation
 * @param {boolean} props.triggerOnce - Whether to trigger animation only once
 * @param {string} props.gridCols - Tailwind grid columns class
 * @param {string} props.gap - Tailwind gap class
 * @returns {JSX.Element} Animated grid component
 */
export const StaggeredGrid = ({
  children,
  className = '',
  staggerDelay = 150,
  animationType = 'fadeInUp',
  threshold = 0.1,
  triggerOnce = true,
  gridCols = 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3',
  gap = 'gap-6',
  ...props
}) => {
  const gridRef = useRef(null)
  const [hasAnimated, setHasAnimated] = useState(false)

  useEffect(() => {
    const gridElement = gridRef.current
    if (!gridElement || hasAnimated) return

    const children = Array.from(gridElement.children)
    
    // Initialize children with invisible state
    children.forEach((child, index) => {
      child.style.opacity = '0'
      child.style.transform = getInitialTransform(animationType)
      child.style.transition = `all 0.6s cubic-bezier(0.4, 0, 0.2, 1)`
    })

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            // Animate children with staggered delays
            children.forEach((child, index) => {
              setTimeout(() => {
                child.style.opacity = '1'
                child.style.transform = getFinalTransform(animationType)
              }, index * staggerDelay)
            })

            setHasAnimated(true)
            
            if (triggerOnce) {
              observer.unobserve(gridElement)
            }
          }
        })
      },
      { threshold }
    )

    observer.observe(gridElement)

    return () => {
      observer.unobserve(gridElement)
      observer.disconnect()
    }
  }, [staggerDelay, animationType, threshold, triggerOnce, hasAnimated])

  return (
    <div
      ref={gridRef}
      className={cn(
        'grid',
        gridCols,
        gap,
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
}

/**
 * Get initial transform for animation type
 * @param {string} animationType - Type of animation
 * @returns {string} CSS transform value
 */
function getInitialTransform(animationType) {
  switch (animationType) {
    case 'fadeInUp':
      return 'translateY(30px)'
    case 'fadeInDown':
      return 'translateY(-30px)'
    case 'fadeInLeft':
      return 'translateX(-30px)'
    case 'fadeInRight':
      return 'translateX(30px)'
    case 'scaleIn':
      return 'scale(0.8)'
    case 'rotateIn':
      return 'rotateY(-90deg)'
    case 'flipIn':
      return 'rotateX(-90deg)'
    default:
      return 'translateY(30px)'
  }
}

/**
 * Get final transform for animation type
 * @param {string} animationType - Type of animation
 * @returns {string} CSS transform value
 */
function getFinalTransform(animationType) {
  switch (animationType) {
    case 'fadeInUp':
    case 'fadeInDown':
    case 'fadeInLeft':
    case 'fadeInRight':
      return 'translate(0, 0)'
    case 'scaleIn':
      return 'scale(1)'
    case 'rotateIn':
    case 'flipIn':
      return 'rotate(0deg)'
    default:
      return 'translate(0, 0)'
  }
}

/**
 * StaggeredList component for animating list items
 * @param {Object} props - Component props
 * @param {React.ReactNode} props.children - List items to animate
 * @param {string} props.className - Additional CSS classes
 * @param {number} props.staggerDelay - Delay between each item animation (ms)
 * @param {string} props.animationType - Type of animation
 * @param {number} props.threshold - Intersection threshold for triggering animation
 * @param {boolean} props.triggerOnce - Whether to trigger animation only once
 * @returns {JSX.Element} Animated list component
 */
export const StaggeredList = ({
  children,
  className = '',
  staggerDelay = 100,
  animationType = 'fadeInLeft',
  threshold = 0.1,
  triggerOnce = true,
  ...props
}) => {
  const listRef = useRef(null)
  const [hasAnimated, setHasAnimated] = useState(false)

  useEffect(() => {
    const listElement = listRef.current
    if (!listElement || hasAnimated) return

    const children = Array.from(listElement.children)
    
    // Initialize children with invisible state
    children.forEach((child, index) => {
      child.style.opacity = '0'
      child.style.transform = getInitialTransform(animationType)
      child.style.transition = `all 0.6s cubic-bezier(0.4, 0, 0.2, 1)`
    })

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            // Animate children with staggered delays
            children.forEach((child, index) => {
              setTimeout(() => {
                child.style.opacity = '1'
                child.style.transform = getFinalTransform(animationType)
              }, index * staggerDelay)
            })

            setHasAnimated(true)
            
            if (triggerOnce) {
              observer.unobserve(listElement)
            }
          }
        })
      },
      { threshold }
    )

    observer.observe(listElement)

    return () => {
      observer.unobserve(listElement)
      observer.disconnect()
    }
  }, [staggerDelay, animationType, threshold, triggerOnce, hasAnimated])

  return (
    <div
      ref={listRef}
      className={cn('space-y-4', className)}
      {...props}
    >
      {children}
    </div>
  )
}

/**
 * StaggeredContainer component for general staggered animations
 * @param {Object} props - Component props
 * @param {React.ReactNode} props.children - Elements to animate
 * @param {string} props.className - Additional CSS classes
 * @param {number} props.staggerDelay - Delay between each item animation (ms)
 * @param {string} props.animationType - Type of animation
 * @param {number} props.threshold - Intersection threshold for triggering animation
 * @param {boolean} props.triggerOnce - Whether to trigger animation only once
 * @param {string} props.direction - Animation direction ('horizontal', 'vertical', 'random')
 * @returns {JSX.Element} Animated container component
 */
export const StaggeredContainer = ({
  children,
  className = '',
  staggerDelay = 150,
  animationType = 'fadeInUp',
  threshold = 0.1,
  triggerOnce = true,
  direction = 'vertical',
  ...props
}) => {
  const containerRef = useRef(null)
  const [hasAnimated, setHasAnimated] = useState(false)

  useEffect(() => {
    const container = containerRef.current
    if (!container || hasAnimated) return

    const children = Array.from(container.children)
    
    // Initialize children with invisible state
    children.forEach((child, index) => {
      child.style.opacity = '0'
      child.style.transform = getInitialTransform(animationType)
      child.style.transition = `all 0.8s cubic-bezier(0.4, 0, 0.2, 1)`
    })

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            // Calculate animation order based on direction
            const animationOrder = getAnimationOrder(children, direction)
            
            // Animate children with staggered delays
            animationOrder.forEach((childIndex, orderIndex) => {
              setTimeout(() => {
                const child = children[childIndex]
                child.style.opacity = '1'
                child.style.transform = getFinalTransform(animationType)
              }, orderIndex * staggerDelay)
            })

            setHasAnimated(true)
            
            if (triggerOnce) {
              observer.unobserve(container)
            }
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
  }, [staggerDelay, animationType, threshold, triggerOnce, direction, hasAnimated])

  return (
    <div
      ref={containerRef}
      className={className}
      {...props}
    >
      {children}
    </div>
  )
}

/**
 * Get animation order based on direction
 * @param {Array} children - Array of child elements
 * @param {string} direction - Animation direction
 * @returns {Array} Array of indices in animation order
 */
function getAnimationOrder(children, direction) {
  const indices = children.map((_, index) => index)
  
  switch (direction) {
    case 'horizontal':
      // Left to right, then top to bottom
      return indices.sort((a, b) => {
        const aRect = children[a].getBoundingClientRect()
        const bRect = children[b].getBoundingClientRect()
        return aRect.left - bRect.left || aRect.top - bRect.top
      })
    
    case 'vertical':
      // Top to bottom, then left to right
      return indices.sort((a, b) => {
        const aRect = children[a].getBoundingClientRect()
        const bRect = children[b].getBoundingClientRect()
        return aRect.top - bRect.top || aRect.left - bRect.left
      })
    
    case 'random':
      // Random order
      return indices.sort(() => Math.random() - 0.5)
    
    case 'center-out':
      // From center outward
      const centerIndex = Math.floor(indices.length / 2)
      const result = []
      let left = centerIndex
      let right = centerIndex + 1
      
      result.push(indices[centerIndex])
      
      while (left > 0 || right < indices.length) {
        if (left > 0) result.push(indices[--left])
        if (right < indices.length) result.push(indices[right++])
      }
      
      return result
    
    default:
      return indices
  }
}

/**
 * Hook for manually controlling staggered animations
 * @param {Object} options - Configuration options
 * @param {number} options.staggerDelay - Delay between animations
 * @param {string} options.animationType - Type of animation
 * @returns {Array} [ref, trigger] - Element ref and trigger function
 */
export const useStaggeredAnimation = ({
  staggerDelay = 150,
  animationType = 'fadeInUp'
} = {}) => {
  const containerRef = useRef(null)

  const trigger = () => {
    const container = containerRef.current
    if (!container) return

    const children = Array.from(container.children)
    
    children.forEach((child, index) => {
      // Reset animation
      child.style.opacity = '0'
      child.style.transform = getInitialTransform(animationType)
      child.style.transition = `all 0.6s cubic-bezier(0.4, 0, 0.2, 1)`
      
      // Trigger animation with delay
      setTimeout(() => {
        child.style.opacity = '1'
        child.style.transform = getFinalTransform(animationType)
      }, index * staggerDelay)
    })
  }

  return [containerRef, trigger]
}
