'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Mic, MicOff, VolumeX, Volume2, Activity, AlertTriangle } from 'lucide-react'

interface B3Status {
  isActive: boolean
  isMuted: boolean
  hardMute: boolean
  framesProcessed: number
  bufferSize: number
  sessionDuration: number
}

interface TranscriptionResult {
  text: string
  confidence: number
  importance_score: number
  importance_reasons: string[]
  will_store: boolean
  timestamp: number
}

interface B3AmbientVoiceHUDProps {
  className?: string
}

export function B3AmbientVoiceHUD({ className }: B3AmbientVoiceHUDProps) {
  // State management
  const [isConnected, setIsConnected] = useState(false)
  const [isActive, setIsActive] = useState(false)
  const [status, setStatus] = useState<B3Status>({
    isActive: false,
    isMuted: false,
    hardMute: false,
    framesProcessed: 0,
    bufferSize: 0,
    sessionDuration: 0
  })
  
  // Transcription state
  const [lastTranscription, setLastTranscription] = useState<TranscriptionResult | null>(null)
  const [transcriptionHistory, setTranscriptionHistory] = useState<TranscriptionResult[]>([])
  const [ambientClient, setAmbientClient] = useState<any>(null)
  
  // Connection state
  const [connectionError, setConnectionError] = useState<string | null>(null)
  const [isInitializing, setIsInitializing] = useState(false)
  
  // Initialize B3 ambient voice client
  useEffect(() => {
    // Load B3 ambient voice client script
    const script = document.createElement('script')
    script.src = '/lib/b3-ambient-voice-client.js'
    script.onload = () => {
      console.log('B3 Ambient Voice Client loaded')
      // Client will be available as window.B3AmbientVoiceClient
    }
    document.head.appendChild(script)
    
    return () => {
      document.head.removeChild(script)
    }
  }, [])
  
  // Initialize client when available
  useEffect(() => {
    if (typeof window !== 'undefined' && (window as any).B3AmbientVoiceClient && !ambientClient) {
      const client = new (window as any).B3AmbientVoiceClient()
      
      // Setup event listeners
      client.on('connected', () => {
        setIsConnected(true)
        setConnectionError(null)
        console.log('B3 Ambient Voice connected')
      })
      
      client.on('disconnected', () => {
        setIsConnected(false)
        console.log('B3 Ambient Voice disconnected')
      })
      
      client.on('error', (error: any) => {
        setConnectionError(error.message || 'Connection error')
        console.error('B3 Ambient Voice error:', error)
      })
      
      client.on('status_update', (statusUpdate: B3Status) => {
        setStatus(statusUpdate)
      })
      
      client.on('transcription_result', (result: TranscriptionResult) => {
        setLastTranscription(result)
        setTranscriptionHistory(prev => [...prev.slice(-9), result]) // Keep last 10
        console.log('Transcription result:', result)
      })
      
      client.on('started', () => {
        setIsActive(true)
        setIsInitializing(false)
      })
      
      client.on('stopped', () => {
        setIsActive(false)
        setIsInitializing(false)
      })
      
      setAmbientClient(client)
    }
  }, [ambientClient])
  
  // Start ambient voice processing
  const handleStart = useCallback(async () => {
    if (!ambientClient || isActive) return
    
    setIsInitializing(true)
    setConnectionError(null)
    
    try {
      await ambientClient.start()
    } catch (error) {
      console.error('Failed to start B3 ambient voice:', error)
      setConnectionError('Failed to start ambient voice')
      setIsInitializing(false)
    }
  }, [ambientClient, isActive])
  
  // Stop ambient voice processing
  const handleStop = useCallback(async () => {
    if (!ambientClient || !isActive) return
    
    try {
      await ambientClient.stop()
    } catch (error) {
      console.error('Failed to stop B3 ambient voice:', error)
    }
  }, [ambientClient, isActive])
  
  // Toggle mute/unmute
  const handleMuteToggle = useCallback(() => {
    if (!ambientClient) return
    
    if (status.isMuted) {
      ambientClient.unmute()
    } else {
      ambientClient.mute()
    }
  }, [ambientClient, status.isMuted])
  
  // Hard mute toggle (emergency stop)
  const handleHardMute = useCallback(() => {
    if (!ambientClient) return
    
    if (status.hardMute) {
      ambientClient.hardMuteDisable()
    } else {
      ambientClient.hardMuteEnable()
    }
  }, [ambientClient, status.hardMute])
  
  // Clear memory
  const handleClearMemory = useCallback(() => {
    if (!ambientClient) return
    
    ambientClient.clearMemory()
    setTranscriptionHistory([])
    setLastTranscription(null)
  }, [ambientClient])
  
  // Format session duration
  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }
  
  // Get status badge variant
  const getStatusBadge = () => {
    if (status.hardMute) return { variant: 'destructive' as const, text: 'HARD MUTE', icon: VolumeX }
    if (status.isMuted) return { variant: 'secondary' as const, text: 'MUTED', icon: MicOff }
    if (isActive && isConnected) return { variant: 'default' as const, text: 'LIVE', icon: Activity }
    if (connectionError) return { variant: 'destructive' as const, text: 'ERROR', icon: AlertTriangle }
    return { variant: 'outline' as const, text: 'OFF', icon: Mic }
  }
  
  const statusBadge = getStatusBadge()
  const StatusIcon = statusBadge.icon
  
  return (
    <Card className={`w-full max-w-md bg-black/40 backdrop-blur-md border-cyan-500/30 ${className}`}>
      <CardHeader className=\"pb-3\">
        <CardTitle className=\"flex items-center justify-between text-cyan-100 text-sm\">
          <span>B3 Ambient Voice</span>
          <Badge variant={statusBadge.variant} className=\"flex items-center gap-1\">
            <StatusIcon className=\"w-3 h-3\" />
            {statusBadge.text}
          </Badge>
        </CardTitle>
      </CardHeader>
      
      <CardContent className=\"space-y-4\">
        {/* Main controls */}
        <div className=\"flex gap-2\">
          {!isActive ? (
            <Button
              onClick={handleStart}
              disabled={isInitializing}
              className=\"flex-1 bg-cyan-600 hover:bg-cyan-700 text-white\"
            >
              {isInitializing ? (
                <>
                  <div className=\"w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2\" />
                  Starting...
                </>
              ) : (
                <>
                  <Mic className=\"w-4 h-4 mr-2\" />
                  Start Live
                </>
              )}
            </Button>
          ) : (
            <>
              <Button
                onClick={handleStop}
                variant=\"outline\"
                className=\"flex-1 border-red-500/50 text-red-400 hover:bg-red-500/10\"
              >
                <MicOff className=\"w-4 h-4 mr-2\" />
                Stop
              </Button>
              
              <Button
                onClick={handleMuteToggle}
                variant=\"outline\"
                disabled={status.hardMute}
                className={`
                  flex-1 border-yellow-500/50 
                  ${status.isMuted 
                    ? 'text-yellow-400 bg-yellow-500/10' 
                    : 'text-gray-400 hover:bg-yellow-500/10'
                  }
                `}
              >
                {status.isMuted ? <MicOff className=\"w-4 h-4 mr-2\" /> : <Mic className=\"w-4 h-4 mr-2\" />}
                {status.isMuted ? 'Unmute' : 'Mute'}
              </Button>
            </>
          )}
        </div>
        
        {/* Emergency hard mute */}
        {isActive && (
          <Button
            onClick={handleHardMute}
            variant=\"destructive\"
            size=\"sm\"
            className=\"w-full\"
          >
            <VolumeX className=\"w-4 h-4 mr-2\" />
            {status.hardMute ? 'Release Emergency Stop' : 'EMERGENCY STOP'}
          </Button>
        )}
        
        {/* Connection error */}
        {connectionError && (
          <div className=\"p-2 bg-red-500/10 border border-red-500/30 rounded text-red-400 text-sm\">
            <AlertTriangle className=\"w-4 h-4 inline mr-2\" />
            {connectionError}
          </div>
        )}
        
        {/* Status information */}
        {isActive && (
          <div className=\"space-y-2 text-xs text-gray-400\">
            <div className=\"flex justify-between\">
              <span>Session:</span>
              <span className=\"text-cyan-400\">{formatDuration(status.sessionDuration)}</span>
            </div>
            <div className=\"flex justify-between\">
              <span>Frames:</span>
              <span className=\"text-cyan-400\">{status.framesProcessed}</span>
            </div>
            <div className=\"flex justify-between\">
              <span>Buffer:</span>
              <span className=\"text-cyan-400\">{status.bufferSize}</span>
            </div>
          </div>
        )}
        
        {/* Last transcription */}
        {lastTranscription && (
          <div className=\"space-y-2\">
            <h4 className=\"text-sm font-medium text-cyan-100\">Latest Transcription</h4>
            <div className=\"p-2 bg-gray-800/50 rounded text-xs\">
              <div className=\"text-white\">{lastTranscription.text}</div>
              <div className=\"mt-1 flex justify-between items-center text-gray-500\">
                <span>Conf: {(lastTranscription.confidence * 100).toFixed(0)}%</span>
                <span>Score: {lastTranscription.importance_score}</span>
                {lastTranscription.will_store && (
                  <Badge variant=\"secondary\" className=\"text-xs py-0\">Stored</Badge>
                )}
              </div>
            </div>
          </div>
        )}
        
        {/* Clear memory button */}
        {isActive && transcriptionHistory.length > 0 && (
          <Button
            onClick={handleClearMemory}
            variant=\"ghost\"
            size=\"sm\"
            className=\"w-full text-gray-400 hover:text-white\"
          >
            Clear Memory ({transcriptionHistory.length} items)
          </Button>
        )}
      </CardContent>
    </Card>
  )
}