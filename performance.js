// Utilitaires d'optimisation des performances
import { useState, useEffect, useCallback, useMemo } from 'react'

// Hook pour le debouncing
export const useDebounce = (value, delay) => {
  const [debouncedValue, setDebouncedValue] = useState(value)

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value)
    }, delay)

    return () => {
      clearTimeout(handler)
    }
  }, [value, delay])

  return debouncedValue
}

// Hook pour le throttling
export const useThrottle = (callback, delay) => {
  const [lastCall, setLastCall] = useState(0)

  return useCallback((...args) => {
    const now = Date.now()
    if (now - lastCall >= delay) {
      setLastCall(now)
      return callback(...args)
    }
  }, [callback, delay, lastCall])
}

// Hook pour la gestion du cache local
export const useLocalStorage = (key, initialValue) => {
  const [storedValue, setStoredValue] = useState(() => {
    try {
      const item = window.localStorage.getItem(key)
      return item ? JSON.parse(item) : initialValue
    } catch (error) {
      console.warn(`Erreur lecture localStorage pour ${key}:`, error)
      return initialValue
    }
  })

  const setValue = useCallback((value) => {
    try {
      const valueToStore = value instanceof Function ? value(storedValue) : value
      setStoredValue(valueToStore)
      window.localStorage.setItem(key, JSON.stringify(valueToStore))
    } catch (error) {
      console.warn(`Erreur écriture localStorage pour ${key}:`, error)
    }
  }, [key, storedValue])

  const removeValue = useCallback(() => {
    try {
      window.localStorage.removeItem(key)
      setStoredValue(initialValue)
    } catch (error) {
      console.warn(`Erreur suppression localStorage pour ${key}:`, error)
    }
  }, [key, initialValue])

  return [storedValue, setValue, removeValue]
}

// Hook pour la détection de la connexion réseau
export const useNetworkStatus = () => {
  const [isOnline, setIsOnline] = useState(navigator.onLine)
  const [connectionType, setConnectionType] = useState('unknown')

  useEffect(() => {
    const handleOnline = () => setIsOnline(true)
    const handleOffline = () => setIsOnline(false)

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    // Détection du type de connexion si disponible
    if ('connection' in navigator) {
      const connection = navigator.connection
      setConnectionType(connection.effectiveType || 'unknown')
      
      const handleConnectionChange = () => {
        setConnectionType(connection.effectiveType || 'unknown')
      }
      
      connection.addEventListener('change', handleConnectionChange)
      
      return () => {
        window.removeEventListener('online', handleOnline)
        window.removeEventListener('offline', handleOffline)
        connection.removeEventListener('change', handleConnectionChange)
      }
    }

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  return { isOnline, connectionType }
}

// Système de cache en mémoire avec TTL
class MemoryCache {
  constructor() {
    this.cache = new Map()
    this.timers = new Map()
  }

  set(key, value, ttl = 300000) { // TTL par défaut: 5 minutes
    // Nettoyer l'ancien timer s'il existe
    if (this.timers.has(key)) {
      clearTimeout(this.timers.get(key))
    }

    // Stocker la valeur
    this.cache.set(key, {
      value,
      timestamp: Date.now(),
      ttl
    })

    // Programmer l'expiration
    const timer = setTimeout(() => {
      this.delete(key)
    }, ttl)

    this.timers.set(key, timer)
  }

  get(key) {
    const item = this.cache.get(key)
    if (!item) return null

    // Vérifier si l'item a expiré
    if (Date.now() - item.timestamp > item.ttl) {
      this.delete(key)
      return null
    }

    return item.value
  }

  delete(key) {
    this.cache.delete(key)
    if (this.timers.has(key)) {
      clearTimeout(this.timers.get(key))
      this.timers.delete(key)
    }
  }

  clear() {
    this.cache.clear()
    this.timers.forEach(timer => clearTimeout(timer))
    this.timers.clear()
  }

  size() {
    return this.cache.size
  }

  // Nettoyer les entrées expirées
  cleanup() {
    const now = Date.now()
    for (const [key, item] of this.cache.entries()) {
      if (now - item.timestamp > item.ttl) {
        this.delete(key)
      }
    }
  }
}

// Instance globale du cache
export const memoryCache = new MemoryCache()

// Nettoyer le cache toutes les 10 minutes
setInterval(() => {
  memoryCache.cleanup()
}, 10 * 60 * 1000)

// Utilitaire pour compresser les images côté client
export const compressImage = (file, maxWidth = 1920, maxHeight = 1080, quality = 0.8) => {
  return new Promise((resolve) => {
    const canvas = document.createElement('canvas')
    const ctx = canvas.getContext('2d')
    const img = new Image()

    img.onload = () => {
      // Calculer les nouvelles dimensions
      let { width, height } = img
      
      if (width > maxWidth || height > maxHeight) {
        const ratio = Math.min(maxWidth / width, maxHeight / height)
        width *= ratio
        height *= ratio
      }

      // Redimensionner l'image
      canvas.width = width
      canvas.height = height
      ctx.drawImage(img, 0, 0, width, height)

      // Convertir en blob
      canvas.toBlob(resolve, file.type, quality)
    }

    img.src = URL.createObjectURL(file)
  })
}

// Utilitaire pour le lazy loading des images
export const useLazyImage = (src, placeholder = null) => {
  const [imageSrc, setImageSrc] = useState(placeholder)
  const [isLoaded, setIsLoaded] = useState(false)
  const [isError, setIsError] = useState(false)

  useEffect(() => {
    if (!src) return

    const img = new Image()
    
    img.onload = () => {
      setImageSrc(src)
      setIsLoaded(true)
      setIsError(false)
    }

    img.onerror = () => {
      setIsError(true)
      setIsLoaded(false)
    }

    img.src = src
  }, [src])

  return { imageSrc, isLoaded, isError }
}

// Utilitaire pour mesurer les performances
export const performanceMonitor = {
  marks: new Map(),
  
  start(name) {
    this.marks.set(name, performance.now())
  },

  end(name) {
    const startTime = this.marks.get(name)
    if (startTime) {
      const duration = performance.now() - startTime
      this.marks.delete(name)
      return duration
    }
    return null
  },

  measure(name, fn) {
    this.start(name)
    const result = fn()
    const duration = this.end(name)
    
    if (process.env.NODE_ENV === 'development') {
      console.log(`Performance [${name}]: ${duration.toFixed(2)}ms`)
    }
    
    return result
  },

  async measureAsync(name, fn) {
    this.start(name)
    const result = await fn()
    const duration = this.end(name)
    
    if (process.env.NODE_ENV === 'development') {
      console.log(`Performance [${name}]: ${duration.toFixed(2)}ms`)
    }
    
    return result
  }
}

// Hook pour l'optimisation des re-rendus
export const useOptimizedCallback = (callback, deps) => {
  return useCallback(callback, deps)
}

export const useOptimizedMemo = (factory, deps) => {
  return useMemo(factory, deps)
}

// Utilitaire pour le préchargement des ressources
export const preloadResource = (url, type = 'fetch') => {
  return new Promise((resolve, reject) => {
    const link = document.createElement('link')
    link.rel = 'preload'
    link.href = url
    
    switch (type) {
      case 'image':
        link.as = 'image'
        break
      case 'script':
        link.as = 'script'
        break
      case 'style':
        link.as = 'style'
        break
      default:
        link.as = 'fetch'
        link.crossOrigin = 'anonymous'
    }

    link.onload = resolve
    link.onerror = reject
    
    document.head.appendChild(link)
  })
}

// Utilitaire pour la gestion des erreurs avec retry
export const withRetry = async (fn, maxRetries = 3, delay = 1000) => {
  let lastError
  
  for (let i = 0; i <= maxRetries; i++) {
    try {
      return await fn()
    } catch (error) {
      lastError = error
      
      if (i === maxRetries) {
        throw lastError
      }
      
      // Attendre avant de réessayer (backoff exponentiel)
      await new Promise(resolve => setTimeout(resolve, delay * Math.pow(2, i)))
    }
  }
}

// Utilitaire pour l'optimisation des bundles
export const loadChunk = (chunkName) => {
  return import(/* webpackChunkName: "[request]" */ `../chunks/${chunkName}`)
}

export default {
  useDebounce,
  useThrottle,
  useLocalStorage,
  useNetworkStatus,
  memoryCache,
  compressImage,
  useLazyImage,
  performanceMonitor,
  useOptimizedCallback,
  useOptimizedMemo,
  preloadResource,
  withRetry,
  loadChunk
}
