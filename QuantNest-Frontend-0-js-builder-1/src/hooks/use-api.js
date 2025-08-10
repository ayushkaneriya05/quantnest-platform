import { useState, useCallback } from 'react'
import api from '@/services/api'

export function useApi() {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)

  const execute = useCallback(async (apiCall, options = {}) => {
    const { 
      onSuccess, 
      onError, 
      successMessage,
      errorMessage = 'An error occurred',
      resetErrorOnCall = true 
    } = options

    if (resetErrorOnCall) {
      setError(null)
    }
    
    setIsLoading(true)

    try {
      const result = await apiCall()
      
      if (onSuccess) {
        onSuccess(result)
      }

      if (successMessage) {
        return {
          success: true,
          data: result,
          message: successMessage
        }
      }

      return {
        success: true,
        data: result
      }
    } catch (err) {
      console.error('API Error:', err)
      
      let errorMsg = errorMessage
      
      if (err.response?.data) {
        if (typeof err.response.data === 'string') {
          errorMsg = err.response.data
        } else if (err.response.data.detail) {
          errorMsg = err.response.data.detail
        } else if (err.response.data.message) {
          errorMsg = err.response.data.message
        }
      } else if (err.message) {
        errorMsg = err.message
      }

      setError(errorMsg)

      if (onError) {
        onError(err)
      }

      return {
        success: false,
        error: errorMsg
      }
    } finally {
      setIsLoading(false)
    }
  }, [])

  const clearError = useCallback(() => {
    setError(null)
  }, [])

  return {
    isLoading,
    error,
    execute,
    clearError
  }
}

// Specialized hook for form submissions
export function useFormSubmit() {
  const { isLoading, error, execute, clearError } = useApi()
  const [fieldErrors, setFieldErrors] = useState({})

  const submit = useCallback(async (apiCall, options = {}) => {
    setFieldErrors({})
    
    const result = await execute(apiCall, options)
    
    // Handle field-specific errors
    if (!result.success && result.error && typeof result.error === 'object') {
      setFieldErrors(result.error)
    }
    
    return result
  }, [execute])

  const clearFieldError = useCallback((fieldName) => {
    setFieldErrors(prev => ({
      ...prev,
      [fieldName]: null
    }))
  }, [])

  const getFieldError = useCallback((fieldName) => {
    const error = fieldErrors[fieldName]
    if (error) {
      if (Array.isArray(error)) {
        return error[0]
      }
      return error
    }
    return null
  }, [fieldErrors])

  return {
    isLoading,
    error,
    fieldErrors,
    submit,
    clearError,
    clearFieldError,
    getFieldError
  }
}

// Hook for data fetching with caching
export function useApiData(apiCall, dependencies = [], options = {}) {
  const [data, setData] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const { cache = false, defaultValue = null } = options

  const fetchData = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      const result = await apiCall()
      setData(result)
    } catch (err) {
      console.error('API Data Fetch Error:', err)
      setError(err.response?.data?.detail || err.message || 'Failed to fetch data')
      setData(defaultValue)
    } finally {
      setIsLoading(false)
    }
  }, dependencies)

  React.useEffect(() => {
    fetchData()
  }, [fetchData])

  const refetch = useCallback(() => {
    fetchData()
  }, [fetchData])

  return {
    data,
    isLoading,
    error,
    refetch
  }
}
