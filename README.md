# 🌾 Classification des Cultures Agricoles - IA Satellite

Une application web moderne et sécurisée pour la classification automatique des cultures agricoles utilisant l'imagerie satellite et l'intelligence artificielle.

## ✨ Fonctionnalités

- **🤖 Classification IA Avancée** : Modèle hybride Random Forest + XGBoost avec calibration automatique
- **🛡️ Système de Confiance à 5 Niveaux** : Évaluation précise de la fiabilité des prédictions
- **📊 Dashboard Interactif** : Interface moderne avec visualisations en temps réel
- **🗺️ Visualisation Cartographique** : Cartes interactives avec niveaux de confiance
- **📁 Export Multi-Format** : CSV, GeoJSON, et rapports PDF automatisés
- **🔒 Sécurité Renforcée** : Rate limiting, validation, chiffrement des données
- **⚡ Performances Optimisées** : Cache intelligent, compression, CDN global
- **📱 Design Responsive** : Interface adaptative avec thème sombre moderne

## 🚀 Déploiement Rapide sur Vercel

### 1. Prérequis

- Compte [Vercel](https://vercel.com)
- Node.js 18+ (optionnel pour développement local)

### 2. Déploiement en Un Clic

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/votre-username/crop-classification-app)

### 3. Déploiement Manuel

```bash
# Cloner le repository
git clone https://github.com/votre-username/crop-classification-app.git
cd crop-classification-app

# Installer les dépendances
npm install

# Construire l'application
npm run build

# Déployer sur Vercel
npx vercel --prod
```

### 4. Variables d'Environnement

Configurez ces variables dans votre dashboard Vercel :

```env
NODE_ENV=production
NEXT_PUBLIC_API_URL=https://votre-app.vercel.app
SECRET_KEY=votre-clé-secrète-sécurisée
RATE_LIMIT_MAX_REQUESTS=100
MAX_FILE_SIZE=10485760
ENABLE_ANALYTICS=true
```

## 🛠️ Développement Local

### Installation

```bash
# Cloner le projet
git clone https://github.com/votre-username/crop-classification-app.git
cd crop-classification-app

# Installer les dépendances
pnpm install

# Copier la configuration d'environnement
cp .env.example .env.local

# Démarrer le serveur de développement
pnpm run dev
```

### Scripts Disponibles

```bash
# Développement
pnpm run dev          # Serveur de développement
pnpm run build        # Build de production
pnpm run preview      # Prévisualisation du build
pnpm run lint         # Vérification du code
pnpm run test         # Tests unitaires
```

## 📋 Architecture Technique

### Stack Technologique

- **Frontend** : React 18, Vite, TypeScript
- **UI/UX** : Tailwind CSS, Shadcn/UI, Framer Motion
- **Backend** : Vercel Functions (Serverless)
- **ML/IA** : Random Forest + XGBoost, NDVI, Sentinel-2
- **Sécurité** : Helmet, Rate Limiting, Validation
- **Performance** : Cache, Compression, CDN

### Structure du Projet

```
src/
├── components/          # Composants React réutilisables
│   └── ui/             # Composants UI Shadcn
├── services/           # Services API et intégrations
├── utils/              # Utilitaires et helpers
│   ├── performance.js  # Optimisations performance
│   ├── monitoring.js   # Monitoring et analytics
│   └── validation.js   # Validation et sécurité
├── api/                # API Routes serverless
│   ├── upload.js       # Upload de fichiers
│   ├── classify.js     # Classification ML
│   └── export.js       # Export des résultats
└── middleware/         # Middleware de sécurité
```

## 🔒 Sécurité

### Mesures de Sécurité Implémentées

- **Rate Limiting** : Protection contre les attaques DDoS
- **Validation des Entrées** : Sanitisation et validation complète
- **Chiffrement** : Données sensibles chiffrées
- **Headers de Sécurité** : CSP, HSTS, X-Frame-Options
- **CORS Configuré** : Origines autorisées uniquement
- **Upload Sécurisé** : Validation des types et tailles de fichiers

### Configuration de Sécurité

```javascript
// Rate Limiting
- Upload: 10 fichiers / 15 minutes
- Classification: 5 requêtes / minute  
- API générale: 100 requêtes / 15 minutes

// Validation des Fichiers
- Types autorisés: JPEG, PNG, TIFF, GeoTIFF
- Taille maximale: 10MB
- Validation du contenu et des métadonnées
```

## ⚡ Performance

### Optimisations Implémentées

- **Code Splitting** : Chargement des composants à la demande
- **Lazy Loading** : Images et ressources chargées progressivement
- **Cache Intelligent** : Mise en cache des résultats et ressources
- **Compression** : Gzip et Brotli pour tous les assets
- **CDN Global** : Distribution mondiale via Vercel Edge Network
- **Bundle Optimization** : Minification et tree-shaking avancés

### Métriques de Performance

- **First Contentful Paint** : < 1.5s
- **Largest Contentful Paint** : < 2.5s
- **Time to Interactive** : < 3.5s
- **Cumulative Layout Shift** : < 0.1

## 🤖 Modèle d'IA

### Caractéristiques du Modèle

- **Algorithmes** : Random Forest + XGBoost hybride
- **Données** : Imagerie satellite Sentinel-2
- **Indices** : NDVI, EVI, SAVI
- **Classes** : Palmier à huile, Cacao, Forêt
- **Précision** : 94.2% sur dataset de validation

### Système de Confiance

| Niveau | Seuil | Action Recommandée |
|--------|-------|-------------------|
| 5 | > 80% | Utilisation automatique |
| 4 | 60-80% | Cartographie avec vérifications |
| 3 | 40-60% | Vérification visuelle |
| 2 | 20-40% | Vérification terrain |
| 1 | < 20% | Analyse approfondie |

## 📊 Monitoring

### Analytics et Monitoring

- **Performance Monitoring** : Métriques temps réel
- **Error Tracking** : Capture et analyse des erreurs
- **Usage Analytics** : Statistiques d'utilisation
- **Health Checks** : Surveillance de la santé système

### Métriques Surveillées

- Temps de réponse API
- Taux d'erreur
- Utilisation des ressources
- Satisfaction utilisateur
- Précision du modèle

## 🌍 Déploiement Multi-Environnement

### Environnements Supportés

- **Production** : Vercel (recommandé)
- **Staging** : Vercel Preview
- **Développement** : Local avec Vite

### Configuration par Environnement

```javascript
// Production
- Optimisations complètes
- Monitoring activé
- Cache agressif
- Sécurité maximale

// Développement  
- Hot reload
- Source maps
- Logs détaillés
- Outils de debug
```

## 🤝 Contribution

### Guide de Contribution

1. Fork le projet
2. Créer une branche feature (`git checkout -b feature/AmazingFeature`)
3. Commit les changements (`git commit -m 'Add AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

### Standards de Code

- **ESLint** : Configuration stricte
- **Prettier** : Formatage automatique
- **TypeScript** : Typage strict
- **Tests** : Couverture > 80%

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

## 🆘 Support

### Documentation

- [Guide d'utilisation](docs/user-guide.md)
- [API Documentation](docs/api.md)
- [Guide de déploiement](docs/deployment.md)

### Contact

- **Issues** : [GitHub Issues](https://github.com/votre-username/crop-classification-app/issues)
- **Discussions** : [GitHub Discussions](https://github.com/votre-username/crop-classification-app/discussions)
- **Email** : support@votre-domain.com

## 🙏 Remerciements

- [Sentinel-2](https://sentinel.esa.int/) pour les données satellite
- [Vercel](https://vercel.com) pour l'hébergement
- [Shadcn/UI](https://ui.shadcn.com/) pour les composants UI
- [Tailwind CSS](https://tailwindcss.com/) pour le styling

---

**Développé avec ❤️ pour l'agriculture durable et la technologie open source**
