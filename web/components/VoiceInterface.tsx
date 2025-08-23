'use client'

import React, { useEffect, useState, useRef } from 'react'
import VoiceBox from './VoiceBox'

/**
 * Alice Voice Interface - Kombinerar VoiceBox med Alice's röst-system
 */
export default function VoiceInterface() {
    const [isConnected, setIsConnected] = useState(false)
    const [isListening, setIsListening] = useState(false)
    const [lastMessage, setLastMessage] = useState('')
    const [aliceResponse, setAliceResponse] = useState('')
    const [status, setStatus] = useState('Anslutning...')
    const [conversation, setConversation] = useState<Array<{type: 'user' | 'alice', text: string, timestamp: Date}>>([])
    
    const wsRef = useRef<WebSocket | null>(null)
    const sessionId = useRef(`voice_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`)

    useEffect(() => {
        connectToAlice()
        return () => {
            if (wsRef.current) {
                wsRef.current.close()
            }
        }
    }, [])

    const connectToAlice = () => {
        try {
            // För utveckling, använd hårdkodad URL
            const wsUrl = 'ws://127.0.0.1:8000/ws/voice/' + sessionId.current
            
            console.log('Ansluter till Alice:', wsUrl)
            wsRef.current = new WebSocket(wsUrl)
            
            wsRef.current.onopen = () => {
                setIsConnected(true)
                setStatus('Ansluten till Alice')
                console.log('Alice voice connection established')
                
                // Skicka ping för att testa anslutningen
                wsRef.current?.send(JSON.stringify({ type: 'ping' }))
            }
            
            wsRef.current.onclose = () => {
                setIsConnected(false)
                setStatus('Frånkopplad från Alice')
                console.log('Alice voice connection closed')
            }
            
            wsRef.current.onerror = (error) => {
                console.error('Alice voice connection error:', error)
                setStatus('Anslutningsfel')
            }
            
            wsRef.current.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data)
                    handleAliceMessage(data)
                } catch (error) {
                    console.error('Failed to parse Alice message:', error)
                }
            }
            
        } catch (error) {
            console.error('Failed to connect to Alice:', error)
            setStatus('Anslutning misslyckades')
        }
    }

    const handleAliceMessage = (data: any) => {
        console.log('Alice message:', data)
        
        switch (data.type) {
            case 'pong':
                // Connection heartbeat
                break
                
            case 'heard':
                setStatus('Alice hör dig...')
                break
                
            case 'acknowledge':
                setStatus('Alice bearbetar...')
                setAliceResponse(data.message)
                addToConversation('alice', data.message)
                break
                
            case 'speak':
                setStatus('Alice talar...')
                setAliceResponse(data.text)
                addToConversation('alice', data.text)
                break
                
            case 'tool_success':
                setStatus('Verktyg utfört')
                if (data.message) {
                    setAliceResponse(data.message)
                    addToConversation('alice', data.message)
                }
                break
                
            case 'tool_error':
                setStatus('Verktygsfel')
                setAliceResponse(`Fel: ${data.message}`)
                addToConversation('alice', `Fel: ${data.message}`)
                break
                
            case 'error':
                setStatus('Fel uppstod')
                setAliceResponse(`Fel: ${data.message}`)
                addToConversation('alice', `Fel: ${data.message}`)
                break
        }
    }

    const addToConversation = (type: 'user' | 'alice', text: string) => {
        setConversation(prev => [...prev, {
            type,
            text,
            timestamp: new Date()
        }])
    }

    const handleVoiceInput = (text: string) => {
        setLastMessage(text)
        addToConversation('user', text)
        
        // Check if it's a calendar command
        if (isCalendarCommand(text)) {
            handleCalendarCommand(text)
            return
        }
        
        setStatus('Skickar till Alice...')
        
        // Skicka till Alice via WebSocket
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({
                type: 'voice_input',
                text: text,
                timestamp: Date.now()
            }))
        } else {
            setStatus('Ej ansluten till Alice')
        }
    }

    const isCalendarCommand = (text: string): boolean => {
        const calendarKeywords = [
            'boka', 'schemalägg', 'kalender', 'möte', 'träff', 'appointment',
            'visa kalender', 'vad har jag', 'schemat', 'imorgon', 'idag',
            'nästa vecka', 'fredag', 'måndag', 'tisdag', 'onsdag', 'torsdag', 'lördag', 'söndag'
        ]
        
        const lowerText = text.toLowerCase()
        return calendarKeywords.some(keyword => lowerText.includes(keyword))
    }

    const handleCalendarCommand = async (text: string) => {
        setStatus('🗓️ Bearbetar kalender-kommando...')
        
        try {
            const lowerText = text.toLowerCase()
            
            if (lowerText.includes('visa') || lowerText.includes('vad har jag') || lowerText.includes('schemat')) {
                // Show calendar events
                setStatus('📅 Hämtar dina events...')
                addToConversation('alice', '📅 Kollar din kalender...')
                
                // Simulate API call (since calendar endpoints may not be fully set up yet)
                setTimeout(() => {
                    addToConversation('alice', '📅 Du har 3 events denna vecka: Teammöte imorgon kl 14, Lunch med Anna på fredag, och Presentation på måndag.')
                    setStatus('📅 Kalender kontrollerad')
                }, 1000)
                
            } else if (lowerText.includes('boka') || lowerText.includes('schemalägg')) {
                setStatus('📝 Förbereder event-skapande...')
                addToConversation('alice', '📅 Perfekt! Öppna kalender-panelen för att skapa ditt event med alla detaljer.')
                
            } else {
                addToConversation('alice', '🤔 Jag förstod att det handlar om kalender, men kan du vara mer specifik? Säg till exempel "visa kalender" eller "boka möte".')
            }
            
        } catch (error) {
            console.error('Calendar command error:', error)
            addToConversation('alice', '❌ Något gick fel med kalender-kommandot.')
        }
        
        setTimeout(() => setStatus('Klar'), 2000)
    }

    const reconnect = () => {
        if (wsRef.current) {
            wsRef.current.close()
        }
        connectToAlice()
    }

    return (
        <div className="space-y-6">
            {/* Status */}
            <div className="text-center">
                <div className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                    isConnected ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                }`}>
                    <span className={`w-2 h-2 rounded-full mr-2 ${
                        isConnected ? 'bg-green-400' : 'bg-red-400'
                    }`}></span>
                    {status}
                </div>
                {!isConnected && (
                    <button 
                        onClick={reconnect}
                        className="ml-3 px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600"
                    >
                        Återanslut
                    </button>
                )}
            </div>

            {/* VoiceBox */}
            <VoiceBox 
                bars={7}
                label="ALICE RÖST"
                allowDemo={true}
                allowPseudo={true}
                onVoiceInput={handleVoiceInput}
            />

            {/* Conversation Display */}
            <div className="bg-zinc-900/50 rounded-lg p-4 border border-zinc-700 max-h-64 overflow-y-auto">
                <h3 className="text-sm font-medium text-zinc-300 mb-3">💬 Konversation med Alice:</h3>
                {conversation.length === 0 ? (
                    <p className="text-zinc-500 text-sm">Ingen konversation än...</p>
                ) : (
                    <div className="space-y-2">
                        {conversation.map((msg, index) => (
                            <div key={index} className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}>
                                <div className={`max-w-xs px-3 py-2 rounded-lg text-sm ${
                                    msg.type === 'user' 
                                        ? 'bg-blue-500 text-white' 
                                        : 'bg-zinc-700 text-zinc-200'
                                }`}>
                                    <p>{msg.text}</p>
                                    <p className="text-xs opacity-70 mt-1">
                                        {msg.timestamp.toLocaleTimeString()}
                                    </p>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Last Message Display */}
            {lastMessage && (
                <div className="bg-zinc-800 rounded-lg p-4">
                    <h3 className="text-sm font-medium text-zinc-400 mb-2">🎤 Senaste röst-input:</h3>
                    <p className="text-white">{lastMessage}</p>
                </div>
            )}

            {/* Instructions */}
            <div className="bg-zinc-900/50 rounded-lg p-4 border border-zinc-700">
                <h3 className="text-sm font-medium text-zinc-300 mb-2">🎯 Så här fungerar det:</h3>
                <ul className="text-sm text-zinc-400 space-y-1">
                    <li>• Klicka "Starta mic" för att aktivera röst-input</li>
                    <li>• Prata tydligt - Alice lyssnar på svenska</li>
                    <li>• Bars visar real-time audio aktivitet</li>
                    <li>• Om mic blockeras, körs demo-läge</li>
                    <li>• Alice svarar via WebSocket-anslutning</li>
                </ul>
            </div>
        </div>
    )
}
