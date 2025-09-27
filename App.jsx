import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button.jsx'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card.jsx'
import { Badge } from '@/components/ui/badge.jsx'
import { Progress } from '@/components/ui/progress.jsx'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs.jsx'
import { Alert, AlertDescription } from '@/components/ui/alert.jsx'
import { 
  Upload, 
  Satellite, 
  Brain, 
  MapPin, 
  BarChart3, 
  Download, 
  Shield, 
  Zap,
  Leaf,
  TreePine,
  Palmtree,
  Eye,
  CheckCircle,
  AlertTriangle,
  XCircle,
  FileText,
  Map
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  uploadFile, 
  classifyImage, 
  exportResults, 
  downloadFile, 
  validateFile, 
  handleApiError, 
  formatClassificationResult 
} from './services/api.js'
import './App.css'

// Composant pour les cartes de statistiques
const StatsCard = ({ icon: Icon, title, value, description, color = "primary" }) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.5 }}
  >
    <Card className="bg-card/50 backdrop-blur-sm border-border/50 hover:bg-card/70 transition-all duration-300">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        <Icon className={`h-4 w-4 text-${color}`} />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold text-foreground">{value}</div>
        <p className="text-xs text-muted-foreground">{description}</p>
      </CardContent>
    </Card>
  </motion.div>
)

// Composant pour les niveaux de confiance
const ConfidenceLevel = ({ level, label, color, percentage, action }) => (
  <motion.div
    initial={{ opacity: 0, x: -20 }}
    animate={{ opacity: 1, x: 0 }}
    transition={{ duration: 0.5 }}
    className="flex items-center justify-between p-4 rounded-lg bg-card/30 border border-border/50"
  >
    <div className="flex items-center space-x-3">
      <div className={`w-3 h-3 rounded-full bg-${color}-500`}></div>
      <div>
        <p className="font-medium text-foreground">Niveau {level} - {label}</p>
        <p className="text-sm text-muted-foreground">{action}</p>
      </div>
    </div>
    <div className="flex items-center space-x-2">
      <Progress value={percentage} className="w-20" />
      <span className="text-sm font-medium text-foreground">{percentage}%</span>
    </div>
  </motion.div>
)

// Composant pour l'upload de fichiers
const FileUpload = ({ onFileSelect, onError }) => {
  const [isDragOver, setIsDragOver] = useState(false)
  const [selectedFile, setSelectedFile] = useState(null)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [isUploading, setIsUploading] = useState(false)

  const handleDragOver = (e) => {
    e.preventDefault()
    setIsDragOver(true)
  }

  const handleDragLeave = (e) => {
    e.preventDefault()
    setIsDragOver(false)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setIsDragOver(false)
    const files = e.dataTransfer.files
    if (files.length > 0) {
      handleFileSelection(files[0])
    }
  }

  const handleFileChange = (e) => {
    const file = e.target.files[0]
    if (file) {
      handleFileSelection(file)
    }
  }

  const handleFileSelection = async (file) => {
    // Valider le fichier
    const validation = validateFile(file)
    if (!validation.isValid) {
      onError(validation.errors.join(', '))
      return
    }

    setSelectedFile(file)
    setIsUploading(true)
    setUploadProgress(0)

    try {
      // Upload du fichier
      const result = await uploadFile(file, (progress) => {
        setUploadProgress(progress)
      })

      onFileSelect(file, result)
    } catch (error) {
      onError(error.message)
    } finally {
      setIsUploading(false)
      setUploadProgress(0)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5 }}
      className={`relative border-2 border-dashed rounded-lg p-8 text-center transition-all duration-300 ${
        isDragOver 
          ? 'border-primary bg-primary/10' 
          : 'border-border hover:border-primary/50 hover:bg-card/30'
      }`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <input
        type="file"
        accept="image/*,.tif,.tiff"
        onChange={handleFileChange}
        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
      />
      <div className="space-y-4">
        <div className="mx-auto w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center">
          {isUploading ? (
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary"></div>
          ) : (
            <Upload className="w-6 h-6 text-primary" />
          )}
        </div>
        <div>
          <p className="text-lg font-medium text-foreground">
            {isUploading ? 'Upload en cours...' : 
             selectedFile ? selectedFile.name : 'Glissez votre image satellite ici'}
          </p>
          <p className="text-sm text-muted-foreground">
            Formats supportés: JPEG, PNG, GeoTIFF (max 10MB)
          </p>
        </div>
        {selectedFile && !isUploading && (
          <Badge variant="secondary" className="mt-2">
            {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
          </Badge>
        )}
        {isUploading && (
          <div className="space-y-2">
            <Progress value={uploadProgress} className="w-full" />
            <p className="text-sm text-muted-foreground">{uploadProgress}% uploadé</p>
          </div>
        )}
      </div>
    </motion.div>
  )
}

function App() {
  const [activeTab, setActiveTab] = useState('dashboard')
  const [selectedFile, setSelectedFile] = useState(null)
  const [uploadResult, setUploadResult] = useState(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [results, setResults] = useState(null)
  const [allResults, setAllResults] = useState([])
  const [error, setError] = useState(null)
  const [processingProgress, setProcessingProgress] = useState(0)

  // Données simulées pour la démonstration
  const confidenceLevels = [
    { level: 5, label: "Très haute confiance", color: "green", percentage: 85, action: "Utilisation automatique recommandée" },
    { level: 4, label: "Confiance élevée", color: "lime", percentage: 70, action: "Cartographie automatique avec vérifications" },
    { level: 3, label: "Confiance moyenne", color: "yellow", percentage: 45, action: "Vérification visuelle recommandée" },
    { level: 2, label: "Faible confiance", color: "orange", percentage: 25, action: "Vérification sur le terrain nécessaire" },
    { level: 1, label: "Très faible confiance", color: "red", percentage: 15, action: "Analyse approfondie requise" }
  ]

  const handleFileSelect = (file, uploadResult) => {
    setSelectedFile(file)
    setUploadResult(uploadResult)
    setError(null)
  }

  const handleError = (errorMessage) => {
    setError(errorMessage)
    setTimeout(() => setError(null), 5000) // Effacer l'erreur après 5 secondes
  }

  const handleClassify = async () => {
    if (!selectedFile || !uploadResult) return
    
    setIsProcessing(true)
    setProcessingProgress(0)
    setError(null)

    try {
      // Simulation du progrès
      const progressInterval = setInterval(() => {
        setProcessingProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval)
            return 90
          }
          return prev + 10
        })
      }, 300)

      // Classification de l'image
      const classificationResult = await classifyImage(uploadResult.file.filename)
      
      clearInterval(progressInterval)
      setProcessingProgress(100)

      // Formater les résultats
      const formattedResult = formatClassificationResult(classificationResult)
      setResults(formattedResult)
      
      // Ajouter aux résultats globaux
      setAllResults(prev => [...prev, formattedResult])
      
      // Passer à l'onglet résultats
      setActiveTab('results')

    } catch (error) {
      const errorInfo = handleApiError(error)
      handleError(errorInfo.message)
    } finally {
      setIsProcessing(false)
      setProcessingProgress(0)
    }
  }

  const handleExport = async (format) => {
    if (allResults.length === 0) {
      handleError('Aucun résultat à exporter')
      return
    }

    try {
      const { url, filename } = await exportResults(format, allResults)
      downloadFile(url, filename)
    } catch (error) {
      const errorInfo = handleApiError(error)
      handleError(errorInfo.message)
    }
  }

  useEffect(() => {
    // Appliquer le thème sombre par défaut
    document.documentElement.classList.add('dark')
  }, [])

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-card/20">
      {/* Header */}
      <header className="border-b border-border/50 bg-card/30 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-primary rounded-lg flex items-center justify-center">
                <Satellite className="w-6 h-6 text-primary-foreground" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-foreground">Classification des Cultures</h1>
                <p className="text-sm text-muted-foreground">Intelligence Artificielle Satellite</p>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <Badge variant="secondary" className="flex items-center space-x-1">
                <Shield className="w-3 h-3" />
                <span>Sécurisé</span>
              </Badge>
              <Badge variant="secondary" className="flex items-center space-x-1">
                <Zap className="w-3 h-3" />
                <span>Temps réel</span>
              </Badge>
            </div>
          </div>
        </div>
      </header>

      {/* Contenu principal */}
      <main className="container mx-auto px-4 py-8">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-4 bg-card/50 backdrop-blur-sm">
            <TabsTrigger value="dashboard" className="flex items-center space-x-2">
              <BarChart3 className="w-4 h-4" />
              <span className="hidden sm:inline">Dashboard</span>
            </TabsTrigger>
            <TabsTrigger value="upload" className="flex items-center space-x-2">
              <Upload className="w-4 h-4" />
              <span className="hidden sm:inline">Upload</span>
            </TabsTrigger>
            <TabsTrigger value="map" className="flex items-center space-x-2">
              <MapPin className="w-4 h-4" />
              <span className="hidden sm:inline">Carte</span>
            </TabsTrigger>
            <TabsTrigger value="results" className="flex items-center space-x-2">
              <Eye className="w-4 h-4" />
              <span className="hidden sm:inline">Résultats</span>
            </TabsTrigger>
          </TabsList>

          {/* Onglet Dashboard */}
          <TabsContent value="dashboard" className="space-y-6">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
            >
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                <StatsCard
                  icon={Brain}
                  title="Précision du Modèle"
                  value="94.2%"
                  description="Basé sur 10,000+ échantillons"
                  color="primary"
                />
                <StatsCard
                  icon={Leaf}
                  title="Cultures Analysées"
                  value="1,247"
                  description="Ce mois-ci"
                  color="green"
                />
                <StatsCard
                  icon={MapPin}
                  title="Zones Couvertes"
                  value="15,680 km²"
                  description="Côte d'Ivoire"
                  color="blue"
                />
                <StatsCard
                  icon={Zap}
                  title="Temps Moyen"
                  value="2.3s"
                  description="Par classification"
                  color="yellow"
                />
              </div>
            </motion.div>

            {/* Système de confiance */}
            <Card className="bg-card/50 backdrop-blur-sm border-border/50">
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Shield className="w-5 h-5 text-primary" />
                  <span>Système de Confiance à 5 Niveaux</span>
                </CardTitle>
                <CardDescription>
                  Classification automatique avec recommandations d'actions
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {confidenceLevels.map((level, index) => (
                  <ConfidenceLevel key={index} {...level} />
                ))}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Onglet Upload */}
          <TabsContent value="upload" className="space-y-6">
            {error && (
              <Alert className="border-destructive/50 text-destructive">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            
            <Card className="bg-card/50 backdrop-blur-sm border-border/50">
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Upload className="w-5 h-5 text-primary" />
                  <span>Analyser une Image Satellite</span>
                </CardTitle>
                <CardDescription>
                  Uploadez votre image satellite pour une classification automatique
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <FileUpload onFileSelect={handleFileSelect} onError={handleError} />
                
                {selectedFile && uploadResult && (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="space-y-4"
                  >
                    <div className="flex items-center justify-between">
                      <Button 
                        onClick={handleClassify}
                        disabled={isProcessing}
                        className="flex items-center space-x-2"
                      >
                        <Brain className="w-4 h-4" />
                        <span>{isProcessing ? 'Classification en cours...' : 'Classifier l\'image'}</span>
                      </Button>
                      {isProcessing && (
                        <div className="flex items-center space-x-2 text-muted-foreground">
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary"></div>
                          <span className="text-sm">Analyse IA en cours...</span>
                        </div>
                      )}
                    </div>
                    
                    {isProcessing && (
                      <div className="space-y-2">
                        <Progress value={processingProgress} className="w-full" />
                        <p className="text-sm text-muted-foreground">
                          {processingProgress < 30 ? 'Lecture de l\'image satellite...' :
                           processingProgress < 60 ? 'Calcul du NDVI et extraction des caractéristiques...' :
                           processingProgress < 90 ? 'Classification avec Random Forest + XGBoost...' :
                           'Finalisation des résultats...'}
                        </p>
                      </div>
                    )}
                  </motion.div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Onglet Carte */}
          <TabsContent value="map" className="space-y-6">
            <Card className="bg-card/50 backdrop-blur-sm border-border/50">
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <MapPin className="w-5 h-5 text-primary" />
                  <span>Visualisation Cartographique</span>
                </CardTitle>
                <CardDescription>
                  Carte interactive des classifications avec niveaux de confiance
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-96 bg-muted/20 rounded-lg flex items-center justify-center border border-border/50">
                  <div className="text-center space-y-2">
                    <MapPin className="w-12 h-12 text-muted-foreground mx-auto" />
                    <p className="text-muted-foreground">Carte interactive en cours de développement</p>
                    <p className="text-sm text-muted-foreground">Intégration Leaflet avec données géospatiales</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Onglet Résultats */}
          <TabsContent value="results" className="space-y-6">
            <AnimatePresence>
              {results && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.5 }}
                >
                  <Card className="bg-card/50 backdrop-blur-sm border-border/50">
                    <CardHeader>
                      <CardTitle className="flex items-center space-x-2">
                        <CheckCircle className="w-5 h-5 text-green-500" />
                        <span>Résultats de Classification</span>
                      </CardTitle>
                      <CardDescription>
                        Analyse complète de votre image satellite
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <div className="space-y-2">
                          <p className="text-sm font-medium text-muted-foreground">Culture Détectée</p>
                          <div className="flex items-center space-x-2">
                            <Palmtree className="w-5 h-5 text-green-500" />
                            <span className="text-lg font-semibold text-foreground">{results.culture}</span>
                          </div>
                        </div>
                        <div className="space-y-2">
                          <p className="text-sm font-medium text-muted-foreground">Niveau de Confiance</p>
                          <div className="flex items-center space-x-2">
                            <Badge variant="secondary" className="bg-green-500/20 text-green-400">
                              Niveau {results.level}
                            </Badge>
                            <span className="text-lg font-semibold text-foreground">
                              {(results.confidence * 100).toFixed(1)}%
                            </span>
                          </div>
                        </div>
                        <div className="space-y-2">
                          <p className="text-sm font-medium text-muted-foreground">Indice NDVI</p>
                          <div className="flex items-center space-x-2">
                            <Leaf className="w-5 h-5 text-green-500" />
                            <span className="text-lg font-semibold text-foreground">{results.ndvi}</span>
                          </div>
                        </div>
                      </div>
                      
                      <div className="flex flex-wrap gap-4">
                        <Button 
                          variant="outline" 
                          className="flex items-center space-x-2"
                          onClick={() => handleExport('csv')}
                        >
                          <FileText className="w-4 h-4" />
                          <span>Exporter CSV</span>
                        </Button>
                        <Button 
                          variant="outline" 
                          className="flex items-center space-x-2"
                          onClick={() => handleExport('geojson')}
                        >
                          <Map className="w-4 h-4" />
                          <span>Exporter GeoJSON</span>
                        </Button>
                        <Button 
                          variant="outline" 
                          className="flex items-center space-x-2"
                          onClick={() => handleExport('pdf')}
                        >
                          <Download className="w-4 h-4" />
                          <span>Rapport PDF</span>
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              )}
            </AnimatePresence>

            {!results && (
              <Card className="bg-card/50 backdrop-blur-sm border-border/50">
                <CardContent className="py-12">
                  <div className="text-center space-y-4">
                    <Eye className="w-12 h-12 text-muted-foreground mx-auto" />
                    <p className="text-lg text-muted-foreground">Aucun résultat à afficher</p>
                    <p className="text-sm text-muted-foreground">
                      Uploadez et classifiez une image pour voir les résultats ici
                    </p>
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>
        </Tabs>
      </main>

      {/* Footer */}
      <footer className="border-t border-border/50 bg-card/30 backdrop-blur-sm mt-12">
        <div className="container mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <p className="text-sm text-muted-foreground">
                © 2025 Classification des Cultures Agricoles - Powered by IA
              </p>
            </div>
            <div className="flex items-center space-x-4">
              <Badge variant="outline" className="flex items-center space-x-1">
                <Shield className="w-3 h-3" />
                <span>100% Gratuit</span>
              </Badge>
              <Badge variant="outline" className="flex items-center space-x-1">
                <Zap className="w-3 h-3" />
                <span>Open Source</span>
              </Badge>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default App
