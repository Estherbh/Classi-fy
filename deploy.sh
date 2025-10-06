#!/bin/bash

# Script de déploiement automatisé pour Vercel
# Classification des Cultures Agricoles - IA Satellite

set -e  # Arrêter en cas d'erreur

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonctions utilitaires
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Banner
echo -e "${GREEN}"
echo "🌾 Classification des Cultures Agricoles - Déploiement"
echo "=================================================="
echo -e "${NC}"

# Vérifications préalables
log_info "Vérification des prérequis..."

# Vérifier Node.js
if ! command -v node &> /dev/null; then
    log_error "Node.js n'est pas installé"
    exit 1
fi

NODE_VERSION=$(node --version)
log_success "Node.js version: $NODE_VERSION"

# Vérifier pnpm
if ! command -v pnpm &> /dev/null; then
    log_warning "pnpm n'est pas installé, installation en cours..."
    npm install -g pnpm
fi

PNPM_VERSION=$(pnpm --version)
log_success "pnpm version: $PNPM_VERSION"

# Vérifier Vercel CLI
if ! command -v vercel &> /dev/null; then
    log_warning "Vercel CLI n'est pas installé, installation en cours..."
    npm install -g vercel
fi

VERCEL_VERSION=$(vercel --version)
log_success "Vercel CLI version: $VERCEL_VERSION"

# Installation des dépendances
log_info "Installation des dépendances..."
pnpm install --frozen-lockfile

# Vérification du code
log_info "Vérification du code avec ESLint..."
if pnpm run lint; then
    log_success "Code vérifié avec succès"
else
    log_warning "Avertissements ESLint détectés, mais déploiement continué"
fi

# Tests (si disponibles)
if [ -f "package.json" ] && grep -q '"test"' package.json; then
    log_info "Exécution des tests..."
    if pnpm run test; then
        log_success "Tests passés avec succès"
    else
        log_error "Tests échoués"
        read -p "Continuer le déploiement malgré les tests échoués? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi

# Build de l'application
log_info "Construction de l'application..."
pnpm run build

if [ $? -eq 0 ]; then
    log_success "Build terminé avec succès"
else
    log_error "Échec du build"
    exit 1
fi

# Vérification de la taille du bundle
log_info "Vérification de la taille du bundle..."
DIST_SIZE=$(du -sh dist 2>/dev/null | cut -f1 || echo "N/A")
log_info "Taille du bundle: $DIST_SIZE"

# Vérification des fichiers critiques
log_info "Vérification des fichiers critiques..."
CRITICAL_FILES=("dist/index.html" "dist/assets" "vercel.json" "package.json")

for file in "${CRITICAL_FILES[@]}"; do
    if [ -e "$file" ]; then
        log_success "✓ $file"
    else
        log_error "✗ $file manquant"
        exit 1
    fi
done

# Configuration des variables d'environnement
log_info "Configuration des variables d'environnement..."

# Vérifier si .env.local existe
if [ -f ".env.local" ]; then
    log_success "Fichier .env.local trouvé"
else
    log_warning "Fichier .env.local non trouvé, utilisation de .env.example"
    if [ -f ".env.example" ]; then
        cp .env.example .env.local
        log_info "Veuillez configurer les variables dans .env.local"
    fi
fi

# Déploiement sur Vercel
log_info "Déploiement sur Vercel..."

# Demander le type de déploiement
echo "Type de déploiement:"
echo "1) Production"
echo "2) Preview"
echo "3) Development"
read -p "Choisissez (1-3): " -n 1 -r DEPLOY_TYPE
echo

case $DEPLOY_TYPE in
    1)
        log_info "Déploiement en production..."
        vercel --prod --confirm
        ;;
    2)
        log_info "Déploiement en preview..."
        vercel --confirm
        ;;
    3)
        log_info "Déploiement en développement..."
        vercel --confirm
        ;;
    *)
        log_error "Choix invalide"
        exit 1
        ;;
esac

if [ $? -eq 0 ]; then
    log_success "Déploiement terminé avec succès!"
    
    # Obtenir l'URL de déploiement
    DEPLOYMENT_URL=$(vercel ls --limit 1 --json | jq -r '.[0].url' 2>/dev/null || echo "N/A")
    if [ "$DEPLOYMENT_URL" != "N/A" ]; then
        log_success "URL de déploiement: https://$DEPLOYMENT_URL"
    fi
    
    # Tests post-déploiement
    log_info "Tests post-déploiement..."
    
    if [ "$DEPLOYMENT_URL" != "N/A" ]; then
        # Test de disponibilité
        if curl -f -s "https://$DEPLOYMENT_URL" > /dev/null; then
            log_success "✓ Application accessible"
        else
            log_warning "⚠ Application peut ne pas être immédiatement accessible"
        fi
        
        # Test de l'API
        if curl -f -s "https://$DEPLOYMENT_URL/api/health" > /dev/null 2>&1; then
            log_success "✓ API fonctionnelle"
        else
            log_warning "⚠ API peut ne pas être immédiatement disponible"
        fi
    fi
    
    # Nettoyage
    log_info "Nettoyage des fichiers temporaires..."
    # Garder dist pour debug si nécessaire
    
    echo -e "${GREEN}"
    echo "🎉 Déploiement terminé avec succès!"
    echo "=================================="
    echo -e "${NC}"
    
    if [ "$DEPLOYMENT_URL" != "N/A" ]; then
        echo -e "🌐 URL: ${BLUE}https://$DEPLOYMENT_URL${NC}"
    fi
    echo -e "📊 Dashboard Vercel: ${BLUE}https://vercel.com/dashboard${NC}"
    echo -e "📖 Documentation: ${BLUE}README.md${NC}"
    
else
    log_error "Échec du déploiement"
    exit 1
fi

# Conseils post-déploiement
echo -e "\n${YELLOW}Conseils post-déploiement:${NC}"
echo "• Configurez les variables d'environnement dans le dashboard Vercel"
echo "• Ajoutez un domaine personnalisé si nécessaire"
echo "• Configurez les alertes de monitoring"
echo "• Testez toutes les fonctionnalités en production"
echo "• Documentez les changements dans CHANGELOG.md"

log_success "Script de déploiement terminé!"
