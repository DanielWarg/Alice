'use client'

import React, { useState, useEffect } from 'react'
import { Calendar, Clock, Plus, ChevronLeft, ChevronRight } from 'lucide-react'

/**
 * CalendarWidget - Kompakt kalenderwidget för Alice HUD
 * Visar kommande events och möjliggör snabbt skapande av nya
 */

interface CalendarEvent {
  id: string
  title: string
  start: Date
  end: Date
  type?: string
  attendees?: string[]
}

interface CalendarWidgetProps {
  compact?: boolean
  showCreateButton?: boolean
  onEventCreate?: (event: CalendarEvent) => void
  onEventClick?: (event: CalendarEvent) => void
}

export default function CalendarWidget({
  compact = false,
  showCreateButton = true,
  onEventCreate,
  onEventClick
}: CalendarWidgetProps) {
  const [events, setEvents] = useState<CalendarEvent[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedDate, setSelectedDate] = useState(new Date())
  const [showQuickCreate, setShowQuickCreate] = useState(false)

  // Ladda dagens events
  useEffect(() => {
    loadTodaysEvents()
  }, [])

  const loadTodaysEvents = async () => {
    setLoading(true)
    try {
      const today = new Date()
      const response = await fetch('/api/calendar/events', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          date_from: today.toISOString().split('T')[0],
          date_to: today.toISOString().split('T')[0]
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        const parsedEvents = data.events?.map((event: any) => ({
          id: event.id,
          title: event.summary || 'Untitled Event',
          start: new Date(event.start?.dateTime || event.start?.date),
          end: new Date(event.end?.dateTime || event.end?.date),
          type: event.eventType || 'meeting'
        })) || []
        setEvents(parsedEvents)
      }
    } catch (error) {
      console.error('Failed to load calendar events:', error)
    }
    setLoading(false)
  }

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('sv-SE', { 
      hour: '2-digit', 
      minute: '2-digit',
      hour12: false 
    })
  }

  const formatDate = (date: Date) => {
    return date.toLocaleDateString('sv-SE', {
      weekday: 'short',
      day: 'numeric',
      month: 'short'
    })
  }

  const isToday = (date: Date) => {
    const today = new Date()
    return date.toDateString() === today.toDateString()
  }

  const getEventTypeColor = (type: string) => {
    switch (type) {
      case 'meeting': return 'text-blue-400 bg-blue-500/10 border-blue-500/20'
      case 'lunch': return 'text-green-400 bg-green-500/10 border-green-500/20'  
      case 'personal': return 'text-purple-400 bg-purple-500/10 border-purple-500/20'
      case 'work': return 'text-cyan-400 bg-cyan-500/10 border-cyan-500/20'
      default: return 'text-zinc-400 bg-zinc-500/10 border-zinc-500/20'
    }
  }

  const getEventTypeIcon = (type: string) => {
    switch (type) {
      case 'meeting': return '🤝'
      case 'lunch': return '🍽️'
      case 'personal': return '👤'
      case 'work': return '💼'
      default: return '📅'
    }
  }

  if (compact) {
    return (
      <div className="bg-zinc-900/50 rounded-xl p-4 border border-zinc-700/50 backdrop-blur-sm" data-testid="calendar-widget-compact">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-cyan-400" />
            <span className="text-sm font-medium text-zinc-300" data-testid="calendar-widget-title">Kalender</span>
          </div>
          {showCreateButton && (
            <button
              onClick={() => setShowQuickCreate(!showQuickCreate)}
              className="p-1.5 rounded-lg bg-cyan-500/10 text-cyan-400 hover:bg-cyan-500/20 transition-colors"
              data-testid="calendar-widget-create-button"
            >
              <Plus className="w-3 h-3" />
            </button>
          )}
        </div>

        <div className="space-y-2" data-testid="calendar-widget-events-list">
          {loading ? (
            <div className="text-xs text-zinc-500" data-testid="calendar-widget-loading">Laddar events...</div>
          ) : events.length === 0 ? (
            <div className="text-xs text-zinc-500" data-testid="calendar-widget-no-events">Inga events idag</div>
          ) : (
            events.slice(0, 3).map((event) => (
              <div
                key={event.id}
                onClick={() => onEventClick?.(event)}
                className={`
                  p-2 rounded-lg border cursor-pointer transition-all hover:scale-[1.02]
                  ${getEventTypeColor(event.type || 'meeting')}
                `}
                data-testid={`calendar-widget-event-${event.id}`}
              >
                <div className="flex items-center gap-2">
                  <span className="text-xs">{getEventTypeIcon(event.type || 'meeting')}</span>
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-medium truncate">{event.title}</div>
                    <div className="text-xs opacity-70">
                      {formatTime(event.start)} - {formatTime(event.end)}
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {events.length > 3 && (
          <button className="w-full mt-2 text-xs text-cyan-400 hover:text-cyan-300 transition-colors">
            +{events.length - 3} fler events
          </button>
        )}
      </div>
    )
  }

  return (
    <div className="bg-zinc-900/50 rounded-xl p-6 border border-zinc-700/50 backdrop-blur-sm" data-testid="calendar-widget-full">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Calendar className="w-5 h-5 text-cyan-400" />
          <h2 className="text-lg font-semibold text-zinc-100" data-testid="calendar-widget-full-title">Kalender</h2>
        </div>
        {showCreateButton && (
          <button
            onClick={() => setShowQuickCreate(!showQuickCreate)}
            className="px-3 py-2 rounded-lg bg-cyan-500/10 text-cyan-400 hover:bg-cyan-500/20 transition-colors flex items-center gap-2"
            data-testid="calendar-widget-full-create-button"
          >
            <Plus className="w-4 h-4" />
            <span className="text-sm">Ny</span>
          </button>
        )}
      </div>

      {/* Quick Create */}
      {showQuickCreate && (
        <div className="mb-6 p-4 rounded-lg bg-zinc-800/50 border border-zinc-600/50" data-testid="calendar-widget-quick-create">
          <div className="text-sm font-medium text-zinc-300 mb-3">Snabbskapa event</div>
          <form onSubmit={(e) => {
            e.preventDefault()
            // Hantera snabbskapande
            setShowQuickCreate(false)
          }}>
            <input
              type="text"
              placeholder="Beskriv ditt event (t.ex. 'Möte med team imorgon kl 14')"
              className="w-full px-3 py-2 rounded-lg bg-zinc-700 text-zinc-100 placeholder-zinc-400 border border-zinc-600 focus:border-cyan-500 focus:outline-none"
              data-testid="calendar-widget-quick-create-input"
            />
            <div className="flex gap-2 mt-3">
              <button
                type="submit"
                className="px-4 py-2 rounded-lg bg-cyan-500 text-black font-medium hover:bg-cyan-400 transition-colors"
              >
                Skapa
              </button>
              <button
                type="button"
                onClick={() => setShowQuickCreate(false)}
                className="px-4 py-2 rounded-lg bg-zinc-700 text-zinc-300 hover:bg-zinc-600 transition-colors"
              >
                Avbryt
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Today's Events */}
      <div className="space-y-3">
        <h3 className="text-sm font-medium text-zinc-400 flex items-center gap-2">
          <Clock className="w-4 h-4" />
          {isToday(selectedDate) ? 'Idag' : formatDate(selectedDate)}
        </h3>

        {loading ? (
          <div className="text-sm text-zinc-500">Laddar events...</div>
        ) : events.length === 0 ? (
          <div className="text-sm text-zinc-500">Inga events schemalagda</div>
        ) : (
          <div className="space-y-2">
            {events.map((event) => (
              <div
                key={event.id}
                onClick={() => onEventClick?.(event)}
                className={`
                  p-3 rounded-lg border cursor-pointer transition-all hover:scale-[1.01]
                  ${getEventTypeColor(event.type || 'meeting')}
                `}
              >
                <div className="flex items-start gap-3">
                  <span className="text-lg">{getEventTypeIcon(event.type || 'meeting')}</span>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium truncate">{event.title}</div>
                    <div className="text-sm opacity-70 mt-1">
                      {formatTime(event.start)} - {formatTime(event.end)}
                    </div>
                    {event.attendees && event.attendees.length > 0 && (
                      <div className="text-xs opacity-60 mt-1">
                        {event.attendees.slice(0, 2).join(', ')}
                        {event.attendees.length > 2 && ` +${event.attendees.length - 2}`}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Navigation for different days */}
      <div className="flex items-center justify-between mt-6 pt-4 border-t border-zinc-700/50">
        <button
          onClick={() => {
            const yesterday = new Date(selectedDate)
            yesterday.setDate(yesterday.getDate() - 1)
            setSelectedDate(yesterday)
          }}
          className="p-2 rounded-lg text-zinc-400 hover:text-zinc-300 hover:bg-zinc-800/50 transition-colors"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>
        
        <button
          onClick={() => setSelectedDate(new Date())}
          className="text-sm text-cyan-400 hover:text-cyan-300 transition-colors"
        >
          Idag
        </button>
        
        <button
          onClick={() => {
            const tomorrow = new Date(selectedDate)
            tomorrow.setDate(tomorrow.getDate() + 1)
            setSelectedDate(tomorrow)
          }}
          className="p-2 rounded-lg text-zinc-400 hover:text-zinc-300 hover:bg-zinc-800/50 transition-colors"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}