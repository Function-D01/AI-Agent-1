import { useState } from "react";
import { Button } from "@/components/livekit/button";
import { Input } from "@/components/livekit/input";
import { Mic, Theater } from "lucide-react";

export default function WelcomeView({ startButtonText = "Start Improv Battle", onStartCall }: any) {
  const [name, setName] = useState("");

  const handleStart = async () => {
    if (!name.trim()) return;
    try {
      const res = await fetch("/api/improv/init", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      const { token, serverUrl } = await res.json();
      onStartCall(token, serverUrl);
    } catch (error) {
      console.error("Error fetching token:", error);
    }
  };

  return (
    <div className="bg-gradient-to-b from-black via-gray-900 to-gray-950 text-gray-200 min-h-screen overflow-y-auto py-16 px-4">
      <div className="flex flex-col items-center mx-auto max-w-3xl">

        {/* Header */}
        <header className="flex items-center space-x-2 mb-10">
       
          <span className="text-2xl font-bold text-gray-100">Improv Battle</span>
        </header>

        {/* Hero */}
        <section className="flex flex-col items-center text-center w-full max-w-xl">
          
          <div className="mb-8 text-pink-400">
            <Mic size={70} className="animate-pulse" />
          </div>

          <h1 className="text-5xl sm:text-6xl font-extrabold text-white mb-4 tracking-tight">
            Step Into the Spotlight
          </h1>

          <p className="text-lg sm:text-xl text-gray-300 max-w-lg font-medium mb-12">
            Your host is waiting.  
            Each round brings a new scenario.  
            Improv your way through the madness!
          </p>

          {/* Name input */}
          <div className="w-full max-w-sm mb-6">
            <input
              type="text"
              placeholder="Enter your name"
              value={name}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setName(e.target.value)}
              className="w-full px-4 py-3 bg-gray-800/50 border border-gray-700/70 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-pink-500"
            />
          </div>

          {/* Start Button */}
          <Button
            variant="primary"
            size="lg"
            onClick={handleStart}
            disabled={!name.trim()}
            className="w-full sm:w-80 font-bold text-xl py-4 bg-pink-500 hover:bg-pink-400 text-black shadow-2xl shadow-pink-500/40 hover:shadow-pink-400/70 transition-all hover:-translate-y-1 active:translate-y-0 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {startButtonText}
          </Button>

          <div className="mt-10 mb-12 text-gray-500 text-xs sm:text-sm">
            <p>Murf Falcon TTS • Gemini • Deepgram • LiveKit Agents</p>
          </div>

        </section>

        {/* Footer */}
        <footer className="w-full py-4 text-center text-gray-600 text-xs max-w-xl px-4">
          <p>This is a voice-first improv experience. Speak clearly when the host prompts you.</p>
        </footer>
      </div>
    </div>
  );
}
