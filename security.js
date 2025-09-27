// Middleware de sécurité et rate limiting
import rateLimit from 'express-rate-limit'
import helmet from 'helmet'
import cors from 'cors'

// Configuration CORS sécurisée
export const corsConfig = cors({
  origin: process.env.NODE_ENV === 'production' 
    ? ['https://your-app.vercel.app', 'https://*.vercel.app']
    : ['http://localhost:3000', 'http://localhost:5173'],
  methods: ['GET', 'POST'],
  allowedHeaders: ['Content-Type', 'Authorization'],
  credentials: true,
  maxAge: 86400 // 24 heures
})

// Rate limiting pour les uploads
export const uploadRateLimit = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 10, // Maximum 10 uploads par IP par fenêtre
  message: {
    error: 'Trop de tentatives d\'upload. Réessayez dans 15 minutes.',
    retryAfter: 15 * 60
  },
  standardHeaders: true,
  legacyHeaders: false,
  handler: (req, res) => {
    res.status(429).json({
      error: 'Trop de tentatives d\'upload',
      message: 'Vous avez dépassé la limite d\'uploads. Réessayez dans 15 minutes.',
      retryAfter: Math.round(req.rateLimit.resetTime / 1000)
    })
  }
})

// Rate limiting pour les classifications
export const classifyRateLimit = rateLimit({
  windowMs: 60 * 1000, // 1 minute
  max: 5, // Maximum 5 classifications par minute
  message: {
    error: 'Trop de demandes de classification. Réessayez dans une minute.',
    retryAfter: 60
  },
  standardHeaders: true,
  legacyHeaders: false
})

// Rate limiting général pour l'API
export const generalRateLimit = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // Maximum 100 requêtes par IP par fenêtre
  message: {
    error: 'Trop de requêtes. Réessayez plus tard.',
    retryAfter: 15 * 60
  }
})

// Configuration Helmet pour la sécurité des en-têtes
export const helmetConfig = helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      styleSrc: ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
      fontSrc: ["'self'", "https://fonts.gstatic.com"],
      imgSrc: ["'self'", "data:", "https:"],
      scriptSrc: ["'self'"],
      connectSrc: ["'self'", "https://api.vercel.com"],
      frameSrc: ["'none'"],
      objectSrc: ["'none'"],
      upgradeInsecureRequests: []
    }
  },
  crossOriginEmbedderPolicy: false,
  hsts: {
    maxAge: 31536000,
    includeSubDomains: true,
    preload: true
  }
})

// Middleware de validation des fichiers
export const validateFileMiddleware = (req, res, next) => {
  const allowedMimeTypes = [
    'image/jpeg',
    'image/png', 
    'image/tiff',
    'image/geotiff'
  ]
  
  const maxFileSize = 10 * 1024 * 1024 // 10MB

  if (req.file) {
    // Vérifier le type MIME
    if (!allowedMimeTypes.includes(req.file.mimetype)) {
      return res.status(400).json({
        error: 'Type de fichier non autorisé',
        allowedTypes: ['JPEG', 'PNG', 'TIFF', 'GeoTIFF']
      })
    }

    // Vérifier la taille
    if (req.file.size > maxFileSize) {
      return res.status(400).json({
        error: 'Fichier trop volumineux',
        maxSize: '10MB',
        receivedSize: `${(req.file.size / 1024 / 1024).toFixed(2)}MB`
      })
    }

    // Vérifier l'extension
    const allowedExtensions = ['.jpg', '.jpeg', '.png', '.tif', '.tiff']
    const fileExtension = req.file.originalname.toLowerCase().slice(-4)
    
    if (!allowedExtensions.some(ext => fileExtension.endsWith(ext))) {
      return res.status(400).json({
        error: 'Extension de fichier non autorisée',
        allowedExtensions
      })
    }
  }

  next()
}

// Middleware de logging sécurisé
export const secureLogger = (req, res, next) => {
  const startTime = Date.now()
  
  // Ne pas logger les données sensibles
  const logData = {
    method: req.method,
    url: req.url.split('?')[0], // Enlever les query params
    ip: req.ip || req.connection.remoteAddress,
    userAgent: req.get('User-Agent'),
    timestamp: new Date().toISOString()
  }

  res.on('finish', () => {
    const duration = Date.now() - startTime
    console.log(JSON.stringify({
      ...logData,
      statusCode: res.statusCode,
      duration: `${duration}ms`,
      success: res.statusCode < 400
    }))
  })

  next()
}

// Middleware de nettoyage des données d'entrée
export const sanitizeInput = (req, res, next) => {
  // Nettoyer les chaînes de caractères
  const sanitizeString = (str) => {
    if (typeof str !== 'string') return str
    return str
      .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '') // Enlever les scripts
      .replace(/javascript:/gi, '') // Enlever javascript:
      .replace(/on\w+\s*=/gi, '') // Enlever les event handlers
      .trim()
  }

  // Sanitiser récursivement les objets
  const sanitizeObject = (obj) => {
    if (obj === null || typeof obj !== 'object') {
      return typeof obj === 'string' ? sanitizeString(obj) : obj
    }

    if (Array.isArray(obj)) {
      return obj.map(sanitizeObject)
    }

    const sanitized = {}
    for (const [key, value] of Object.entries(obj)) {
      sanitized[key] = sanitizeObject(value)
    }
    return sanitized
  }

  // Appliquer la sanitisation
  if (req.body) {
    req.body = sanitizeObject(req.body)
  }
  if (req.query) {
    req.query = sanitizeObject(req.query)
  }

  next()
}

// Middleware de gestion des erreurs sécurisé
export const secureErrorHandler = (err, req, res, next) => {
  // Logger l'erreur complète côté serveur
  console.error('Erreur serveur:', {
    error: err.message,
    stack: process.env.NODE_ENV === 'development' ? err.stack : undefined,
    url: req.url,
    method: req.method,
    ip: req.ip,
    timestamp: new Date().toISOString()
  })

  // Réponse sécurisée côté client
  const isDevelopment = process.env.NODE_ENV === 'development'
  
  res.status(err.status || 500).json({
    error: 'Une erreur est survenue',
    message: isDevelopment ? err.message : 'Erreur interne du serveur',
    ...(isDevelopment && { stack: err.stack })
  })
}

// Configuration de sécurité pour les cookies
export const secureCookieConfig = {
  httpOnly: true,
  secure: process.env.NODE_ENV === 'production',
  sameSite: 'strict',
  maxAge: 24 * 60 * 60 * 1000 // 24 heures
}

export default {
  corsConfig,
  uploadRateLimit,
  classifyRateLimit,
  generalRateLimit,
  helmetConfig,
  validateFileMiddleware,
  secureLogger,
  sanitizeInput,
  secureErrorHandler,
  secureCookieConfig
}
