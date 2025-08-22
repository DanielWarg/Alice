'use client'

import React, { useState, useRef } from 'react'
import { Upload, File, CheckCircle, AlertCircle, X, FileText, FileImage } from 'lucide-react'

interface UploadResult {
  ok: boolean
  message?: string
  error?: string
  chunks_created?: number
  embeddings_created?: number
  file_size_kb?: number
  content_preview?: string
}

interface DocumentUploadProps {
  baseUrl?: string
  onUploadComplete?: (result: UploadResult) => void
  className?: string
}

export default function DocumentUpload({ 
  baseUrl = '', 
  onUploadComplete, 
  className = '' 
}: DocumentUploadProps) {
  const [isUploading, setIsUploading] = useState(false)
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null)
  const [dragActive, setDragActive] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const supportedTypes = ['.txt', '.md', '.pdf', '.docx', '.html']
  const maxSizeKB = 10 * 1024 // 10MB

  const handleFileUpload = async (file: File) => {
    if (!file) return

    // Validate file size
    const fileSizeKB = file.size / 1024
    if (fileSizeKB > maxSizeKB) {
      setUploadResult({
        ok: false,
        error: `Filen är för stor (${Math.round(fileSizeKB)}KB). Max storlek: ${maxSizeKB/1024}MB`
      })
      return
    }

    // Validate file type
    const extension = '.' + file.name.split('.').pop()?.toLowerCase()
    if (!supportedTypes.includes(extension)) {
      setUploadResult({
        ok: false,
        error: `Filtyp ${extension} stöds inte. Tillåtna: ${supportedTypes.join(', ')}`
      })
      return
    }

    setIsUploading(true)
    setUploadResult(null)

    try {
      const formData = new FormData()
      formData.append('file', file)
      
      // Add metadata tags
      const tags = {
        category: getFileCategory(extension),
        uploaded_by: 'user',
        original_size: file.size
      }
      formData.append('tags', JSON.stringify(tags))

      const response = await fetch(`${baseUrl}/api/documents/upload`, {
        method: 'POST',
        body: formData
      })

      const result: UploadResult = await response.json()
      setUploadResult(result)
      
      if (onUploadComplete) {
        onUploadComplete(result)
      }

    } catch (error) {
      const errorResult = {
        ok: false,
        error: `Upload misslyckades: ${error instanceof Error ? error.message : 'Okänt fel'}`
      }
      setUploadResult(errorResult)
      
      if (onUploadComplete) {
        onUploadComplete(errorResult)
      }
    } finally {
      setIsUploading(false)
    }
  }

  const getFileCategory = (extension: string): string => {
    if (['.pdf', '.docx'].includes(extension)) return 'document'
    if (['.md', '.html'].includes(extension)) return 'markup'
    return 'text'
  }

  const getFileIcon = (filename: string) => {
    const ext = '.' + filename.split('.').pop()?.toLowerCase()
    if (['.pdf', '.docx'].includes(ext)) return <FileText className="w-4 h-4" />
    return <File className="w-4 h-4" />
  }

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
  }

  const handleDragIn = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
      setDragActive(true)
    }
  }

  const handleDragOut = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0])
    }
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileUpload(e.target.files[0])
    }
  }

  const clearResult = () => {
    setUploadResult(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  return (
    <div className={`document-upload ${className}`}>
      <div 
        className={`
          border-2 border-dashed rounded-xl p-6 text-center cursor-pointer
          transition-all duration-300 relative overflow-hidden
          ${dragActive 
            ? 'border-cyan-400 bg-cyan-950/30 shadow-lg shadow-cyan-500/20' 
            : 'border-gray-600 bg-gray-800/50 hover:border-gray-500 hover:bg-gray-800/70'
          }
          ${isUploading ? 'pointer-events-none opacity-70' : ''}
        `}
        onDragEnter={handleDragIn}
        onDragLeave={handleDragOut}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          accept={supportedTypes.join(',')}
          onChange={handleFileSelect}
          disabled={isUploading}
        />

        <div className="flex flex-col items-center space-y-3">
          {isUploading ? (
            <>
              <div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
              <p className="text-gray-300">Laddar upp dokument...</p>
              <p className="text-sm text-gray-500">Skapar embeddings för Alice's minne</p>
            </>
          ) : (
            <>
              <Upload className={`w-8 h-8 ${dragActive ? 'text-cyan-400' : 'text-gray-400'}`} />
              <p className={`font-medium ${dragActive ? 'text-cyan-300' : 'text-gray-300'}`}>
                {dragActive ? 'Släpp filen här' : 'Ladda upp dokument till Alice'}
              </p>
              <p className="text-sm text-gray-500">
                Drag & drop eller klicka för att välja
              </p>
              <p className="text-xs text-gray-600">
                Stöds: {supportedTypes.join(', ')} • Max: {maxSizeKB/1024}MB
              </p>
            </>
          )}
        </div>

        {/* Background pattern */}
        <div className="absolute inset-0 opacity-5 pointer-events-none">
          <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/10 to-blue-500/10" />
        </div>
      </div>

      {/* Upload Result */}
      {uploadResult && (
        <div className={`
          mt-4 p-4 rounded-lg border backdrop-blur-sm
          ${uploadResult.ok 
            ? 'bg-green-950/50 border-green-500/30' 
            : 'bg-red-950/50 border-red-500/30'
          }
        `}>
          <div className="flex items-start justify-between">
            <div className="flex items-start space-x-3">
              {uploadResult.ok ? (
                <CheckCircle className="w-5 h-5 text-green-400 mt-0.5" />
              ) : (
                <AlertCircle className="w-5 h-5 text-red-400 mt-0.5" />
              )}
              <div className="flex-1">
                <p className={`font-medium ${uploadResult.ok ? 'text-green-300' : 'text-red-300'}`}>
                  {uploadResult.ok ? 'Uppladdning lyckades!' : 'Uppladdning misslyckades'}
                </p>
                <p className="text-sm text-gray-300 mt-1">
                  {uploadResult.message || uploadResult.error}
                </p>
                
                {uploadResult.ok && (
                  <div className="mt-2 text-xs text-gray-400 space-y-1">
                    <div className="flex justify-between">
                      <span>Chunks skapade:</span>
                      <span className="text-cyan-400 font-mono">
                        {uploadResult.chunks_created || 0}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Embeddings:</span>
                      <span className="text-cyan-400 font-mono">
                        {uploadResult.embeddings_created || 0}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Storlek:</span>
                      <span className="text-cyan-400 font-mono">
                        {uploadResult.file_size_kb?.toFixed(1) || 0} KB
                      </span>
                    </div>
                  </div>
                )}

                {uploadResult.content_preview && (
                  <div className="mt-3 p-2 bg-gray-900/50 rounded text-xs text-gray-400 font-mono">
                    <p className="mb-1">Förhandsvisning:</p>
                    <p className="truncate">{uploadResult.content_preview}</p>
                  </div>
                )}
              </div>
            </div>
            
            <button
              onClick={clearResult}
              className="text-gray-400 hover:text-gray-300 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Quick Tips */}
      <div className="mt-4 text-xs text-gray-500 space-y-1">
        <p>💡 <strong>Tips:</strong></p>
        <ul className="list-disc list-inside space-y-1 ml-2">
          <li>Uppladdade dokument blir tillgängliga för Alice's AI-kontext</li>
          <li>Stora dokument delas automatiskt upp i hanterbara delar</li>
          <li>Alice kan svara på frågor baserat på dokumentinnehållet</li>
          <li>Embeddings skapas för semantisk sökning och bättre förståelse</li>
        </ul>
      </div>
    </div>
  )
}

// Export both default and named export for flexibility
export { DocumentUpload }