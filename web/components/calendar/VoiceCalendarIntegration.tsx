'use client'

import React, { useState, useCallback } from 'react'
import VoiceBox, { type VoiceBoxProps } from '../VoiceBox'
import CalendarHUD from './CalendarHUD'
import { calendarService } from '../../lib/calendar-service'

/**
 * Integration mellan VoiceBox och Calendar för naturliga röstkommandon
 * Exempel på hur Alice kan hantera calendar-kommandon via röst
 */

export interface VoiceCalendarIntegrationProps {
  className?: string
  voiceBoxProps?: Partial<VoiceBoxProps>
  calendarCompact?: boolean
  enableSmartParsing?: boolean
}

export default function VoiceCalendarIntegration({
  className = "",
  voiceBoxProps = {},
  calendarCompact = false,
  enableSmartParsing = true
}: VoiceCalendarIntegrationProps) {
  const [isProcessingVoice, setIsProcessingVoice] = useState(false)
  const [lastCommand, setLastCommand] = useState<string>('')
  const [feedback, setFeedback] = useState<string>('')

  /**
   * Avancerad parsning av svenska calendar-kommandon
   */
  const parseAdvancedCalendarCommand = (command: string): {
    action: string
    params: any
    confidence: number
  } => {
    const lowerCommand = command.toLowerCase().trim()

    // Skapa händelse med detaljer
    const createWithDetailsPattern = /(?:skapa|boka|lägg till|planera)\s+(?:ett?\s+)?(?:möte|händelse|tid)\s+(?:med\s+)?(.+?)\s+(?:på|imorgon|idag|nästa|fredag|måndag|tisdag|onsdag|torsdag|lördag|söndag)\s*(?:kl\s*)?(\d{1,2}(?:[:\.]?\d{2})?)?/
    
    let match = lowerCommand.match(createWithDetailsPattern)
    if (match) {
      const title = match[1]
      const time = match[2] || '09:00'
      return {
        action: 'create_detailed',
        params: { title, time, rawCommand: command },
        confidence: 0.9
      }
    }

    // Vanliga calendar patterns från calendarService
    const basicParsing = calendarService.parseVoiceCommand(command)
    if (basicParsing.action) {
      return {
        action: basicParsing.action,
        params: basicParsing.params,
        confidence: 0.7
      }
    }

    // Kontrollera om det är calendar-relaterat även om vi inte kan parsa exakt
    const calendarKeywords = [
      'kalender', 'möte', 'händelse', 'tid', 'schema', 'boka', 'planera',
      'imorgon', 'idag', 'nästa vecka', 'fredag', 'måndag'
    ]
    
    const hasCalendarKeyword = calendarKeywords.some(keyword => 
      lowerCommand.includes(keyword)
    )

    if (hasCalendarKeyword) {
      return {
        action: 'calendar_general',
        params: { rawCommand: command },
        confidence: 0.4
      }
    }

    return {
      action: 'unknown',
      params: {},
      confidence: 0
    }
  }

  /**
   * Huvudhanterare för röstinput från VoiceBox
   */
  const handleVoiceInput = useCallback(async (voiceText: string) => {
    console.log('Voice Calendar Input:', voiceText)
    setLastCommand(voiceText)
    setIsProcessingVoice(true)
    setFeedback('')

    try {
      if (!enableSmartParsing) {
        // Enkel mode - skicka direkt till calendar service
        const parsed = calendarService.parseVoiceCommand(voiceText)
        if (parsed.action) {
          setFeedback(`Utför ${parsed.action} för calendar`)
        } else {
          setFeedback('Inget calendar-kommando upptäckt')
        }
        return
      }

      // Avancerad parsning
      const parsed = parseAdvancedCalendarCommand(voiceText)
      
      if (parsed.confidence < 0.3) {
        setFeedback('Jag förstod inte det som ett calendar-kommando')
        return
      }

      switch (parsed.action) {
        case 'create_detailed':
          setFeedback(`Skapar möte: "${parsed.params.title}" kl ${parsed.params.time}`)
          // Här skulle vi kunna integrera med backend eller öppna modal
          break

        case 'create':
          setFeedback('Öppnar skapa händelse-dialog')
          break

        case 'list':
          setFeedback('Visar kommande händelser')
          break

        case 'search':
          setFeedback(`Söker efter: "${parsed.params.query}"`)
          break

        case 'calendar_general':
          setFeedback('Det verkar vara calendar-relaterat, men jag förstod inte exakt vad du vill göra')
          break

        default:
          setFeedback('Okänt calendar-kommando')
      }

    } catch (error) {
      console.error('Fel vid bearbetning av röstkommando:', error)
      setFeedback('Fel vid bearbetning av kommando')
    } finally {
      setIsProcessingVoice(false)
      
      // Rensa feedback efter 3 sekunder
      setTimeout(() => setFeedback(''), 3000)
    }
  }, [enableSmartParsing])

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Voice Interface */}
      <div className="relative">
        <VoiceBox
          {...voiceBoxProps}
          onVoiceInput={handleVoiceInput}
          label="ALICE CALENDAR"
          personality="alice"
          emotion="friendly"
        />
        
        {/* Voice Status Overlay */}
        {isProcessingVoice && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/20 rounded-2xl">
            <div className="px-3 py-1 bg-cyan-500/20 border border-cyan-400/30 rounded-lg">
              <span className="text-xs text-cyan-100">Bearbetar kommando...</span>
            </div>
          </div>
        )}
      </div>

      {/* Feedback Display */}
      {(feedback || lastCommand) && (
        <div className="p-3 bg-cyan-950/20 border border-cyan-500/20 rounded-lg">
          {lastCommand && (
            <div className="mb-2">
              <span className="text-xs text-cyan-300/60">Senaste kommando:</span>
              <p className="text-sm text-cyan-200">"{lastCommand}"</p>
            </div>
          )}
          {feedback && (
            <div>
              <span className="text-xs text-cyan-300/60">Respons:</span>
              <p className="text-sm text-cyan-100">{feedback}</p>
            </div>
          )}
        </div>
      )}

      {/* Calendar HUD */}
      <CalendarHUD
        compact={calendarCompact}
        enableVoiceCommands={false} // Avstängt eftersom vi hanterar det här
        className="w-full"
      />

      {/* Voice Command Help */}
      <div className="p-3 bg-cyan-950/10 border border-cyan-500/10 rounded-lg">
        <h4 className="text-xs text-cyan-300/80 mb-2">Röstkommandon för kalender:</h4>
        <div className="text-xs text-cyan-300/60 space-y-1">
          <p>• "Skapa möte imorgon kl 14:00"</p>
          <p>• "Boka tid för tandläkare på fredag"</p>
          <p>• "Visa mina möten denna vecka"</p>
          <p>• "Sök efter möte med Jonas"</p>
          <p>• "Vad har jag för möten imorgon"</p>
        </div>
      </div>
    </div>
  )
}