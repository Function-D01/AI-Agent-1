# ======================================================
# 💼 AI SALES DEVELOPMENT REP (SDR)
# 🏦 "Razorpay SDR Agent" - Auto-Lead Capture Agent
# 🚀 Features: FAQ Retrieval, Lead Qualification, JSON Database
# ======================================================

import logging
import json
import os
import asyncio
from datetime import datetime
from typing import Annotated, Optional
from dataclasses import dataclass, asdict

print("\n" + "💼" * 50)
print("🚀 AI SDR AGENT - RAZORPAY EDITION")
print("🏦 SELLING: Razorpay Payment Solutions")
print("💡 agent.py LOADED SUCCESSFULLY!")
print("💼" * 50 + "\n")

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
    function_tool,
    RunContext,
)

# 🔌 PLUGINS
from livekit.plugins import murf, silero, google, deepgram, noise_cancellation
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("agent")
load_dotenv(".env.local")

# ======================================================
# 📂 1. KNOWLEDGE BASE (RAZORPAY FAQ)
# ======================================================

FAQ_FILE = "razorpay_faq.json"
LEADS_FILE = "leads_db.json"

# Razorpay FAQ content
DEFAULT_FAQ = [
    {
        "question": "What does Razorpay do?",
        "answer": "Razorpay is a full-stack Indian payments platform that lets businesses accept and process online payments via UPI, cards, netbanking and wallets."
    },
    {
        "question": "Who is Razorpay for?",
        "answer": "Razorpay is built for Indian startups, SMBs, D2C brands, SaaS companies and enterprises that want to accept online payments or automate payouts."
    },
    {
        "question": "Do you have a free tier?",
        "answer": "Yes. Razorpay has no setup or maintenance fees on the standard plan. You only pay a per-transaction charge."
    },
    {
        "question": "What are your charges?",
        "answer": "Standard pricing is ~2% per successful domestic card/netbanking/wallet transaction, 0% for UPI/RuPay debit cards, and higher fees for international cards. Taxes apply."
    },
    {
        "question": "How do I get started?",
        "answer": "Sign up on the Razorpay website, complete KYC, and integrate your payment methods. You can go live in minutes."
    }
]

def load_knowledge_base():
    """Load Razorpay FAQ or generate if missing"""
    try:
        path = os.path.join(os.path.dirname(__file__), FAQ_FILE)
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_FAQ, f, indent=4)
        with open(path, "r", encoding="utf-8") as f:
            return json.dumps(json.load(f))
    except Exception as e:
        print(f"⚠️ FAQ Load Error: {e}")
        return ""

RAZORPAY_FAQ_TEXT = load_knowledge_base()

# ======================================================
# 💾 2. LEAD DATA STRUCTURE
# ======================================================

@dataclass
class LeadProfile:
    name: str | None = None
    company: str | None = None
    email: str | None = None
    role: str | None = None
    use_case: str | None = None
    team_size: str | None = None
    timeline: str | None = None
   
    def is_qualified(self):
        return all([self.name, self.email, self.use_case])

@dataclass
class Userdata:
    lead_profile: LeadProfile

# ======================================================
# 🛠️ 3. SDR TOOLS
# ======================================================

@function_tool
async def update_lead_profile(
    ctx: RunContext[Userdata],
    name: Annotated[Optional[str], Field(description="Customer name")] = None,
    company: Annotated[Optional[str], Field(description="Customer company name")] = None,
    email: Annotated[Optional[str], Field(description="Customer email")] = None,
    role: Annotated[Optional[str], Field(description="Job title")] = None,
    use_case: Annotated[Optional[str], Field(description="Business use case")] = None,
    team_size: Annotated[Optional[str], Field(description="Team size")] = None,
    timeline: Annotated[Optional[str], Field(description="Launch timeline")] = None,
) -> str:
    """
    Saves partial lead data as the user shares it.
    """
    profile = ctx.userdata.lead_profile
   
    if name: profile.name = name
    if company: profile.company = company
    if email: profile.email = email
    if role: profile.role = role
    if use_case: profile.use_case = use_case
    if team_size: profile.team_size = team_size
    if timeline: profile.timeline = timeline
   
    print(f"📝 UPDATING LEAD: {profile}")
    return "Lead profile updated. Continue the conversation."

@function_tool
async def submit_lead_and_end(ctx: RunContext[Userdata]) -> str:
    """
    Finalizes and saves lead, then instructs agent to give verbal summary.
    """
    profile = ctx.userdata.lead_profile
    db_path = os.path.join(os.path.dirname(__file__), LEADS_FILE)

    entry = asdict(profile)
    entry["timestamp"] = datetime.now().isoformat()

    existing = []
    if os.path.exists(db_path):
        try:
            with open(db_path, "r") as f:
                existing = json.load(f)
        except:
            pass

    existing.append(entry)

    with open(db_path, "w") as f:
        json.dump(existing, f, indent=4)

    print(f"✅ LEAD SAVED TO {LEADS_FILE}")

    return f"Lead saved. Please summarize the call: Thank {profile.name}, confirm their use case ({profile.use_case}), and mention you will email them at {profile.email}. Then say goodbye."

# ======================================================
# 🧠 4. RAZORPAY SDR AGENT
# ======================================================

class SDRAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions=f"""
            You are "Riya", a friendly and professional Sales Development Representative (SDR) for Razorpay.

            🏦 COMPANY:
            Razorpay is India’s leading full-stack payments platform offering payment gateway, payouts, subscriptions, and UPI/card processing.

            📘 KNOWLEDGE BASE (STRICTLY USE THESE ANSWERS):
            {RAZORPAY_FAQ_TEXT}

            🎯 YOUR GOALS:
            1. Greet warmly and understand the user's business.
            2. Answer product/pricing questions ONLY using the FAQ above.
               - If something is NOT in the FAQ, say:
                 "I can check this with our solutions team and email you the details."
            3. Qualify the lead naturally. Collect:
               - Name
               - Company
               - Role
               - Email
               - Use Case (What payments problem they want to solve)
               - Team Size
               - Timeline (Now / Soon / Later)
            4. After every piece of information, call update_lead_profile.
            5. When the user is done or says "thanks", call submit_lead_and_end.

            ⚙️ BEHAVIOR:
            - Be conversational, warm, and helpful.
            - Do NOT interrogate. Follow this pattern:
              • Answer → Ask one short follow-up → Wait.
            - Stay in Razorpay context always.
            - Never hallucinate pricing or features outside the FAQ.

            🛑 RULE:
            If unsure, politely say:
            "I'm not fully sure about that, but I can confirm with our team and get back to you."
            """,
            tools=[update_lead_profile, submit_lead_and_end],
        )

# ======================================================
# 🎬 ENTRYPOINT
# ======================================================

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {"room": ctx.room.name}

    print("\n" + "💼" * 25)
    print("🚀 STARTING RAZORPAY SDR SESSION")
   
    userdata = Userdata(lead_profile=LeadProfile())

    session = AgentSession(
        stt=deepgram.STT(model="nova-3"),
        llm=google.LLM(model="gemini-2.5-flash"),
        tts=murf.TTS(
            voice="en-US-natalie",
            style="Promo",
            text_pacing=True,
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        userdata=userdata,
    )
   
    await session.start(
        agent=SDRAgent(),
        room=ctx.room,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC()
        ),
    )

    await ctx.connect()

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
