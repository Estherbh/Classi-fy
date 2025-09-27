// API d'upload de fichiers pour les images satellites
import formidable from 'formidable';
import fs from 'fs';
import path from 'path';

export const config = {
  api: {
    bodyParser: false,
  },
};

// Configuration pour l'upload
const uploadDir = path.join(process.cwd(), 'uploads');

// Créer le dossier d'upload s'il n'existe pas
if (!fs.existsSync(uploadDir)) {
  fs.mkdirSync(uploadDir, { recursive: true });
}

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Méthode non autorisée' });
  }

  try {
    const form = formidable({
      uploadDir,
      keepExtensions: true,
      maxFileSize: 10 * 1024 * 1024, // 10MB max
      filter: ({ name, originalFilename, mimetype }) => {
        // Filtrer les types de fichiers acceptés
        const allowedTypes = [
          'image/jpeg',
          'image/png',
          'image/tiff',
          'image/geotiff'
        ];
        return allowedTypes.includes(mimetype) || 
               originalFilename?.toLowerCase().endsWith('.tif') ||
               originalFilename?.toLowerCase().endsWith('.tiff');
      }
    });

    const [fields, files] = await form.parse(req);
    
    if (!files.file || !files.file[0]) {
      return res.status(400).json({ error: 'Aucun fichier uploadé' });
    }

    const file = files.file[0];
    const fileInfo = {
      filename: file.newFilename,
      originalName: file.originalFilename,
      size: file.size,
      mimetype: file.mimetype,
      path: file.filepath,
      uploadedAt: new Date().toISOString()
    };

    // Validation supplémentaire de la taille
    if (file.size > 10 * 1024 * 1024) {
      fs.unlinkSync(file.filepath); // Supprimer le fichier
      return res.status(400).json({ error: 'Fichier trop volumineux (max 10MB)' });
    }

    res.status(200).json({
      success: true,
      message: 'Fichier uploadé avec succès',
      file: fileInfo
    });

  } catch (error) {
    console.error('Erreur upload:', error);
    res.status(500).json({ 
      error: 'Erreur lors de l\'upload du fichier',
      details: error.message 
    });
  }
}
