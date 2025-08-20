"use client";

import React, { useState, useEffect, useRef } from 'react';
import { Mic, MicOff, Volume2, VolumeX, Activity } from 'lucide-react';

const VoiceInterface = () => {
    const [voiceClient, setVoiceClient] = useState(null);
    const [isConnected, setIsConnected] = useState(false);
    const [isListening, setIsListening] = useState(false);
    const [isSpeaking, setIsSpeaking] = useState(false);
    const [lastHeard, setLastHeard] = useState('');
    const [aliceResponse, setAliceResponse] = useState('');
    const [status, setStatus] = useState('Disconnected');
    const [logs, setLogs] = useState([]);
    const voiceClientRef = useRef(null);

    useEffect(() => {
        // Dynamically import the voice client (browser-only)
        const initVoiceClient = async () => {
            if (typeof window === 'undefined') return;
            
            try {
                // Import the voice client
                const script = document.createElement('script');
                script.src = '/lib/voice-client.js';
                script.onload = () => {
                    if (window.AliceVoiceClient) {
                        const client = new window.AliceVoiceClient();
                        voiceClientRef.current = client;
                        setVoiceClient(client);
                        setupEventHandlers(client);
                    }
                };
                document.head.appendChild(script);
            } catch (error) {
                console.error('Failed to load voice client:', error);
                addLog('Error', 'Failed to load voice client');
            }
        };

        initVoiceClient();

        return () => {
            if (voiceClientRef.current) {
                voiceClientRef.current.disconnect();
            }
        };
    }, []);

    const setupEventHandlers = (client) => {
        client.on('connected', () => {
            setIsConnected(true);
            setStatus('Connected');
            addLog('System', 'Connected to Alice');
        });

        client.on('disconnected', () => {
            setIsConnected(false);
            setStatus('Disconnected');
            addLog('System', 'Disconnected from Alice');
        });

        client.on('listening_started', () => {
            setIsListening(true);
            setStatus('Listening...');
            addLog('System', 'Started listening');
        });

        client.on('listening_stopped', () => {
            setIsListening(false);
            setStatus('Connected');
            addLog('System', 'Stopped listening');
        });

        client.on('voice_input', (data) => {
            if (data.final) {
                setLastHeard(data.text);
                addLog('You', data.text);
            }
        });

        client.on('alice_heard', (text) => {
            addLog('Alice heard', text);
        });

        client.on('alice_acknowledge', (message) => {
            addLog('Alice', `🎯 ${message}`);
        });

        client.on('alice_response', (data) => {
            if (data.final) {
                setAliceResponse(data.text);
                addLog('Alice', data.text);
            }
        });

        client.on('tool_executed', (data) => {
            addLog('Tool', `✅ ${data.tool}: ${data.message}`);
        });

        client.on('tool_error', (message) => {
            addLog('Error', `❌ ${message}`);
        });

        client.on('speaking_started', () => {
            setIsSpeaking(true);
            setStatus('Alice speaking...');
        });

        client.on('speaking_ended', () => {
            setIsSpeaking(false);
            setStatus('Connected');
        });

        client.on('error', (message) => {
            addLog('Error', message);
        });
    };

    const addLog = (type, message) => {
        const timestamp = new Date().toLocaleTimeString();
        setLogs(prev => [...prev.slice(-9), { type, message, timestamp }]);
    };

    const handleConnect = async () => {
        if (!voiceClient) {
            addLog('Error', 'Voice client not loaded');
            return;
        }

        if (!voiceClient.isSupported()) {
            addLog('Error', 'Speech recognition not supported in this browser');
            return;
        }

        try {
            await voiceClient.connect();
        } catch (error) {
            addLog('Error', 'Failed to connect to Alice');
        }
    };

    const handleDisconnect = () => {
        if (voiceClient) {
            voiceClient.disconnect();
        }
    };

    const handleToggleListening = () => {
        if (!voiceClient || !isConnected) return;

        if (isListening) {
            voiceClient.stopListening();
        } else {
            voiceClient.startListening();
        }
    };

    const handleStopSpeaking = () => {
        if (voiceClient) {
            voiceClient.stopSpeaking();
        }
    };

    const getStatusColor = () => {
        if (!isConnected) return 'text-red-400';
        if (isListening) return 'text-green-400';
        if (isSpeaking) return 'text-blue-400';
        return 'text-gray-400';
    };

    return (
        <div className="voice-interface p-6 bg-gray-900 rounded-lg border border-gray-700 max-w-2xl mx-auto">
            <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-white flex items-center gap-2">
                    <Activity className="w-5 h-5" />
                    Alice Voice Interface
                </h2>
                <div className={`text-sm font-medium ${getStatusColor()}`}>
                    {status}
                </div>
            </div>

            <div className="flex gap-3 mb-6">
                {!isConnected ? (
                    <button
                        onClick={handleConnect}
                        className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                    >
                        Connect to Alice
                    </button>
                ) : (
                    <button
                        onClick={handleDisconnect}
                        className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
                    >
                        Disconnect
                    </button>
                )}

                {isConnected && (
                    <>
                        <button
                            onClick={handleToggleListening}
                            className={`px-4 py-2 rounded-lg transition-colors flex items-center gap-2 ${
                                isListening 
                                    ? 'bg-red-600 hover:bg-red-700 text-white' 
                                    : 'bg-green-600 hover:bg-green-700 text-white'
                            }`}
                        >
                            {isListening ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
                            {isListening ? 'Stop Listening' : 'Start Listening'}
                        </button>

                        {isSpeaking && (
                            <button
                                onClick={handleStopSpeaking}
                                className="px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-lg transition-colors flex items-center gap-2"
                            >
                                <VolumeX className="w-4 h-4" />
                                Stop Speaking
                            </button>
                        )}
                    </>
                )}
            </div>

            <div className="space-y-3 mb-6">
                {lastHeard && (
                    <div className="p-3 bg-gray-800 rounded-lg border-l-4 border-blue-500">
                        <div className="text-sm text-gray-400 mb-1">You said:</div>
                        <div className="text-white">{lastHeard}</div>
                    </div>
                )}

                {aliceResponse && (
                    <div className="p-3 bg-gray-800 rounded-lg border-l-4 border-green-500">
                        <div className="text-sm text-gray-400 mb-1">Alice responded:</div>
                        <div className="text-white">{aliceResponse}</div>
                    </div>
                )}
            </div>

            <div className="conversation-log">
                <h3 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
                    <Volume2 className="w-4 h-4" />
                    Conversation Log
                </h3>
                <div className="space-y-2 max-h-64 overflow-y-auto">
                    {logs.length === 0 ? (
                        <div className="text-gray-500 italic">No conversation yet...</div>
                    ) : (
                        logs.map((log, index) => (
                            <div key={index} className="flex gap-3 text-sm">
                                <span className="text-gray-500 min-w-[60px]">{log.timestamp}</span>
                                <span className={`min-w-[80px] font-medium ${
                                    log.type === 'You' ? 'text-blue-400' :
                                    log.type === 'Alice' ? 'text-green-400' :
                                    log.type === 'Tool' ? 'text-purple-400' :
                                    log.type === 'Error' ? 'text-red-400' :
                                    'text-gray-400'
                                }`}>
                                    {log.type}:
                                </span>
                                <span className="text-gray-300 flex-1">{log.message}</span>
                            </div>
                        ))
                    )}
                </div>
            </div>

            <div className="mt-6 p-4 bg-gray-800 rounded-lg border border-gray-600">
                <h4 className="text-sm font-semibold text-white mb-2">How to use:</h4>
                <ul className="text-sm text-gray-400 space-y-1">
                    <li>• Click &quot;Connect to Alice&quot; to establish voice connection</li>
                    <li>• Click &quot;Start Listening&quot; and speak in Swedish</li>
                    <li>• Try commands like &quot;spela musik&quot; or ask questions like &quot;vad tycker du om AC/DC?&quot;</li>
                    <li>• Alice will respond instantly with acknowledgments and then detailed answers</li>
                </ul>
            </div>
        </div>
    );
};

export default VoiceInterface;