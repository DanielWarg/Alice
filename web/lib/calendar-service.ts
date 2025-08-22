/**
 * Calendar Service - Frontend integration med Alice Calendar API
 * Hanterar all kommunikation med backend calendar endpoints
 */

import type { CalendarEvent } from '../components/calendar/CalendarWidget'

export interface CalendarApiResponse {
  success: boolean
  message?: string
  suggestions?: any[]
  result?: any
}

export interface ConflictCheckResult {
  has_conflict: boolean
  message: string
  conflicts?: Array<{
    title: string
    start: string
    end: string
    id: string
  }>
  suggestions?: Array<{
    start_time: Date
    end_time: Date
    formatted: string
    confidence: number
  }>
}

export class CalendarService {
  private baseUrl: string

  constructor(baseUrl: string = '') {
    this.baseUrl = baseUrl
  }

  /**
   * Formatera Date till svensk API-format
   */
  private formatDateForAPI(date: Date): string {
    return date.toLocaleString('sv-SE', {
      year: 'numeric',
      month: '2-digit', 
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    }).replace(',', '')
  }

  /**
   * Parse API datum tillbaka till Date objekt
   */
  private parseDateFromAPI(dateStr: string): Date {
    // Hantera olika format från Google Calendar API
    if (dateStr.includes('T')) {
      return new Date(dateStr)
    }
    // Fallback för svenska datum
    return new Date(dateStr)
  }

  /**
   * Hämta kommande kalenderhändelser
   */
  async getEvents(
    maxResults: number = 10,
    timeMin?: string,
    timeMax?: string
  ): Promise<CalendarEvent[]> {
    try {
      const params = new URLSearchParams({
        max_results: maxResults.toString()
      })
      
      if (timeMin) params.append('time_min', timeMin)
      if (timeMax) params.append('time_max', timeMax)

      const response = await fetch(`${this.baseUrl}/api/calendar/events?${params}`)
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const data: CalendarApiResponse = await response.json()
      
      if (!data.success) {
        throw new Error(data.message || 'API error')
      }

      // Parse responsen till CalendarEvent format
      // Här skulle vi behöva parsa backend responsen korrekt
      // För nu returnerar vi tom array och låter detta implementeras steg för steg
      return []
      
    } catch (error) {
      console.error('Fel vid hämtning av händelser:', error)
      throw error
    }
  }

  /**
   * Skapa ny kalenderhändelse
   */
  async createEvent(eventData: Partial<CalendarEvent>): Promise<CalendarEvent> {
    try {
      if (!eventData.title || !eventData.start || !eventData.end) {
        throw new Error('Titel, start- och sluttid krävs')
      }

      const payload = {
        title: eventData.title,
        start_time: this.formatDateForAPI(eventData.start),
        end_time: this.formatDateForAPI(eventData.end),
        description: eventData.description || null,
        attendees: [], // Skulle kunna implementeras senare
        check_conflicts: true
      }

      const response = await fetch(`${this.baseUrl}/api/calendar/events`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const data: CalendarApiResponse = await response.json()
      
      if (!data.success) {
        throw new Error(data.message || 'Kunde inte skapa händelse')
      }

      // Returnera den skapade händelsen
      return {
        id: `temp-${Date.now()}`, // Backend borde returnera ID
        title: eventData.title,
        start: eventData.start,
        end: eventData.end,
        description: eventData.description,
        type: eventData.type || 'meeting'
      }

    } catch (error) {
      console.error('Fel vid skapande av händelse:', error)
      throw error
    }
  }

  /**
   * Uppdatera befintlig händelse
   */
  async updateEvent(eventData: CalendarEvent): Promise<CalendarEvent> {
    try {
      const payload = {
        event_id: eventData.id,
        title: eventData.title,
        start_time: this.formatDateForAPI(eventData.start),
        end_time: this.formatDateForAPI(eventData.end),
        description: eventData.description || null
      }

      const response = await fetch(`${this.baseUrl}/api/calendar/events`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const data: CalendarApiResponse = await response.json()
      
      if (!data.success) {
        throw new Error(data.message || 'Kunde inte uppdatera händelse')
      }

      return eventData

    } catch (error) {
      console.error('Fel vid uppdatering av händelse:', error)
      throw error
    }
  }

  /**
   * Ta bort händelse
   */
  async deleteEvent(eventId: string): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/api/calendar/events/${eventId}`, {
        method: 'DELETE'
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const data: CalendarApiResponse = await response.json()
      
      if (!data.success) {
        throw new Error(data.message || 'Kunde inte ta bort händelse')
      }

    } catch (error) {
      console.error('Fel vid borttagning av händelse:', error)
      throw error
    }
  }

  /**
   * Sök efter händelser
   */
  async searchEvents(query: string, maxResults: number = 20): Promise<CalendarEvent[]> {
    try {
      const response = await fetch(`${this.baseUrl}/api/calendar/events/search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          query,
          max_results: maxResults
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const data: CalendarApiResponse = await response.json()
      
      if (!data.success) {
        throw new Error(data.message || 'Sökning misslyckades')
      }

      // Parse sökresutat till CalendarEvent format
      return []

    } catch (error) {
      console.error('Fel vid sökning av händelser:', error)
      throw error
    }
  }

  /**
   * Kontrollera konflikter för föreslagen tid
   */
  async checkConflicts(
    startTime: Date,
    endTime: Date,
    excludeEventId?: string
  ): Promise<ConflictCheckResult> {
    try {
      const payload = {
        start_time: this.formatDateForAPI(startTime),
        end_time: this.formatDateForAPI(endTime),
        exclude_event_id: excludeEventId || null
      }

      const response = await fetch(`${this.baseUrl}/api/calendar/check-conflicts`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const data: CalendarApiResponse = await response.json()
      
      if (!data.success) {
        throw new Error(data.message || 'Konfliktkolning misslyckades')
      }

      return data.result as ConflictCheckResult

    } catch (error) {
      console.error('Fel vid konfliktkolning:', error)
      throw error
    }
  }

  /**
   * Få förslag på lämpliga mötestider
   */
  async getSuggestedTimes(
    durationMinutes: number = 60,
    datePreference?: Date,
    maxSuggestions: number = 5
  ): Promise<Array<{
    start_time: Date
    end_time: Date
    formatted: string
    confidence: number
  }>> {
    try {
      const payload = {
        duration_minutes: durationMinutes,
        date_preference: datePreference ? this.formatDateForAPI(datePreference) : null,
        max_suggestions: maxSuggestions
      }

      const response = await fetch(`${this.baseUrl}/api/calendar/suggest-times`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const data: CalendarApiResponse = await response.json()
      
      if (!data.success) {
        throw new Error(data.message || 'Kunde inte hämta förslag')
      }

      // Konvertera API-respons till Date objekt
      return (data.suggestions || []).map((suggestion: any) => ({
        ...suggestion,
        start_time: new Date(suggestion.start_time),
        end_time: new Date(suggestion.end_time)
      }))

    } catch (error) {
      console.error('Fel vid hämtning av förslag:', error)
      throw error
    }
  }

  /**
   * Parse svenska röstkommandon till calendar actions
   */
  parseVoiceCommand(command: string): {
    action: 'create' | 'list' | 'search' | 'delete' | 'update' | null
    params: any
  } {
    const lowerCommand = command.toLowerCase().trim()

    // Skapa händelse
    const createPatterns = [
      /(?:skapa|boka|lägg till|planera|schemalägg)\s+(.+)/,
      /(?:ny|nytt)\s+(?:möte|händelse|tid)\s+(.+)/,
      /(?:sätt upp|arrangera|reservera)\s+(.+)/
    ]

    for (const pattern of createPatterns) {
      const match = lowerCommand.match(pattern)
      if (match) {
        return {
          action: 'create',
          params: { description: match[1] }
        }
      }
    }

    // Lista händelser
    const listPatterns = [
      /(?:visa|lista|kolla)\s+(?:mina\s+)?(?:möten|kalendern?|schema)/,
      /vad\s+(?:har jag|står)\s+(?:för\s+)?(?:möten|i kalendern)/,
      /(?:hur ser|vad finns i)\s+(?:min\s+)?kalender/
    ]

    for (const pattern of listPatterns) {
      if (pattern.test(lowerCommand)) {
        return {
          action: 'list',
          params: {}
        }
      }
    }

    // Sök händelser
    const searchPatterns = [
      /(?:sök|hitta|leta)\s+(?:efter\s+)?(.+)/,
      /när\s+har\s+jag\s+(.+)/,
      /vilken\s+dag\s+(?:har jag|är)\s+(.+)/
    ]

    for (const pattern of searchPatterns) {
      const match = lowerCommand.match(pattern)
      if (match) {
        return {
          action: 'search',
          params: { query: match[1] }
        }
      }
    }

    return { action: null, params: {} }
  }
}

// Global instans för användning i komponenter
export const calendarService = new CalendarService()