# ======================================================
# 🧠 DAY 4: TEACH-THE-TUTOR (COMPUTER EDITION)
# 🚀 Features: Computer Basics, Hardware vs Software, OS, Programming Basics
# ======================================================

import logging
import json
import os
import asyncio
from typing import Annotated, Literal, Optional
from dataclasses import dataclass

print("\n" + "💻" * 50)
print("🚀 COMPUTER TUTOR - DAY 4 ")
print("💡 agent.py LOADED SUCCESSFULLY!")
print("💻" * 50 + "\n")

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
# 📚 KNOWLEDGE BASE (COMPUTER SCIENCE / IT DATA)
# ======================================================

# 🆕 Renamed file so it generates fresh COMPUTER edition data for you
CONTENT_FILE = "computer_content.json"

# 💻 COMPUTER TUTOR QUESTIONS
DEFAULT_CONTENT = [
    {
        "id": "computer_basics",
        "title": "What is a Computer?",
        "summary": (
            "A computer is an electronic device that accepts data as input, "
            "processes it using instructions (programs), and produces output. "
            "It can store data and run different types of software to perform tasks."
        ),
        "sample_question": "How would you define a computer in simple words, and what are its main functions?"
    },
    {
        "id": "hardware_software",
        "title": "Hardware vs Software",
        "summary": (
            "Hardware refers to the physical components of a computer such as the CPU, RAM, keyboard, and monitor. "
            "Software refers to the programs and operating systems that run on the hardware and tell it what to do."
        ),
        "sample_question": "What is the difference between hardware and software? Give one example of each."
    },
    {
        "id": "operating_system",
        "title": "Operating System (OS)",
        "summary": (
            "An Operating System is system software that manages computer hardware and software resources. "
            "It provides a user interface, manages files, runs applications, and controls input/output devices. "
            "Examples include Windows, macOS, Linux, and Android."
        ),
        "sample_question": "What is an operating system and why is it important for a computer?"
    },
    {
        "id": "programming_basics",
        "title": "Programming Basics",
        "summary": (
            "Programming is the process of writing instructions (code) that a computer can execute. "
            "These instructions are written in programming languages like Python, Java, or C++. "
            "Key ideas include variables, data types, conditions, loops, and functions."
        ),
        "sample_question": "What is programming, and can you name any two programming languages?"
    }
]


def load_content():
    """
    📖 Checks if the computer-tutor JSON exists.
    If NO: Generates it from DEFAULT_CONTENT.
    If YES: Loads it.
    """
    try:
        path = os.path.join(os.path.dirname(__file__), CONTENT_FILE)

        # Check if file exists
        if not os.path.exists(path):
            print(f"⚠️ {CONTENT_FILE} not found. Generating computer tutor data...")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_CONTENT, f, indent=4)
            print("✅ Computer content file created successfully.")

        # Read the file
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data

    except Exception as e:
        print(f"⚠️ Error managing content file: {e}")
        return []


# Load data immediately on startup
COURSE_CONTENT = load_content()

# ======================================================
# 🧠 STATE MANAGEMENT
# ======================================================


@dataclass
class TutorState:
    """🧠 Tracks the current learning context for computer tutoring."""
    current_topic_id: str | None = None
    current_topic_data: dict | None = None
    mode: Literal["learn", "quiz", "teach_back"] = "learn"

    def set_topic(self, topic_id: str):
        # Find topic in loaded content
        topic = next((item for item in COURSE_CONTENT if item["id"] == topic_id), None)
        if topic:
            self.current_topic_id = topic_id
            self.current_topic_data = topic
            return True
        return False


@dataclass
class Userdata:
    tutor_state: TutorState
    agent_session: Optional[AgentSession] = None

# ======================================================
# 🛠️ TUTOR TOOLS
# ======================================================


@function_tool
async def select_topic(
    ctx: RunContext[Userdata],
    topic_id: Annotated[str, Field(description="The ID of the topic to study (e.g., 'computer_basics', 'hardware_software', 'operating_system', 'programming_basics')")]
) -> str:
    """📚 Selects a computer topic to study from the available list."""
    state = ctx.userdata.tutor_state
    success = state.set_topic(topic_id.lower())

    if success:
        return f"Topic set to {state.current_topic_data['title']}. Ask the user if they want to 'Learn', be 'Quizzed', or 'Teach it back'."
    else:
        available = ", ".join([t["id"] for t in COURSE_CONTENT])
        return f"Topic not found. Available topics are: {available}"


@function_tool
async def set_learning_mode(
    ctx: RunContext[Userdata],
    mode: Annotated[str, Field(description="The mode to switch to: 'learn', 'quiz', or 'teach_back'")]
) -> str:
    """🔄 Switches the interaction mode and updates the agent's voice/persona."""

    # 1. Update State
    state = ctx.userdata.tutor_state
    state.mode = mode.lower()

    # 2. Switch Voice based on Mode
    agent_session = ctx.userdata.agent_session

    if agent_session and state.current_topic_data:
        if state.mode == "learn":
            # 👨‍🏫 MATTHEW: The Lecturer
            agent_session.tts.update_options(voice="en-US-matthew", style="Promo")
            instruction = f"Mode: LEARN. Explain this computer topic in simple steps: {state.current_topic_data['summary']}"

        elif state.mode == "quiz":
            # 👩‍🏫 ALICIA: The Examiner
            agent_session.tts.update_options(voice="en-US-alicia", style="Conversational")
            instruction = (
                "Mode: QUIZ. Ask this question to check their understanding: "
                f"{state.current_topic_data['sample_question']}"
            )

        elif state.mode == "teach_back":
            # 👨‍🎓 KEN: The Student/Coach
            agent_session.tts.update_options(voice="en-US-ken", style="Promo")
            instruction = (
                "Mode: TEACH_BACK. Ask the user to explain this computer topic to you as if YOU are a beginner. "
                "Encourage them to break it into small, clear points."
            )
        else:
            return "Invalid mode."
    else:
        instruction = "Voice switch failed (Session not found or topic not selected)."

    print(f"🔄 SWITCHING MODE -> {state.mode.upper()}")
    return f"Switched to {state.mode} mode. {instruction}"


@function_tool
async def evaluate_teaching(
    ctx: RunContext[Userdata],
    user_explanation: Annotated[str, Field(description="The explanation given by the user during teach-back")]
) -> str:
    """
    📝 Call this when the user has finished explaining a computer concept in 'teach_back' mode.
    The LLM should:
    - Score their explanation out of 10 for accuracy and clarity.
    - Gently correct mistakes.
    - Add 1–2 suggestions to improve their explanation.
    """
    print(f"📝 EVALUATING EXPLANATION: {user_explanation}")
    return (
        "Analyze the user's explanation of the computer topic. "
        "Give them a score out of 10 on accuracy and clarity, correct any mistakes, "
        "and suggest how they can explain it even better next time."
    )

# ======================================================
# 🧠 AGENT DEFINITION
# ======================================================


class TutorAgent(Agent):
    def __init__(self):
        # Generate list of topics for the prompt
        topic_list = ", ".join([f"{t['id']} ({t['title']})" for t in COURSE_CONTENT])

        super().__init__(
            instructions=f"""
            You are a **Computer Tutor** designed to help users master basic computer and programming concepts.

            💻 **AVAILABLE TOPICS:** {topic_list}

            🔄 **YOU HAVE 3 MODES:**
            1. **LEARN Mode (Voice: Matthew):**
               - You explain the selected computer topic step by step using the `summary` from the knowledge base.
               - Use simple language and examples (like comparing hardware to body parts, OS to a manager, etc.).
            2. **QUIZ Mode (Voice: Alicia):**
               - You ask the user the `sample_question` and follow-up questions.
               - Encourage them to answer in their own words.
               - Give hints if they are stuck.
            3. **TEACH_BACK Mode (Voice: Ken):**
               - YOU pretend to be a beginner student.
               - Ask the user to teach the concept to you.
               - Listen to their explanation and then call `evaluate_teaching` to get feedback.

            ⚙️ **BEHAVIOR:**
            - Start by asking what topic they want to study (mention the topic IDs you see above).
            - When they pick a topic, use the `select_topic` tool.
            - When they say things like:
                - "I want to learn it" → use `set_learning_mode` with 'learn'.
                - "Quiz me" or "Ask questions" → use `set_learning_mode` with 'quiz'.
                - "Let me explain it" → use `set_learning_mode` with 'teach_back'.
            - In 'teach_back' mode:
                - Allow the user to speak for a while.
                - Once they are done explaining, call `evaluate_teaching` with their explanation.
                - Then give them feedback using the tool's response.

            🧩 **STYLE:**
            - Be friendly, motivating, and beginner-friendly.
            - Break complex words into simple explanations.
            - Use small recaps: "So in short, ...".
            """,
            tools=[select_topic, set_learning_mode, evaluate_teaching],
        )

# ======================================================
# 🎬 ENTRYPOINT
# ======================================================


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {"room": ctx.room.name}

    print("\n" + "💻" * 25)
    print("🚀 STARTING COMPUTER TUTOR SESSION")
    print(f"📚 Loaded {len(COURSE_CONTENT)} topics from Knowledge Base")

    # 1. Initialize State
    userdata = Userdata(tutor_state=TutorState())

    # 2. Setup Agent
    session = AgentSession(
        stt=deepgram.STT(model="nova-3"),
        llm=google.LLM(model="gemini-2.5-flash"),
        tts=murf.TTS(
            voice="en-US-matthew",
            style="Promo",
            text_pacing=True,
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        userdata=userdata,
    )

    # 3. Store session in userdata for tools to access
    userdata.agent_session = session

    # 4. Start
    await session.start(
        agent=TutorAgent(),
        room=ctx.room,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC()
        ),
    )

    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
