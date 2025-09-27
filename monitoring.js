// Système de monitoring et d'analytics
class Analytics {
  constructor() {
    this.events = []
    this.sessionId = this.generateSessionId()
    this.startTime = Date.now()
    this.isEnabled = process.env.NODE_ENV === 'production'
  }

  generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9)
  }

  // Enregistrer un événement
  track(eventName, properties = {}) {
    if (!this.isEnabled) {
      console.log('Analytics Event:', eventName, properties)
      return
    }

    const event = {
      name: eventName,
      properties: {
        ...properties,
        sessionId: this.sessionId,
        timestamp: Date.now(),
        url: window.location.pathname,
        userAgent: navigator.userAgent,
        viewport: {
          width: window.innerWidth,
          height: window.innerHeight
        }
      }
    }

    this.events.push(event)
    this.sendEvent(event)
  }

  // Envoyer l'événement au service d'analytics
  async sendEvent(event) {
    try {
      // En production, envoyer vers un service d'analytics réel
      // Ici on simule avec un log
      if (this.isEnabled) {
        await fetch('/api/analytics', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(event)
        })
      }
    } catch (error) {
      console.warn('Erreur envoi analytics:', error)
    }
  }

  // Événements spécifiques à l'application
  trackPageView(page) {
    this.track('page_view', { page })
  }

  trackFileUpload(fileSize, fileType) {
    this.track('file_upload', { 
      fileSize: Math.round(fileSize / 1024), // en KB
      fileType 
    })
  }

  trackClassification(confidence, culture, processingTime) {
    this.track('classification_completed', {
      confidence,
      culture,
      processingTime
    })
  }

  trackExport(format, resultCount) {
    this.track('export_data', {
      format,
      resultCount
    })
  }

  trackError(error, context = {}) {
    this.track('error_occurred', {
      error: error.message,
      stack: error.stack,
      context
    })
  }

  trackPerformance(metric, value, unit = 'ms') {
    this.track('performance_metric', {
      metric,
      value,
      unit
    })
  }

  // Métriques de session
  getSessionMetrics() {
    return {
      sessionId: this.sessionId,
      duration: Date.now() - this.startTime,
      eventCount: this.events.length,
      startTime: this.startTime
    }
  }
}

// Instance globale d'analytics
export const analytics = new Analytics()

// Système de monitoring des erreurs
class ErrorMonitor {
  constructor() {
    this.errors = []
    this.setupGlobalErrorHandling()
  }

  setupGlobalErrorHandling() {
    // Erreurs JavaScript non capturées
    window.addEventListener('error', (event) => {
      this.captureError(event.error, {
        type: 'javascript_error',
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno
      })
    })

    // Promesses rejetées non capturées
    window.addEventListener('unhandledrejection', (event) => {
      this.captureError(event.reason, {
        type: 'unhandled_promise_rejection'
      })
    })

    // Erreurs de ressources
    window.addEventListener('error', (event) => {
      if (event.target !== window) {
        this.captureError(new Error(`Resource failed to load: ${event.target.src || event.target.href}`), {
          type: 'resource_error',
          element: event.target.tagName,
          source: event.target.src || event.target.href
        })
      }
    }, true)
  }

  captureError(error, context = {}) {
    const errorInfo = {
      message: error.message || 'Unknown error',
      stack: error.stack,
      timestamp: Date.now(),
      url: window.location.href,
      userAgent: navigator.userAgent,
      context
    }

    this.errors.push(errorInfo)
    
    // Envoyer à analytics
    analytics.trackError(error, context)

    // Logger en développement
    if (process.env.NODE_ENV === 'development') {
      console.error('Error captured:', errorInfo)
    }

    // Limiter le nombre d'erreurs stockées
    if (this.errors.length > 100) {
      this.errors = this.errors.slice(-50)
    }
  }

  getErrors() {
    return this.errors
  }

  clearErrors() {
    this.errors = []
  }
}

// Instance globale de monitoring d'erreurs
export const errorMonitor = new ErrorMonitor()

// Système de monitoring des performances
class PerformanceMonitor {
  constructor() {
    this.metrics = new Map()
    this.observers = new Map()
    this.setupPerformanceObservers()
  }

  setupPerformanceObservers() {
    // Observer pour les métriques de navigation
    if ('PerformanceObserver' in window) {
      try {
        // Métriques de chargement
        const navigationObserver = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            this.recordMetric('navigation', {
              domContentLoaded: entry.domContentLoadedEventEnd - entry.domContentLoadedEventStart,
              loadComplete: entry.loadEventEnd - entry.loadEventStart,
              firstPaint: entry.responseEnd - entry.requestStart
            })
          }
        })
        navigationObserver.observe({ entryTypes: ['navigation'] })

        // Métriques de ressources
        const resourceObserver = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            if (entry.duration > 1000) { // Ressources lentes (>1s)
              this.recordMetric('slow_resource', {
                name: entry.name,
                duration: entry.duration,
                size: entry.transferSize
              })
            }
          }
        })
        resourceObserver.observe({ entryTypes: ['resource'] })

        // Métriques de performance utilisateur
        if ('web-vitals' in window) {
          // Core Web Vitals (si disponible)
          const vitalsObserver = new PerformanceObserver((list) => {
            for (const entry of list.getEntries()) {
              this.recordMetric('web_vital', {
                name: entry.name,
                value: entry.value,
                rating: entry.rating
              })
            }
          })
          vitalsObserver.observe({ entryTypes: ['largest-contentful-paint', 'first-input', 'cumulative-layout-shift'] })
        }

      } catch (error) {
        console.warn('Performance observers not supported:', error)
      }
    }
  }

  recordMetric(name, data) {
    if (!this.metrics.has(name)) {
      this.metrics.set(name, [])
    }
    
    const metric = {
      ...data,
      timestamp: Date.now()
    }
    
    this.metrics.get(name).push(metric)
    
    // Envoyer à analytics
    analytics.trackPerformance(name, data.duration || data.value || 0)

    // Limiter le nombre de métriques stockées
    const metrics = this.metrics.get(name)
    if (metrics.length > 100) {
      this.metrics.set(name, metrics.slice(-50))
    }
  }

  getMetrics(name) {
    return this.metrics.get(name) || []
  }

  getAllMetrics() {
    const result = {}
    for (const [name, metrics] of this.metrics.entries()) {
      result[name] = metrics
    }
    return result
  }

  // Mesurer une fonction
  measure(name, fn) {
    const start = performance.now()
    const result = fn()
    const duration = performance.now() - start
    
    this.recordMetric('function_performance', {
      name,
      duration
    })
    
    return result
  }

  // Mesurer une fonction asynchrone
  async measureAsync(name, fn) {
    const start = performance.now()
    const result = await fn()
    const duration = performance.now() - start
    
    this.recordMetric('async_function_performance', {
      name,
      duration
    })
    
    return result
  }
}

// Instance globale de monitoring des performances
export const performanceMonitor = new PerformanceMonitor()

// Système de health check
class HealthMonitor {
  constructor() {
    this.checks = new Map()
    this.status = 'healthy'
    this.lastCheck = null
  }

  // Ajouter un check de santé
  addCheck(name, checkFn, interval = 30000) {
    const check = {
      name,
      checkFn,
      interval,
      lastRun: null,
      lastResult: null,
      failures: 0
    }

    this.checks.set(name, check)
    
    // Programmer l'exécution périodique
    setInterval(() => {
      this.runCheck(name)
    }, interval)

    // Exécuter immédiatement
    this.runCheck(name)
  }

  // Exécuter un check spécifique
  async runCheck(name) {
    const check = this.checks.get(name)
    if (!check) return

    try {
      const result = await check.checkFn()
      check.lastRun = Date.now()
      check.lastResult = result
      check.failures = 0

      if (!result.healthy) {
        console.warn(`Health check failed: ${name}`, result)
        analytics.track('health_check_failed', { check: name, reason: result.message })
      }

    } catch (error) {
      check.failures++
      check.lastResult = {
        healthy: false,
        message: error.message,
        error: true
      }

      console.error(`Health check error: ${name}`, error)
      analytics.trackError(error, { healthCheck: name })
    }
  }

  // Obtenir le statut global
  getStatus() {
    let overallHealthy = true
    const checkResults = {}

    for (const [name, check] of this.checks.entries()) {
      checkResults[name] = check.lastResult
      if (check.lastResult && !check.lastResult.healthy) {
        overallHealthy = false
      }
    }

    return {
      healthy: overallHealthy,
      timestamp: Date.now(),
      checks: checkResults
    }
  }
}

// Instance globale de health monitoring
export const healthMonitor = new HealthMonitor()

// Checks de santé par défaut
healthMonitor.addCheck('api_connectivity', async () => {
  try {
    const response = await fetch('/api/health', { 
      method: 'GET',
      timeout: 5000 
    })
    return {
      healthy: response.ok,
      message: response.ok ? 'API accessible' : `API error: ${response.status}`
    }
  } catch (error) {
    return {
      healthy: false,
      message: `API unreachable: ${error.message}`
    }
  }
})

healthMonitor.addCheck('local_storage', async () => {
  try {
    const testKey = 'health_check_test'
    localStorage.setItem(testKey, 'test')
    const value = localStorage.getItem(testKey)
    localStorage.removeItem(testKey)
    
    return {
      healthy: value === 'test',
      message: value === 'test' ? 'LocalStorage working' : 'LocalStorage failed'
    }
  } catch (error) {
    return {
      healthy: false,
      message: `LocalStorage error: ${error.message}`
    }
  }
})

// Hook React pour utiliser le monitoring
export const useMonitoring = () => {
  return {
    analytics,
    errorMonitor,
    performanceMonitor,
    healthMonitor,
    trackEvent: analytics.track.bind(analytics),
    trackError: analytics.trackError.bind(analytics),
    trackPerformance: analytics.trackPerformance.bind(analytics)
  }
}

export default {
  analytics,
  errorMonitor,
  performanceMonitor,
  healthMonitor,
  useMonitoring
}
