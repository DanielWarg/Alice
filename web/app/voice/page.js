"use client";

export default function VoicePage() {
    return (
        <div className="min-h-screen bg-black p-8">
            <div className="max-w-4xl mx-auto">
                <h1 className="text-3xl font-bold text-white mb-8 text-center">
                    🎤 Alice Röst Interface
                </h1>
                <p className="text-center text-zinc-400 mb-8">
                    Röstgränssnittet har flyttats till Alice Core huvudsida
                </p>
                <div className="text-center">
                    <a href="/" className="inline-block px-6 py-3 bg-cyan-500 text-black rounded-lg hover:bg-cyan-400 transition">
                        Gå till Alice Core
                    </a>
                </div>
            </div>
        </div>
    );
}