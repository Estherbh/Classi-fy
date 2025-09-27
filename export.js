// API d'export des résultats de classification
import fs from 'fs';
import path from 'path';

// Fonction pour générer un CSV
function generateCSV(results) {
  const headers = [
    'ID',
    'Culture_Predite',
    'Confiance',
    'Niveau_Confiance',
    'Action_Recommandee',
    'NDVI',
    'EVI',
    'SAVI',
    'Surface_Ha',
    'Latitude',
    'Longitude',
    'Timestamp'
  ];

  let csv = headers.join(',') + '\n';

  results.forEach((result, index) => {
    const row = [
      index + 1,
      `"${result.prediction.predicted_class}"`,
      result.prediction.confidence,
      result.prediction.confidence_level,
      `"${result.prediction.recommended_action}"`,
      result.features.ndvi,
      result.features.evi,
      result.features.savi,
      result.features.area_ha,
      result.coordinates?.lat || '',
      result.coordinates?.lng || '',
      result.metadata.timestamp
    ];
    csv += row.join(',') + '\n';
  });

  return csv;
}

// Fonction pour générer un GeoJSON
function generateGeoJSON(results) {
  const features = results.map((result, index) => ({
    type: 'Feature',
    properties: {
      id: index + 1,
      culture_predite: result.prediction.predicted_class,
      confiance: result.prediction.confidence,
      niveau_confiance: result.prediction.confidence_level,
      action_recommandee: result.prediction.recommended_action,
      ndvi: result.features.ndvi,
      evi: result.features.evi,
      savi: result.features.savi,
      surface_ha: result.features.area_ha,
      timestamp: result.metadata.timestamp
    },
    geometry: {
      type: 'Point',
      coordinates: [
        result.coordinates?.lng || 0,
        result.coordinates?.lat || 0
      ]
    }
  }));

  return {
    type: 'FeatureCollection',
    features
  };
}

// Fonction pour générer un rapport PDF (structure HTML pour conversion)
function generatePDFReport(results) {
  const totalResults = results.length;
  const avgConfidence = results.reduce((sum, r) => sum + r.prediction.confidence, 0) / totalResults;
  const cultureStats = {};
  
  results.forEach(result => {
    const culture = result.prediction.predicted_class;
    cultureStats[culture] = (cultureStats[culture] || 0) + 1;
  });

  const html = `
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Rapport de Classification des Cultures Agricoles</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; color: #333; }
            .header { text-align: center; margin-bottom: 30px; }
            .stats { display: flex; justify-content: space-around; margin: 20px 0; }
            .stat-card { text-align: center; padding: 15px; border: 1px solid #ddd; border-radius: 8px; }
            .results-table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            .results-table th, .results-table td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            .results-table th { background-color: #f2f2f2; }
            .confidence-high { color: #22c55e; font-weight: bold; }
            .confidence-medium { color: #eab308; font-weight: bold; }
            .confidence-low { color: #ef4444; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🌾 Rapport de Classification des Cultures Agricoles</h1>
            <p>Généré le ${new Date().toLocaleDateString('fr-FR')}</p>
        </div>

        <div class="stats">
            <div class="stat-card">
                <h3>Total Analysé</h3>
                <p style="font-size: 24px; font-weight: bold;">${totalResults}</p>
            </div>
            <div class="stat-card">
                <h3>Confiance Moyenne</h3>
                <p style="font-size: 24px; font-weight: bold;">${(avgConfidence * 100).toFixed(1)}%</p>
            </div>
            <div class="stat-card">
                <h3>Cultures Détectées</h3>
                <p style="font-size: 24px; font-weight: bold;">${Object.keys(cultureStats).length}</p>
            </div>
        </div>

        <h2>Répartition par Culture</h2>
        <ul>
            ${Object.entries(cultureStats).map(([culture, count]) => 
                `<li><strong>${culture}:</strong> ${count} (${((count/totalResults)*100).toFixed(1)}%)</li>`
            ).join('')}
        </ul>

        <h2>Résultats Détaillés</h2>
        <table class="results-table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Culture Prédite</th>
                    <th>Confiance</th>
                    <th>Niveau</th>
                    <th>NDVI</th>
                    <th>Surface (ha)</th>
                    <th>Action Recommandée</th>
                </tr>
            </thead>
            <tbody>
                ${results.map((result, index) => `
                    <tr>
                        <td>${index + 1}</td>
                        <td>${result.prediction.predicted_class}</td>
                        <td class="${result.prediction.confidence > 0.7 ? 'confidence-high' : 
                                   result.prediction.confidence > 0.4 ? 'confidence-medium' : 'confidence-low'}">
                            ${(result.prediction.confidence * 100).toFixed(1)}%
                        </td>
                        <td>${result.prediction.confidence_level}</td>
                        <td>${result.features.ndvi}</td>
                        <td>${result.features.area_ha.toFixed(2)}</td>
                        <td>${result.prediction.recommended_action}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>

        <div style="margin-top: 30px; padding: 15px; background-color: #f8f9fa; border-radius: 8px;">
            <h3>Notes Méthodologiques</h3>
            <p>Ce rapport a été généré par un système de classification automatique utilisant l'imagerie satellite Sentinel-2 
            et des algorithmes d'apprentissage automatique (Random Forest + XGBoost). Les niveaux de confiance indiquent 
            la fiabilité des prédictions et les actions recommandées pour chaque classification.</p>
        </div>
    </body>
    </html>
  `;

  return html;
}

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Méthode non autorisée' });
  }

  try {
    const { format, results } = req.body;

    if (!results || !Array.isArray(results) || results.length === 0) {
      return res.status(400).json({ error: 'Données de résultats requises' });
    }

    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    let filename, content, contentType;

    switch (format) {
      case 'csv':
        filename = `classification_results_${timestamp}.csv`;
        content = generateCSV(results);
        contentType = 'text/csv';
        break;

      case 'geojson':
        filename = `classification_results_${timestamp}.geojson`;
        content = JSON.stringify(generateGeoJSON(results), null, 2);
        contentType = 'application/geo+json';
        break;

      case 'pdf':
        filename = `rapport_classification_${timestamp}.html`;
        content = generatePDFReport(results);
        contentType = 'text/html';
        break;

      default:
        return res.status(400).json({ error: 'Format non supporté. Utilisez: csv, geojson, ou pdf' });
    }

    // Définir les en-têtes pour le téléchargement
    res.setHeader('Content-Type', contentType);
    res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
    res.setHeader('Cache-Control', 'no-cache');

    res.status(200).send(content);

  } catch (error) {
    console.error('Erreur export:', error);
    res.status(500).json({ 
      error: 'Erreur lors de l\'export',
      details: error.message 
    });
  }
}
