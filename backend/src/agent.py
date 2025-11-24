# ======================================================
# 🏥 APOLLO DAILY WELLNESS VOICE COMPANION
# 🚀 Daily Check-In • Mood • Energy • Goals • JSON History
# ======================================================

import logging
import json
import os
import asyncio
from datetime import datetime, timedelta
from typing import Annotated, Literal, List, Optional, Dict
from dataclasses import dataclass, field, asdict

print("\n" + "🏥" * 50)
print("🚀 APOLLO WELLNESS COMPANION")
print("💡 agent.py LOADED SUCCESSFULLY!")
print("🏥" * 50 + "\n")

from dotenv import load_dotenv
from pydantic import Field
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    RoomInputOptions,
    WorkerOptions,
    cli,
    metrics,
    MetricsCollectedEvent,
    RunContext,
    function_tool,
)

from livekit.plugins import murf, silero, google, deepgram, noise_cancellation
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("agent")
load_dotenv(".env.local")

# ======================================================
# 🧠 STATE MANAGEMENT & DATA STRUCTURES
# ======================================================

@dataclass
class CheckInState:
    """🌿 Holds data for the CURRENT daily check-in"""
    mood: str | None = None
    energy: str | None = None
    objectives: list[str] = field(default_factory=list)
    advice_given: str | None = None
    
    def is_complete(self) -> bool:
        """✅ Check if we have the core check-in data"""
        return all([
            self.mood is not None,
            self.energy is not None,
            len(self.objectives) > 0
        ])
    
    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class Userdata:
    """👤 User session data passed to the agent"""
    current_checkin: CheckInState
    history_summary: str  # String containing info about previous sessions
    session_start: datetime = field(default_factory=datetime.now)

# ======================================================
# 💾 PERSISTENCE LAYERS (JSON LOGGING)
# ======================================================
WELLNESS_LOG_FILE = "apollo_wellness_log.json"

def get_log_path():
    base_dir = os.path.dirname(__file__)
    backend_dir = os.path.abspath(os.path.join(base_dir, ".."))
    return os.path.join(backend_dir, WELLNESS_LOG_FILE)

def load_history() -> list:
    """📖 Read previous check-ins from JSON"""
    path = get_log_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding='utf-8') as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"⚠️ Could not load history: {e}")
        return []

def save_checkin_entry(entry: CheckInState) -> None:
    """💾 Append new check-in to the JSON list"""
    path = get_log_path()
    history = load_history()
    
    # Create record
    record = {
        "timestamp": datetime.now().isoformat(),
        "mood": entry.mood,
        "energy": entry.energy,
        "objectives": entry.objectives,
        "summary": entry.advice_given
    }
    
    history.append(record)
    
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding='utf-8') as f:
        json.dump(history, f, indent=4, ensure_ascii=False)
        
    print(f"\n✅ CHECK-IN SAVED TO {path}")

# ======================================================
# 🧮 ADVANCED GOAL 2 – WEEKLY REFLECTION HELPERS
# ======================================================

def _parse_timestamp(ts: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        return None

def _filter_recent_entries(history: List[Dict], days: int = 7) -> List[Dict]:
    if not history:
        return []
    now = datetime.now()
    cutoff = now - timedelta(days=days)
    recent: List[Dict] = []
    for entry in history:
        ts = entry.get("timestamp")
        dt = _parse_timestamp(ts) if ts else None
        if dt and dt >= cutoff:
            recent.append(entry)
    return recent

def _summarize_recent_history(recent: List[Dict]) -> str:
    if not recent:
        return "I couldn't find any check-ins for the selected period."

    mood_counts: Dict[str, int] = {}
    days_with_goals = 0

    for entry in recent:
        mood = (entry.get("mood") or "").strip().lower()
        if mood:
            mood_counts[mood] = mood_counts.get(mood, 0) + 1
        objectives = entry.get("objectives") or []
        if objectives:
            days_with_goals += 1

    total_days = len(recent)
    parts: List[str] = []
    parts.append(f"In the last {total_days} recorded day(s), you checked in {total_days} time(s).")

    if mood_counts:
        mood_bits = [
            f"{mood} ({count} day{'s' if count > 1 else ''})"
            for mood, count in mood_counts.items()
        ]
        parts.append("Your moods have often been: " + ", ".join(mood_bits) + ".")

    parts.append(
        f"You set at least one goal on {days_with_goals} out of {total_days} day(s)."
    )

    parts.append(
        "This isn't a judgment, just a reflection to help you notice patterns "
        "in how you're feeling and showing up for yourself."
    )
    return " ".join(parts)

# ======================================================
# 🛠️ WELLNESS AGENT TOOLS – CORE
# ======================================================

@function_tool
async def record_mood_and_energy(
    ctx: RunContext[Userdata],
    mood: Annotated[str, Field(description="The user's emotional state (e.g., happy, stressed, anxious)")],
    energy: Annotated[str, Field(description="The user's energy level (e.g., high, low, drained, energetic)")],
) -> str:
    """📝 Record how the user is feeling. Call this after the user describes their state."""
    ctx.userdata.current_checkin.mood = mood
    ctx.userdata.current_checkin.energy = energy
    
    print(f"📊 MOOD LOGGED: {mood} | ENERGY: {energy}")
    
    return f"I've noted that you are feeling {mood} with {energy} energy. I'm listening."

@function_tool
async def record_objectives(
    ctx: RunContext[Userdata],
    objectives: Annotated[list[str], Field(description="List of 1-3 specific goals the user wants to achieve today")],
) -> str:
    """🎯 Record the user's daily goals. Call this when user states what they want to do."""
    ctx.userdata.current_checkin.objectives = objectives
    print(f"🎯 OBJECTIVES LOGGED: {objectives}")
    return "I've written down your goals for the day."

@function_tool
async def complete_checkin(
    ctx: RunContext[Userdata],
    final_advice_summary: Annotated[str, Field(description="A brief 1-sentence summary of the advice given")],
) -> str:
    """💾 Finalize the session, provide a recap, and save to JSON. Call at the very end."""
    state = ctx.userdata.current_checkin
    state.advice_given = final_advice_summary
    
    if not state.is_complete():
        return "I can't finish yet. I still need to know your mood, energy, or at least one goal."

    # Save to JSON
    save_checkin_entry(state)
    
    print("\n" + "⭐" * 60)
    print("🎉 WELLNESS CHECK-IN COMPLETED!")
    print(f"💭 Mood: {state.mood}")
    print(f"🎯 Goals: {state.objectives}")
    print("⭐" * 60 + "\n")

    recap = f"""
    Here is your recap for today:
    You are feeling {state.mood} and your energy is {state.energy}.
    Your main goals are: {', '.join(state.objectives)}.
    
    Remember: {final_advice_summary}
    
    I've saved this in your wellness log. Have a wonderful day!
    """
    return recap

# ======================================================
# 🛠️ ADVANCED GOAL 2 – WEEKLY REFLECTION TOOL
# ======================================================

@function_tool
async def weekly_reflection(
    ctx: RunContext[Userdata],
    days: Annotated[int, Field(description="How many days back to look for the reflection, default 7")] = 7,
) -> str:
    """📆 Provide a simple weekly (or N-day) reflection based on JSON history."""
    history = load_history()
    recent = _filter_recent_entries(history, days=days)
    summary = _summarize_recent_history(recent)
    print("📊 WEEKLY REFLECTION GENERATED")
    return summary

# ======================================================
# 🛠️ ADVANCED GOAL 1 & 3 – MCP STUB TOOLS (TASKS & REMINDERS)
# ======================================================

# NOTE:
# These tools are written as *stubs* for MCP integration.
# You can wire them to a real MCP server (Notion, Todoist, Zapier, etc.)
# by calling the appropriate MCP client inside these functions.

@function_tool
async def create_tasks_from_objectives(
    ctx: RunContext[Userdata],
    backend: Annotated[str, Field(description="Which external system to use, e.g. 'notion', 'todoist', 'zapier'")],
    objectives: Annotated[Optional[List[str]], Field(description="Optional explicit list of goals; if omitted, use current check-in objectives")] = None,
) -> str:
    """🗂️ Advanced Goal 1: Turn today's objectives into external tasks via MCP (stub)."""
    tasks = objectives if objectives is not None else ctx.userdata.current_checkin.objectives
    tasks = [t for t in tasks if t]
    if not tasks:
        return "I don't see any objectives to turn into tasks yet. Let's set 1–3 goals first."

    # 🔗 PLACEHOLDER: here is where you'd call your MCP client.
    # For example, call a Notion / Todoist / Zapier MCP tool with these tasks.
    print(f"🔗 [MCP STUB] Would create tasks in {backend} for: {tasks}")

    joined = "; ".join(tasks)
    return (
        f"I'll treat these as tasks in your {backend} workspace: {joined}. "
        "Once your MCP server is wired up, this step can actually create or update them for you."
    )

@function_tool
async def create_followup_reminder(
    ctx: RunContext[Userdata],
    reminder_text: Annotated[str, Field(description="What the reminder is about, e.g. 'go for a walk'")],
    when: Annotated[str, Field(description="When the reminder should happen, e.g. 'today at 6 pm'")],
    backend: Annotated[str, Field(description="Which MCP tool/integration to use, e.g. 'notion', 'todoist', 'zapier'")] = "todoist",
) -> str:
    """⏰ Advanced Goal 3: Create a follow-up reminder in an external MCP-connected tool (stub)."""
    # 🔗 PLACEHOLDER for MCP reminder creation.
    print(f"🔗 [MCP STUB] Would create reminder in {backend}: '{reminder_text}' at '{when}'")
    return (
        f"Okay, I would set a reminder in your {backend} system to '{reminder_text}' at '{when}'. "
        "Once MCP is connected, this will become a real reminder instead of just a note."
    )

# ======================================================
# 🧠 AGENT DEFINITION
# ======================================================

class WellnessAgent(Agent):
    def __init__(self, history_context: str):
        super().__init__(
            instructions=f"""
            You are Apollo’s Daily Wellness Assistant. 
            Your role is to help users maintain their wellbeing through short daily check-ins focusing on mood, energy, and simple goals. 

            
            🧠 **CONTEXT FROM PREVIOUS SESSIONS:**
            {history_context}
            
            🎯 **GOALS FOR THIS SESSION:**
            1. **Check-in:** Ask how they are feeling (Mood) and their energy levels.
               - *Reference the history context if available (e.g., "Last time you were tired, how is today?").*
            2. **Intentions:** Ask for 1–3 simple objectives for the day.
            3. **Support:** Offer small, grounded, NON-MEDICAL advice.
               - Example: "Try a 5-minute walk" or "Break that big task into small steps."
            4. **Recap & Save:** Summarize their mood and goals, then call 'complete_checkin'.

            🧩 **ADVANCED BEHAVIOURS:**
            - If the user says things like "turn these into tasks", "save this to Notion",
              or "send these goals to Todoist", call `create_tasks_from_objectives`.
            - If the user asks "how has my mood been this week?" or
              "did I follow through on my goals most days?", call `weekly_reflection`.
            - If the user mentions a future self-care activity and wants a reminder,
              like "remind me at 6 pm to go for a walk", confirm the details and then
              call `create_followup_reminder`.

            🚫 **SAFETY GUARDRAILS:**
            - You are NOT a doctor or therapist.
            - Do NOT diagnose conditions or prescribe treatments.
            - If a user mentions self-harm or severe crisis, gently suggest professional help immediately.

            🛠️ **Use the tools to record data as the user speaks and to access history.**
            """,
            tools=[
                record_mood_and_energy,
                record_objectives,
                complete_checkin,
                weekly_reflection,
                create_tasks_from_objectives,
                create_followup_reminder,
            ],
        )

# ======================================================
# 🎬 ENTRYPOINT & INITIALIZATION
# ======================================================

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {"room": ctx.room.name}

    print("\n" + "🌿" * 25)
    print("🚀 STARTING WELLNESS SESSION")
    print("🏥 Apollo Wellness Assistant Active")
    
    # 1. Load History from JSON
    history = load_history()
    history_summary = "No previous history found. This is the first session."
    
    if history:
        last_entry = history[-1]
        history_summary = (
            f"Last check-in was on {last_entry.get('timestamp', 'unknown date')}. "
            f"User felt {last_entry.get('mood')} with {last_entry.get('energy')} energy. "
            f"Their goals were: {', '.join(last_entry.get('objectives', []))}."
        )
        print("📜 HISTORY LOADED:", history_summary)
    else:
        print("📜 NO HISTORY FOUND.")

    # 2. Initialize Session Data
    userdata = Userdata(
        current_checkin=CheckInState(),
        history_summary=history_summary
    )

    # 3. Setup Agent
    session = AgentSession(
        stt=deepgram.STT(model="nova-3"),
        llm=google.LLM(model="gemini-2.5-flash"),
        tts=murf.TTS(
            voice="en-US-natalie", # Using a softer, more caring voice
            style="Promo",         # Often sounds more enthusiastic/supportive
            text_pacing=True,
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        userdata=userdata,
    )
    
    # 4. Start
    await session.start(
        agent=WellnessAgent(history_context=history_summary),
        room=ctx.room,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC()
        ),
    )

    await ctx.connect()

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))