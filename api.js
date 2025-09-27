// Service client pour les appels API
import axios from 'axios';

// Configuration de base d'axios
const api = axios.create({
  baseURL: process.env.NODE_ENV === 'production' 
    ? 'https://your-app.vercel.app' 
    : 'http://localhost:5173',
  timeout: 30000, // 30 secondes
  headers: {
    'Content-Type': 'application/json',
  },
});

// Intercepteur pour les erreurs
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('Erreur API:', error);
    return Promise.reject(error);
  }
);

// Service d'upload de fichiers
export const uploadFile = async (file, onProgress = null) => {
  const formData = new FormData();
  formData.append('file', file);

  try {
    const response = await api.post('/api/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          onProgress(percentCompleted);
        }
      },
    });

    return response.data;
  } catch (error) {
    throw new Error(
      error.response?.data?.error || 'Erreur lors de l\'upload du fichier'
    );
  }
};

// Service de classification
export const classifyImage = async (filePath, coordinates = null) => {
  try {
    const response = await api.post('/api/classify', {
      filePath,
      coordinates,
    });

    return response.data;
  } catch (error) {
    throw new Error(
      error.response?.data?.error || 'Erreur lors de la classification'
    );
  }
};

// Service d'export
export const exportResults = async (format, results) => {
  try {
    const response = await api.post('/api/export', {
      format,
      results,
    }, {
      responseType: 'blob', // Important pour les fichiers
    });

    // Créer un URL pour le téléchargement
    const blob = new Blob([response.data]);
    const url = window.URL.createObjectURL(blob);
    
    // Extraire le nom de fichier depuis les en-têtes
    const contentDisposition = response.headers['content-disposition'];
    let filename = `export_${format}_${Date.now()}`;
    
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename="(.+)"/);
      if (filenameMatch) {
        filename = filenameMatch[1];
      }
    }

    return { url, filename };
  } catch (error) {
    throw new Error(
      error.response?.data?.error || 'Erreur lors de l\'export'
    );
  }
};

// Service de téléchargement de fichier
export const downloadFile = (url, filename) => {
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
};

// Service de validation des fichiers
export const validateFile = (file) => {
  const maxSize = 10 * 1024 * 1024; // 10MB
  const allowedTypes = [
    'image/jpeg',
    'image/png',
    'image/tiff',
    'image/geotiff'
  ];

  const errors = [];

  if (file.size > maxSize) {
    errors.push('Le fichier dépasse la taille maximale de 10MB');
  }

  const isValidType = allowedTypes.includes(file.type) ||
    file.name.toLowerCase().endsWith('.tif') ||
    file.name.toLowerCase().endsWith('.tiff');

  if (!isValidType) {
    errors.push('Type de fichier non supporté. Utilisez JPEG, PNG, TIFF ou GeoTIFF');
  }

  return {
    isValid: errors.length === 0,
    errors
  };
};

// Service de gestion des erreurs
export const handleApiError = (error) => {
  if (error.response) {
    // Erreur de réponse du serveur
    return {
      type: 'server',
      message: error.response.data?.error || 'Erreur serveur',
      status: error.response.status
    };
  } else if (error.request) {
    // Erreur de réseau
    return {
      type: 'network',
      message: 'Erreur de connexion. Vérifiez votre connexion internet.',
      status: null
    };
  } else {
    // Autre erreur
    return {
      type: 'client',
      message: error.message || 'Une erreur inattendue s\'est produite',
      status: null
    };
  }
};

// Service de formatage des résultats
export const formatClassificationResult = (result) => {
  if (!result || !result.prediction) {
    return null;
  }

  return {
    id: Date.now(),
    culture: result.prediction.predicted_class,
    confidence: result.prediction.confidence,
    confidenceLevel: result.prediction.confidence_level,
    confidenceLabel: result.prediction.confidence_label,
    action: result.prediction.recommended_action,
    features: {
      ndvi: result.features.ndvi,
      evi: result.features.evi,
      savi: result.features.savi,
      area: result.features.area_ha
    },
    coordinates: result.coordinates,
    timestamp: result.metadata.timestamp,
    processingTime: result.metadata.processing_time
  };
};

// Service de cache local (localStorage)
export const cacheService = {
  set: (key, data, expirationMinutes = 60) => {
    const item = {
      data,
      expiration: Date.now() + (expirationMinutes * 60 * 1000)
    };
    localStorage.setItem(key, JSON.stringify(item));
  },

  get: (key) => {
    const item = localStorage.getItem(key);
    if (!item) return null;

    try {
      const parsed = JSON.parse(item);
      if (Date.now() > parsed.expiration) {
        localStorage.removeItem(key);
        return null;
      }
      return parsed.data;
    } catch {
      localStorage.removeItem(key);
      return null;
    }
  },

  remove: (key) => {
    localStorage.removeItem(key);
  },

  clear: () => {
    localStorage.clear();
  }
};

export default api;
