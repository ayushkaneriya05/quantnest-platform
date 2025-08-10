// Email validation
export const isValidEmail = (email) => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(email)
}

// Password validation
export const validatePassword = (password) => {
  const errors = []
  
  if (password.length < 8) {
    errors.push('Password must be at least 8 characters long')
  }
  
  if (!/[A-Z]/.test(password)) {
    errors.push('Password must contain at least one uppercase letter')
  }
  
  if (!/[a-z]/.test(password)) {
    errors.push('Password must contain at least one lowercase letter')
  }
  
  if (!/\d/.test(password)) {
    errors.push('Password must contain at least one number')
  }
  
  if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
    errors.push('Password must contain at least one special character')
  }
  
  return {
    isValid: errors.length === 0,
    errors
  }
}

// URL validation
export const isValidUrl = (url) => {
  try {
    new URL(url)
    return true
  } catch {
    return false
  }
}

// Username validation
export const validateUsername = (username) => {
  const errors = []
  
  if (username.length < 3) {
    errors.push('Username must be at least 3 characters long')
  }
  
  if (username.length > 30) {
    errors.push('Username must be less than 30 characters')
  }
  
  if (!/^[a-zA-Z0-9_]+$/.test(username)) {
    errors.push('Username can only contain letters, numbers, and underscores')
  }
  
  return {
    isValid: errors.length === 0,
    errors
  }
}

// File validation
export const validateFile = (file, options = {}) => {
  const {
    maxSize = 5 * 1024 * 1024, // 5MB default
    allowedTypes = ['image/jpeg', 'image/png', 'image/webp'],
    allowedExtensions = ['.jpg', '.jpeg', '.png', '.webp']
  } = options
  
  const errors = []
  
  if (file.size > maxSize) {
    errors.push(`File size must be less than ${formatFileSize(maxSize)}`)
  }
  
  if (allowedTypes.length > 0 && !allowedTypes.includes(file.type)) {
    errors.push(`File type must be one of: ${allowedTypes.join(', ')}`)
  }
  
  const fileExtension = '.' + file.name.split('.').pop().toLowerCase()
  if (allowedExtensions.length > 0 && !allowedExtensions.includes(fileExtension)) {
    errors.push(`File extension must be one of: ${allowedExtensions.join(', ')}`)
  }
  
  return {
    isValid: errors.length === 0,
    errors
  }
}

// Format file size for display
export const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// Phone number validation (basic)
export const isValidPhoneNumber = (phone) => {
  const phoneRegex = /^\+?[\d\s\-\(\)]{10,}$/
  return phoneRegex.test(phone)
}

// Social media URL validation
export const validateSocialUrl = (url, platform) => {
  if (!url) return { isValid: true, errors: [] }
  
  if (!isValidUrl(url)) {
    return { isValid: false, errors: ['Please enter a valid URL'] }
  }
  
  const platformPatterns = {
    twitter: /^https?:\/\/(www\.)?(twitter\.com|x\.com)\/.+/,
    linkedin: /^https?:\/\/(www\.)?linkedin\.com\/.+/,
    github: /^https?:\/\/(www\.)?github\.com\/.+/,
    instagram: /^https?:\/\/(www\.)?instagram\.com\/.+/,
    facebook: /^https?:\/\/(www\.)?facebook\.com\/.+/
  }
  
  if (platform && platformPatterns[platform]) {
    if (!platformPatterns[platform].test(url)) {
      return { 
        isValid: false, 
        errors: [`Please enter a valid ${platform.charAt(0).toUpperCase() + platform.slice(1)} URL`] 
      }
    }
  }
  
  return { isValid: true, errors: [] }
}

// Form validation helper
export const validateForm = (data, rules) => {
  const errors = {}
  let isValid = true
  
  for (const [field, value] of Object.entries(data)) {
    const fieldRules = rules[field]
    if (!fieldRules) continue
    
    const fieldErrors = []
    
    // Required validation
    if (fieldRules.required && (!value || value.toString().trim() === '')) {
      fieldErrors.push(`${fieldRules.label || field} is required`)
    }
    
    // Skip other validations if field is empty and not required
    if (!value && !fieldRules.required) continue
    
    // Email validation
    if (fieldRules.email && !isValidEmail(value)) {
      fieldErrors.push('Please enter a valid email address')
    }
    
    // Password validation
    if (fieldRules.password) {
      const passwordValidation = validatePassword(value)
      if (!passwordValidation.isValid) {
        fieldErrors.push(...passwordValidation.errors)
      }
    }
    
    // Username validation
    if (fieldRules.username) {
      const usernameValidation = validateUsername(value)
      if (!usernameValidation.isValid) {
        fieldErrors.push(...usernameValidation.errors)
      }
    }
    
    // URL validation
    if (fieldRules.url && !isValidUrl(value)) {
      fieldErrors.push('Please enter a valid URL')
    }
    
    // Social media URL validation
    if (fieldRules.socialUrl) {
      const socialValidation = validateSocialUrl(value, fieldRules.platform)
      if (!socialValidation.isValid) {
        fieldErrors.push(...socialValidation.errors)
      }
    }
    
    // Min/Max length validation
    if (fieldRules.minLength && value.length < fieldRules.minLength) {
      fieldErrors.push(`${fieldRules.label || field} must be at least ${fieldRules.minLength} characters`)
    }
    
    if (fieldRules.maxLength && value.length > fieldRules.maxLength) {
      fieldErrors.push(`${fieldRules.label || field} must be less than ${fieldRules.maxLength} characters`)
    }
    
    // Custom validation
    if (fieldRules.custom) {
      const customResult = fieldRules.custom(value, data)
      if (customResult !== true) {
        fieldErrors.push(customResult)
      }
    }
    
    if (fieldErrors.length > 0) {
      errors[field] = fieldErrors
      isValid = false
    }
  }
  
  return { isValid, errors }
}

// Date validation
export const isValidDate = (dateString) => {
  const date = new Date(dateString)
  return date instanceof Date && !isNaN(date)
}

// Age validation
export const calculateAge = (birthDate) => {
  const today = new Date()
  const birth = new Date(birthDate)
  let age = today.getFullYear() - birth.getFullYear()
  const monthDiff = today.getMonth() - birth.getMonth()
  
  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
    age--
  }
  
  return age
}

export const isValidAge = (birthDate, minAge = 13, maxAge = 120) => {
  if (!isValidDate(birthDate)) {
    return { isValid: false, errors: ['Please enter a valid date'] }
  }
  
  const age = calculateAge(birthDate)
  
  if (age < minAge) {
    return { isValid: false, errors: [`You must be at least ${minAge} years old`] }
  }
  
  if (age > maxAge) {
    return { isValid: false, errors: ['Please enter a valid birth date'] }
  }
  
  return { isValid: true, errors: [] }
}
