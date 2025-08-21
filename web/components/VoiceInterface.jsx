'use client'

import React, { useEffect, useState } from 'react'
import VoiceBox from './VoiceBox'

/**
 * Alice Voice Interface - Kombinerar VoiceBox med Alice's röst-system
 */
export default function VoiceInterface() {
    const [isConnected, setIsConnected] = useState(false)
    const [isListening, setIsListening] = useState(false)
    const [lastMessage, setLastMessage] = useState('')
    const [status, setStatus] = useState('Anslutning...')

    useEffect(() => {
        // Här kan vi lägga till WebSocket-anslutning till Alice backend
        // För nu visar vi bara VoiceBox
        setIsConnected(true)
        setStatus('Redo')
    }, [])

    const handleVoiceInput = (text) => {
        setLastMessage(text)
        // Här kan vi skicka text till Alice backend
        console.log('Röst-input:', text)
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
            </div>

            {/* VoiceBox */}
            <VoiceBox 
                bars={7}
                label="ALICE RÖST"
                allowDemo={true}
                allowPseudo={true}
            />

            {/* Last Message Display */}
            {lastMessage && (
                <div className="bg-zinc-800 rounded-lg p-4">
                    <h3 className="text-sm font-medium text-zinc-400 mb-2">Senaste röst-input:</h3>
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
                </ul>
            </div>
        </div>
    )
}
