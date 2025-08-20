"use client";

import VoiceInterface from '../../components/VoiceInterface';

export default function VoicePage() {
    return (
        <div className="min-h-screen bg-black p-8">
            <div className="max-w-4xl mx-auto">
                <h1 className="text-3xl font-bold text-white mb-8 text-center">
                    Alice Voice Interface Test
                </h1>
                <VoiceInterface />
            </div>
        </div>
    );
}