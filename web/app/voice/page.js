"use client";

import VoiceInterface from '../../components/VoiceInterface';

export default function VoicePage() {
    return (
        <div className="min-h-screen bg-black p-8">
            <div className="max-w-4xl mx-auto">
                <h1 className="text-3xl font-bold text-white mb-8 text-center">
                    🎤 Alice Röst Interface
                </h1>
                <p className="text-center text-zinc-400 mb-8">
                    Testa Alice's avancerade röst-system med real-time audio visualisering
                </p>
                
                <VoiceInterface />
            </div>
        </div>
    );
}