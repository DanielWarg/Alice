'use client'

import React, { useState, useEffect, useCallback } from 'react'
import CalendarWidget, { type CalendarEvent } from './CalendarWidget'
import CalendarEventModal from './CalendarEventModal'
import { calendarService } from '../../lib/calendar-service'

// Icons 
const Svg = (p: any) => (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" {...p} />)
const IconPlus = (p: any) => (<Svg {...p}><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></Svg>)
const IconRefresh = (p: any) => (<Svg {...p}><polyline points="23 4 23 10 17 10" /><polyline points="1 20 1 14 7 14" /><path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15" /></Svg>)
const IconMic = (p: any) => (<Svg {...p}><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" /><path d="M19 10v2a7 7 0 0 1-14 0v-2" /><line x1="12" y1="19" x2="12" y2="23" /><line x1="8" y1="23" x2="16" y2="23" /></Svg>)
const IconMicOff = (p: any) => (<Svg {...p}><line x1="1" y1="1" x2="23" y2="23" /><path d="M9 9v3a3 3 0 0 0 5.12 2.12L9 9z" /><path d="M12 2a3 3 0 0 1 3 3v4L12 2z" /><path d="M19 10v2a7 7 0 0 1-.11 1.23" /><line x1="12" y1="19" x2="12" y2="23" /><line x1="8" y1="23" x2="16" y2="23" /></Svg>)

// GlowDot komponent
const GlowDot = ({ className }: { className?: string }) => (
  <div className={`relative ${className}`}>
    <span className="absolute inset-0 rounded-full blur-[6px] bg-cyan-400/40" />
    <span className="absolute inset-0 rounded-full blur-[14px] bg-cyan-400/20" />
    <span className="relative block h-full w-full rounded-full bg-cyan-300" />
  </div>
)

export interface CalendarHUDProps {
  className?: string
  enableVoiceCommands?: boolean
  compact?: boolean
  maxUpcomingEvents?: number
}

export default function CalendarHUD({
  className = "",
  enableVoiceCommands = true,
  compact = false,
  maxUpcomingEvents = 5
}: CalendarHUDProps) {
  const [events, setEvents] = useState<CalendarEvent[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showModal, setShowModal] = useState(false)
  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null)
  const [selectedDate, setSelectedDate] = useState<Date | null>(null)
  const [voiceActive, setVoiceActive] = useState(false)
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date())

  // Ladda händelser vid start och regelbundet
  const loadEvents = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const loadedEvents = await calendarService.getEvents(maxUpcomingEvents)
      setEvents(loadedEvents)
      setLastRefresh(new Date())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Okänt fel')
      console.error('Fel vid laddning av händelser:', err)
    } finally {
      setLoading(false)
    }
  }, [maxUpcomingEvents])

  useEffect(() => {
    loadEvents()
    
    // Auto-refresh var 5:e minut
    const interval = setInterval(loadEvents, 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [loadEvents])

  // Hantera röstkommandon
  const handleVoiceCommand = useCallback(async (command: string) => {
    if (!enableVoiceCommands) return

    console.log('Calendar voice command:', command)
    setVoiceActive(true)

    try {
      const parsed = calendarService.parseVoiceCommand(command)
      
      switch (parsed.action) {
        case 'create':
          // Öppna modal för att skapa händelse
          setSelectedEvent(null)
          setSelectedDate(new Date())
          setShowModal(true)
          break
          
        case 'list':
          // Uppdatera händelselista
          await loadEvents()
          break
          
        case 'search':
          // Sök händelser (implementeras vid behov)
          if (parsed.params.query) {
            const searchResults = await calendarService.searchEvents(parsed.params.query)
            setEvents(searchResults)
          }
          break
          
        default:
          console.log('Okänt calendar-kommando:', command)
      }
    } catch (error) {
      console.error('Fel vid bearbetning av röstkommando:', error)
      setError('Kunde inte bearbeta röstkommando')
    } finally {
      setTimeout(() => setVoiceActive(false), 1000)
    }
  }, [enableVoiceCommands, loadEvents])

  // Event handlers
  const handleEventCreate = async (eventData: Partial<CalendarEvent>) => {
    try {
      const newEvent = await calendarService.createEvent(eventData)
      setEvents(prev => [...prev, newEvent])
      setShowModal(false)
      setSelectedEvent(null)
      setSelectedDate(null)
    } catch (error) {
      console.error('Fel vid skapande av händelse:', error)
      setError('Kunde inte skapa händelse')
    }
  }

  const handleEventUpdate = async (eventData: CalendarEvent) => {
    try {
      const updatedEvent = await calendarService.updateEvent(eventData)
      setEvents(prev => prev.map(e => e.id === updatedEvent.id ? updatedEvent : e))
      setShowModal(false)
      setSelectedEvent(null)
    } catch (error) {
      console.error('Fel vid uppdatering av händelse:', error)
      setError('Kunde inte uppdatera händelse')
    }
  }

  const handleEventDelete = async (eventId: string) => {
    try {
      await calendarService.deleteEvent(eventId)
      setEvents(prev => prev.filter(e => e.id !== eventId))
    } catch (error) {
      console.error('Fel vid borttagning av händelse:', error)
      setError('Kunde inte ta bort händelse')
    }
  }

  const handleEventClick = (event: CalendarEvent) => {
    setSelectedEvent(event)
    setShowModal(true)
  }

  const handleQuickAdd = () => {
    setSelectedEvent(null)
    setSelectedDate(selectedDate || new Date())
    setShowModal(true)
  }

  const handleDateSelect = (date: Date) => {
    setSelectedDate(date)
  }

  return (
    <div className={`relative ${className}`}>
      {/* Huvudcalendar widget */}
      <CalendarWidget
        events={events}
        loading={loading}
        compact={compact}
        onEventClick={handleEventClick}
        onDateSelect={handleDateSelect}
        onQuickAdd={handleQuickAdd}
        onEventCreate={handleEventCreate}
        onEventUpdate={handleEventUpdate}
        onEventDelete={handleEventDelete}
        enableVoiceCommands={enableVoiceCommands}
        className="mb-4"
      />

      {/* Kontrollpanel */}
      <div className="flex items-center justify-between p-3 bg-cyan-950/20 border border-cyan-500/20 rounded-lg">
        <div className="flex items-center gap-2">
          <GlowDot className="h-2 w-2" />
          <span className="text-xs text-cyan-300/80">
            Senast uppdaterad: {lastRefresh.toLocaleTimeString('sv-SE', { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Voice status indikator */}
          {enableVoiceCommands && (
            <div className={`p-1.5 rounded-lg transition-all duration-200 ${
              voiceActive 
                ? 'bg-green-500/20 text-green-400' 
                : 'bg-cyan-500/10 text-cyan-400/60'
            }`}>
              {voiceActive ? <IconMic className="h-3 w-3" /> : <IconMicOff className="h-3 w-3" />}
            </div>
          )}

          {/* Refresh knapp */}
          <button
            onClick={loadEvents}
            disabled={loading}
            className="p-1.5 rounded-lg bg-cyan-500/10 text-cyan-400 hover:bg-cyan-500/20 
                     transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title="Uppdatera kalendern"
          >
            <IconRefresh className={`h-3 w-3 ${loading ? 'animate-spin' : ''}`} />
          </button>

          {/* Add event knapp */}
          <button
            onClick={handleQuickAdd}
            className="p-1.5 rounded-lg bg-cyan-500/20 text-cyan-300 hover:bg-cyan-500/30 
                     transition-colors"
            title="Skapa ny händelse"
          >
            <IconPlus className="h-3 w-3" />
          </button>
        </div>
      </div>

      {/* Kommande händelser (compact view) */}
      {compact && events.length > 0 && (
        <div className="mt-3 p-3 bg-cyan-950/10 border border-cyan-500/10 rounded-lg">
          <h4 className="text-xs text-cyan-300/80 mb-2 flex items-center gap-2">
            <GlowDot className="h-1.5 w-1.5" />
            Kommande händelser
          </h4>
          <div className="space-y-1">
            {events.slice(0, 3).map((event) => (
              <button
                key={event.id}
                onClick={() => handleEventClick(event)}
                className="w-full text-left p-2 rounded bg-cyan-900/20 hover:bg-cyan-900/30 
                         transition-colors border border-cyan-500/10"
              >
                <div className="text-xs text-cyan-100 font-medium truncate">
                  {event.title}
                </div>
                <div className="text-[10px] text-cyan-300/70">
                  {event.start.toLocaleString('sv-SE', { 
                    month: 'short', 
                    day: 'numeric',
                    hour: '2-digit', 
                    minute: '2-digit' 
                  })}
                </div>
              </button>
            ))}
            {events.length > 3 && (
              <div className="text-[10px] text-cyan-300/60 text-center py-1">
                +{events.length - 3} fler händelser
              </div>
            )}
          </div>
        </div>
      )}

      {/* Felmeddelande */}
      {error && (
        <div className="mt-3 p-2 bg-red-500/10 border border-red-500/30 rounded-lg">
          <p className="text-xs text-red-300">{error}</p>
          <button
            onClick={() => setError(null)}
            className="text-[10px] text-red-400 hover:text-red-300 mt-1"
          >
            Stäng
          </button>
        </div>
      )}

      {/* Event Modal */}
      <CalendarEventModal
        isOpen={showModal}
        onClose={() => {
          setShowModal(false)
          setSelectedEvent(null)
          setSelectedDate(null)
        }}
        onSave={selectedEvent ? handleEventUpdate : handleEventCreate}
        event={selectedEvent}
        defaultDate={selectedDate}
        conflictCheckEnabled={true}
      />

      {/* Voice Commands Integration */}
      {enableVoiceCommands && (
        <div className="sr-only" aria-live="polite">
          Calendar voice commands: 
          &quot;skapa möte&quot;, &quot;visa kalendern&quot;, &quot;sök händelser&quot;
        </div>
      )}
    </div>
  )
}