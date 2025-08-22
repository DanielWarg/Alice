'use client'

import React, { useState, useEffect } from 'react'
import type { CalendarEvent } from './CalendarWidget'

// Icons följer samma mönster som andra komponenter
const Svg = (p: any) => (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" {...p} />)
const IconX = (p: any) => (<Svg {...p}><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></Svg>)
const IconCalendar = (p: any) => (<Svg {...p}><rect x="3" y="4" width="18" height="18" rx="2" /><line x1="3" y1="10" x2="21" y2="10" /></Svg>)
const IconClock = (p: any) => (<Svg {...p}><circle cx="12" cy="12" r="10" /><polyline points="12,6 12,12 16,14" /></Svg>)
const IconUser = (p: any) => (<Svg {...p}><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></Svg>)
const IconSave = (p: any) => (<Svg {...p}><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" /><polyline points="17,21 17,13 7,13 7,21" /><polyline points="7,3 7,8 15,8" /></Svg>)
const IconAlertTriangle = (p: any) => (<Svg {...p}><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></Svg>)

// GlowDot komponent från huvudapplikationen
const GlowDot = ({ className }: { className?: string }) => (
  <div className={`relative ${className}`}>
    <span className="absolute inset-0 rounded-full blur-[6px] bg-cyan-400/40" />
    <span className="absolute inset-0 rounded-full blur-[14px] bg-cyan-400/20" />
    <span className="relative block h-full w-full rounded-full bg-cyan-300" />
  </div>
)

export interface CalendarEventModalProps {
  isOpen: boolean
  onClose: () => void
  onSave: (event: Partial<CalendarEvent>) => Promise<void>
  event?: CalendarEvent | null
  defaultDate?: Date
  conflictCheckEnabled?: boolean
}

interface ConflictSuggestion {
  start_time: Date
  end_time: Date
  formatted: string
  confidence: number
}

interface ConflictResult {
  has_conflict: boolean
  message: string
  conflicts?: Array<{
    title: string
    start: string
    end: string
    id: string
  }>
  suggestions?: ConflictSuggestion[]
}

export default function CalendarEventModal({
  isOpen,
  onClose,
  onSave,
  event = null,
  defaultDate,
  conflictCheckEnabled = true
}: CalendarEventModalProps) {
  const [formData, setFormData] = useState({
    title: '',
    start: '',
    end: '',
    description: '',
    attendees: ''
  })
  
  const [loading, setLoading] = useState(false)
  const [conflicts, setConflicts] = useState<ConflictResult | null>(null)
  const [showConflicts, setShowConflicts] = useState(false)
  const [suggestions, setSuggestions] = useState<ConflictSuggestion[]>([])

  // Återställ form när modal öppnas/stängs eller event ändras
  useEffect(() => {
    if (event) {
      // Editing existing event
      setFormData({
        title: event.title || '',
        start: formatDateTimeForInput(event.start),
        end: formatDateTimeForInput(event.end),
        description: event.description || '',
        attendees: '' // Attendees skulle behöva läggas till i CalendarEvent interface
      })
    } else if (defaultDate) {
      // Creating new event with default date
      const defaultStart = new Date(defaultDate)
      defaultStart.setHours(9, 0, 0, 0)
      const defaultEnd = new Date(defaultStart)
      defaultEnd.setHours(10, 0, 0, 0)
      
      setFormData({
        title: '',
        start: formatDateTimeForInput(defaultStart),
        end: formatDateTimeForInput(defaultEnd),
        description: '',
        attendees: ''
      })
    } else {
      // Reset form
      const now = new Date()
      const nextHour = new Date(now)
      nextHour.setHours(now.getHours() + 1, 0, 0, 0)
      
      setFormData({
        title: '',
        start: formatDateTimeForInput(now),
        end: formatDateTimeForInput(nextHour),
        description: '',
        attendees: ''
      })
    }
    
    setConflicts(null)
    setShowConflicts(false)
    setSuggestions([])
  }, [event, defaultDate, isOpen])

  const formatDateTimeForInput = (date: Date): string => {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const hours = String(date.getHours()).padStart(2, '0')
    const minutes = String(date.getMinutes()).padStart(2, '0')
    return `${year}-${month}-${day}T${hours}:${minutes}`
  }

  const formatDateTimeForAPI = (dateTimeLocal: string): string => {
    const date = new Date(dateTimeLocal)
    return date.toLocaleString('sv-SE', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    }).replace(',', '')
  }

  const checkForConflicts = async () => {
    if (!conflictCheckEnabled || !formData.start || !formData.end) return

    try {
      const response = await fetch('/api/calendar/check-conflicts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          start_time: formatDateTimeForAPI(formData.start),
          end_time: formatDateTimeForAPI(formData.end),
          exclude_event_id: event?.id
        })
      })

      if (response.ok) {
        const data = await response.json()
        if (data.success) {
          setConflicts(data.result)
          setShowConflicts(data.result.has_conflict)
          
          // Hämta förslag om det finns konflikter
          if (data.result.has_conflict) {
            await getSuggestions()
          }
        }
      }
    } catch (error) {
      console.error('Fel vid konfliktkolning:', error)
    }
  }

  const getSuggestions = async () => {
    try {
      const startDate = new Date(formData.start)
      const endDate = new Date(formData.end)
      const duration = Math.round((endDate.getTime() - startDate.getTime()) / (1000 * 60))

      const response = await fetch('/api/calendar/suggest-times', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          duration_minutes: duration,
          date_preference: formatDateTimeForAPI(formData.start),
          max_suggestions: 3
        })
      })

      if (response.ok) {
        const data = await response.json()
        if (data.success && data.suggestions) {
          setSuggestions(data.suggestions.map((s: any) => ({
            ...s,
            start_time: new Date(s.start_time),
            end_time: new Date(s.end_time)
          })))
        }
      }
    } catch (error) {
      console.error('Fel vid hämtning av förslag:', error)
    }
  }

  const applySuggestion = (suggestion: ConflictSuggestion) => {
    setFormData(prev => ({
      ...prev,
      start: formatDateTimeForInput(suggestion.start_time),
      end: formatDateTimeForInput(suggestion.end_time)
    }))
    setShowConflicts(false)
    setConflicts(null)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.title.trim()) return

    setLoading(true)
    try {
      const eventData: Partial<CalendarEvent> = {
        title: formData.title,
        start: new Date(formData.start),
        end: new Date(formData.end),
        description: formData.description || undefined
      }

      if (event) {
        eventData.id = event.id
      }

      await onSave(eventData)
      onClose()
    } catch (error) {
      console.error('Fel vid sparande av händelse:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleInputChange = (field: keyof typeof formData, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }))
    
    // Auto-adjust end time when start time changes
    if (field === 'start') {
      const startDate = new Date(value)
      const currentEnd = new Date(formData.end)
      const duration = currentEnd.getTime() - new Date(formData.start).getTime()
      
      if (duration > 0) {
        const newEnd = new Date(startDate.getTime() + duration)
        setFormData(prev => ({ ...prev, end: formatDateTimeForInput(newEnd) }))
      }
    }
  }

  // Kontrollera konflikter när start/end tid ändras
  useEffect(() => {
    if (formData.start && formData.end && conflictCheckEnabled) {
      const timer = setTimeout(checkForConflicts, 500) // Debounce
      return () => clearTimeout(timer)
    }
  }, [formData.start, formData.end])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="relative w-full max-w-lg mx-4 bg-cyan-950/90 border border-cyan-500/30 rounded-2xl shadow-[0_0_60px_-20px_rgba(34,211,238,.5)]">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-cyan-500/20">
          <div className="flex items-center gap-3">
            <GlowDot className="h-3 w-3" />
            <h2 className="text-lg font-medium text-cyan-100">
              {event ? 'Redigera händelse' : 'Ny händelse'}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-cyan-400/10 transition-colors text-cyan-300"
          >
            <IconX className="h-5 w-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Title */}
          <div>
            <label className="flex items-center gap-2 text-sm text-cyan-300/80 mb-2">
              <IconCalendar className="h-4 w-4" />
              Titel
            </label>
            <input
              type="text"
              value={formData.title}
              onChange={(e) => handleInputChange('title', e.target.value)}
              placeholder="Händelsens titel..."
              className="w-full px-3 py-2 bg-cyan-900/30 border border-cyan-500/20 rounded-lg 
                         text-cyan-100 placeholder-cyan-400/50 focus:outline-none focus:border-cyan-400/60"
              required
            />
          </div>

          {/* Start Time */}
          <div>
            <label className="flex items-center gap-2 text-sm text-cyan-300/80 mb-2">
              <IconClock className="h-4 w-4" />
              Starttid
            </label>
            <input
              type="datetime-local"
              value={formData.start}
              onChange={(e) => handleInputChange('start', e.target.value)}
              className="w-full px-3 py-2 bg-cyan-900/30 border border-cyan-500/20 rounded-lg 
                         text-cyan-100 focus:outline-none focus:border-cyan-400/60"
              required
            />
          </div>

          {/* End Time */}
          <div>
            <label className="flex items-center gap-2 text-sm text-cyan-300/80 mb-2">
              <IconClock className="h-4 w-4" />
              Sluttid
            </label>
            <input
              type="datetime-local"
              value={formData.end}
              onChange={(e) => handleInputChange('end', e.target.value)}
              className="w-full px-3 py-2 bg-cyan-900/30 border border-cyan-500/20 rounded-lg 
                         text-cyan-100 focus:outline-none focus:border-cyan-400/60"
              required
            />
          </div>

          {/* Conflict Warning */}
          {showConflicts && conflicts?.has_conflict && (
            <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg">
              <div className="flex items-start gap-2">
                <IconAlertTriangle className="h-4 w-4 text-amber-400 mt-0.5 flex-shrink-0" />
                <div className="flex-1">
                  <p className="text-sm text-amber-200">{conflicts.message}</p>
                  
                  {suggestions.length > 0 && (
                    <div className="mt-3">
                      <p className="text-xs text-amber-300/80 mb-2">Föreslagna alternativ:</p>
                      <div className="space-y-1">
                        {suggestions.map((suggestion, index) => (
                          <button
                            key={index}
                            type="button"
                            onClick={() => applySuggestion(suggestion)}
                            className="block w-full text-left px-2 py-1 text-xs bg-amber-500/20 
                                     hover:bg-amber-500/30 rounded text-amber-100 transition-colors"
                          >
                            {suggestion.formatted} (förtroende: {Math.round(suggestion.confidence * 100)}%)
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Description */}
          <div>
            <label className="flex items-center gap-2 text-sm text-cyan-300/80 mb-2">
              <IconUser className="h-4 w-4" />
              Beskrivning (valfritt)
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => handleInputChange('description', e.target.value)}
              placeholder="Lägg till en beskrivning..."
              rows={3}
              className="w-full px-3 py-2 bg-cyan-900/30 border border-cyan-500/20 rounded-lg 
                         text-cyan-100 placeholder-cyan-400/50 focus:outline-none focus:border-cyan-400/60
                         resize-none"
            />
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-cyan-500/30 text-cyan-300 rounded-lg 
                         hover:bg-cyan-400/10 transition-colors"
            >
              Avbryt
            </button>
            <button
              type="submit"
              disabled={loading || !formData.title.trim()}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2 
                         bg-cyan-500/20 text-cyan-100 rounded-lg hover:bg-cyan-500/30 
                         transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <IconSave className="h-4 w-4" />
              {loading ? 'Sparar...' : event ? 'Uppdatera' : 'Skapa'}
            </button>
          </div>
        </form>

        {/* Inner ring för konsistent stil */}
        <div className="pointer-events-none absolute inset-0 rounded-2xl ring-1 ring-inset ring-cyan-300/10" />
      </div>
    </div>
  )
}