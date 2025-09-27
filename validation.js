// Système de validation et de sécurisation des données
import crypto from 'crypto'

// Schémas de validation
export const validationSchemas = {
  // Validation des fichiers uploadés
  fileUpload: {
    maxSize: 10 * 1024 * 1024, // 10MB
    allowedTypes: [
      'image/jpeg',
      'image/png',
      'image/tiff',
      'image/geotiff'
    ],
    allowedExtensions: ['.jpg', '.jpeg', '.png', '.tif', '.tiff'],
    
    validate(file) {
      const errors = []

      if (!file) {
        errors.push('Aucun fichier fourni')
        return { isValid: false, errors }
      }

      // Vérifier la taille
      if (file.size > this.maxSize) {
        errors.push(`Fichier trop volumineux. Maximum: ${this.maxSize / 1024 / 1024}MB`)
      }

      // Vérifier le type MIME
      if (!this.allowedTypes.includes(file.type)) {
        errors.push(`Type de fichier non supporté. Types autorisés: ${this.allowedTypes.join(', ')}`)
      }

      // Vérifier l'extension
      const extension = file.name.toLowerCase().slice(file.name.lastIndexOf('.'))
      if (!this.allowedExtensions.includes(extension)) {
        errors.push(`Extension non autorisée. Extensions autorisées: ${this.allowedExtensions.join(', ')}`)
      }

      // Vérifier le nom de fichier
      if (!/^[a-zA-Z0-9._-]+$/.test(file.name)) {
        errors.push('Nom de fichier invalide. Utilisez uniquement des lettres, chiffres, points, tirets et underscores')
      }

      return {
        isValid: errors.length === 0,
        errors
      }
    }
  },

  // Validation des coordonnées géographiques
  coordinates: {
    validate(coords) {
      const errors = []

      if (!coords || typeof coords !== 'object') {
        errors.push('Coordonnées requises')
        return { isValid: false, errors }
      }

      const { lat, lng } = coords

      // Vérifier la latitude
      if (typeof lat !== 'number' || lat < -90 || lat > 90) {
        errors.push('Latitude invalide (doit être entre -90 et 90)')
      }

      // Vérifier la longitude
      if (typeof lng !== 'number' || lng < -180 || lng > 180) {
        errors.push('Longitude invalide (doit être entre -180 et 180)')
      }

      return {
        isValid: errors.length === 0,
        errors
      }
    }
  },

  // Validation des paramètres d'export
  exportParams: {
    allowedFormats: ['csv', 'geojson', 'pdf'],
    
    validate(params) {
      const errors = []

      if (!params || typeof params !== 'object') {
        errors.push('Paramètres d\'export requis')
        return { isValid: false, errors }
      }

      const { format, results } = params

      // Vérifier le format
      if (!format || !this.allowedFormats.includes(format)) {
        errors.push(`Format invalide. Formats autorisés: ${this.allowedFormats.join(', ')}`)
      }

      // Vérifier les résultats
      if (!results || !Array.isArray(results) || results.length === 0) {
        errors.push('Aucun résultat à exporter')
      }

      return {
        isValid: errors.length === 0,
        errors
      }
    }
  }
}

// Utilitaires de sanitisation
export const sanitize = {
  // Nettoyer une chaîne de caractères
  string(input, options = {}) {
    if (typeof input !== 'string') return input

    let cleaned = input

    // Enlever les scripts malveillants
    if (options.removeScripts !== false) {
      cleaned = cleaned.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
    }

    // Enlever les event handlers JavaScript
    if (options.removeEventHandlers !== false) {
      cleaned = cleaned.replace(/on\w+\s*=/gi, '')
    }

    // Enlever javascript: URLs
    if (options.removeJavaScriptUrls !== false) {
      cleaned = cleaned.replace(/javascript:/gi, '')
    }

    // Limiter la longueur
    if (options.maxLength) {
      cleaned = cleaned.slice(0, options.maxLength)
    }

    // Trim par défaut
    if (options.trim !== false) {
      cleaned = cleaned.trim()
    }

    return cleaned
  },

  // Nettoyer un nom de fichier
  filename(filename) {
    if (typeof filename !== 'string') return filename

    return filename
      .replace(/[^a-zA-Z0-9._-]/g, '_') // Remplacer les caractères non autorisés
      .replace(/_{2,}/g, '_') // Remplacer les underscores multiples
      .replace(/^_+|_+$/g, '') // Enlever les underscores en début/fin
      .slice(0, 255) // Limiter la longueur
  },

  // Nettoyer un objet récursivement
  object(obj, options = {}) {
    if (obj === null || typeof obj !== 'object') {
      return typeof obj === 'string' ? this.string(obj, options) : obj
    }

    if (Array.isArray(obj)) {
      return obj.map(item => this.object(item, options))
    }

    const sanitized = {}
    for (const [key, value] of Object.entries(obj)) {
      const cleanKey = this.string(key, { maxLength: 100 })
      sanitized[cleanKey] = this.object(value, options)
    }

    return sanitized
  }
}

// Utilitaires de chiffrement
export const encryption = {
  // Générer une clé aléatoire
  generateKey(length = 32) {
    return crypto.randomBytes(length).toString('hex')
  },

  // Chiffrer des données sensibles
  encrypt(text, key) {
    if (!key) throw new Error('Clé de chiffrement requise')
    
    const algorithm = 'aes-256-gcm'
    const iv = crypto.randomBytes(16)
    const cipher = crypto.createCipher(algorithm, key)
    
    let encrypted = cipher.update(text, 'utf8', 'hex')
    encrypted += cipher.final('hex')
    
    return {
      encrypted,
      iv: iv.toString('hex'),
      algorithm
    }
  },

  // Déchiffrer des données
  decrypt(encryptedData, key) {
    if (!key) throw new Error('Clé de déchiffrement requise')
    
    const { encrypted, iv, algorithm } = encryptedData
    const decipher = crypto.createDecipher(algorithm, key)
    
    let decrypted = decipher.update(encrypted, 'hex', 'utf8')
    decrypted += decipher.final('utf8')
    
    return decrypted
  },

  // Hasher des données (pour les mots de passe, etc.)
  hash(data, salt = null) {
    const actualSalt = salt || crypto.randomBytes(16).toString('hex')
    const hash = crypto.pbkdf2Sync(data, actualSalt, 10000, 64, 'sha512').toString('hex')
    
    return {
      hash,
      salt: actualSalt
    }
  },

  // Vérifier un hash
  verifyHash(data, hash, salt) {
    const computed = crypto.pbkdf2Sync(data, salt, 10000, 64, 'sha512').toString('hex')
    return computed === hash
  }
}

// Utilitaires de sécurité
export const security = {
  // Générer un token sécurisé
  generateToken(length = 32) {
    return crypto.randomBytes(length).toString('base64url')
  },

  // Vérifier l'origine de la requête
  verifyOrigin(origin, allowedOrigins) {
    if (!origin) return false
    
    const allowed = Array.isArray(allowedOrigins) ? allowedOrigins : [allowedOrigins]
    return allowed.some(allowed => {
      if (allowed === '*') return true
      if (allowed.includes('*')) {
        const pattern = allowed.replace(/\*/g, '.*')
        return new RegExp(`^${pattern}$`).test(origin)
      }
      return allowed === origin
    })
  },

  // Vérifier la force d'un mot de passe
  checkPasswordStrength(password) {
    const checks = {
      length: password.length >= 8,
      lowercase: /[a-z]/.test(password),
      uppercase: /[A-Z]/.test(password),
      numbers: /\d/.test(password),
      symbols: /[!@#$%^&*(),.?":{}|<>]/.test(password)
    }

    const score = Object.values(checks).filter(Boolean).length
    
    return {
      score,
      maxScore: 5,
      strength: score < 2 ? 'weak' : score < 4 ? 'medium' : 'strong',
      checks
    }
  },

  // Détecter des tentatives d'injection
  detectInjection(input) {
    const patterns = [
      /<script/i,
      /javascript:/i,
      /on\w+\s*=/i,
      /eval\s*\(/i,
      /expression\s*\(/i,
      /vbscript:/i,
      /data:text\/html/i
    ]

    return patterns.some(pattern => pattern.test(input))
  },

  // Rate limiting côté client
  rateLimiter: new Map(),
  
  checkRateLimit(key, maxRequests = 10, windowMs = 60000) {
    const now = Date.now()
    const windowStart = now - windowMs
    
    if (!this.rateLimiter.has(key)) {
      this.rateLimiter.set(key, [])
    }
    
    const requests = this.rateLimiter.get(key)
    
    // Nettoyer les anciennes requêtes
    const validRequests = requests.filter(time => time > windowStart)
    
    if (validRequests.length >= maxRequests) {
      return {
        allowed: false,
        remaining: 0,
        resetTime: Math.min(...validRequests) + windowMs
      }
    }
    
    validRequests.push(now)
    this.rateLimiter.set(key, validRequests)
    
    return {
      allowed: true,
      remaining: maxRequests - validRequests.length,
      resetTime: now + windowMs
    }
  }
}

// Middleware de validation pour les APIs
export const createValidationMiddleware = (schema) => {
  return (req, res, next) => {
    const validation = schema.validate(req.body)
    
    if (!validation.isValid) {
      return res.status(400).json({
        error: 'Données invalides',
        details: validation.errors
      })
    }
    
    // Sanitiser les données
    req.body = sanitize.object(req.body)
    
    next()
  }
}

// Hook React pour la validation
export const useValidation = () => {
  const [errors, setErrors] = useState({})
  
  const validate = useCallback((data, schema) => {
    const validation = schema.validate(data)
    
    if (!validation.isValid) {
      const errorObj = {}
      validation.errors.forEach((error, index) => {
        errorObj[`error_${index}`] = error
      })
      setErrors(errorObj)
      return false
    }
    
    setErrors({})
    return true
  }, [])
  
  const clearErrors = useCallback(() => {
    setErrors({})
  }, [])
  
  return {
    errors,
    validate,
    clearErrors,
    hasErrors: Object.keys(errors).length > 0
  }
}

export default {
  validationSchemas,
  sanitize,
  encryption,
  security,
  createValidationMiddleware,
  useValidation
}
