# ======================================================
# 🏦 GLOBAL BANK - FRAUD ALERT AGENT (SQLite DB variant)
# 🛡️ Fraud Detection & Resolution System
# ======================================================

import logging
import os
import sqlite3
from datetime import datetime
from typing import Annotated, Optional
from dataclasses import dataclass

print("\n" + "🛡️" * 50)
print("🚀 GLOBAL BANK - FRAUD AGENT (SQLite) INITIALIZED")
print("📚 TASKS: Verify Identity -> Check Transaction -> Update DB")
print("🛡️" * 50 + "\n")

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

from livekit.plugins import murf, silero, google, deepgram, noise_cancellation
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("agent")
load_dotenv(".env.local")

# ======================================================
# 💾 1. DATABASE SETUP (SQLite)
# ======================================================

DB_FILE = "fraud_db.sqlite"


@dataclass
class FraudCase:
    userName: str
    securityIdentifier: str
    cardEnding: str
    transactionName: str
    transactionAmount: str
    transactionTime: str
    transactionSource: str
    case_status: str = "pending_review"
    notes: str = ""


def get_db_path() -> str:
    """Return absolute path to the SQLite DB file."""
    return os.path.join(os.path.dirname(__file__), DB_FILE)


def get_conn() -> sqlite3.Connection:
    """Create and return a SQLite connection with Row factory."""
    path = get_db_path()
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def seed_database() -> None:
    """Create SQLite DB and insert sample rows if empty."""
    conn = get_conn()
    cur = conn.cursor()

    # Create table if it does not exist
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS fraud_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            userName TEXT NOT NULL,
            securityIdentifier TEXT,
            cardEnding TEXT,
            transactionName TEXT,
            transactionAmount TEXT,
            transactionTime TEXT,
            transactionSource TEXT,
            case_status TEXT DEFAULT 'pending_review',
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
        """
    )

    # Seed with sample data only if empty
    cur.execute("SELECT COUNT(1) FROM fraud_cases")
    if cur.fetchone()[0] == 0:
        sample_data = [
            (
                "John",
                "12345",
                "4242",
                "ABC Industry",
                "$450.00",
                "2:30 AM EST",
                "alibaba.com",
                "pending_review",
                "Automated flag: High value transaction.",
            ),
            (
                "Divya",
                "99887",
                "1199",
                "Unknown Crypto Exchange",
                "$2,100.00",
                "4:15 AM PST",
                "online_transfer",
                "pending_review",
                "Automated flag: Unusual location.",
            ),
        ]
        cur.executemany(
            """
            INSERT INTO fraud_cases (
                userName,
                securityIdentifier,
                cardEnding,
                transactionName,
                transactionAmount,
                transactionTime,
                transactionSource,
                case_status,
                notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            sample_data,
        )
        conn.commit()
        print(f"✅ SQLite DB seeded at {DB_FILE}")

    conn.close()


# Initialize DB on module load
seed_database()

# ======================================================
# 🧠 2. STATE MANAGEMENT
# ======================================================


@dataclass
class Userdata:
    active_case: Optional[FraudCase] = None


# ======================================================
# 🛠️ 3. FRAUD AGENT TOOLS (SQLite-backed)
# ======================================================


@function_tool
async def lookup_customer(
    ctx: RunContext[Userdata],
    name: Annotated[str, Field(description="The name the user provides")],
) -> str:
    """
    Lookup a customer in the SQLite DB by first name.
    Sets ctx.userdata.active_case if a record is found.
    """
    print(f"🔎 LOOKING UP CUSTOMER AT GLOBAL BANK: {name}")
    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM fraud_cases WHERE LOWER(userName) = LOWER(?) LIMIT 1",
            (name,),
        )
        row = cur.fetchone()
        conn.close()

        if not row:
            return (
                "I’m sorry, I couldn’t find a matching record at Global Bank for that "
                "name. Please repeat your first name clearly."
            )

        record = dict(row)
        ctx.userdata.active_case = FraudCase(
            userName=record["userName"],
            securityIdentifier=record["securityIdentifier"],
            cardEnding=record["cardEnding"],
            transactionName=record["transactionName"],
            transactionAmount=record["transactionAmount"],
            transactionTime=record["transactionTime"],
            transactionSource=record["transactionSource"],
            case_status=record["case_status"],
            notes=record["notes"],
        )

        return (
            "Thanks. I’ve located your Global Bank account.\n"
            f"Customer Name: {record['userName']}\n"
            f"Security Identifier (expected): {record['securityIdentifier']}\n"
            f"Recent flagged transaction: {record['transactionAmount']} at "
            f"{record['transactionName']} ({record['transactionSource']}).\n"
            "Now, please ask the customer for their Security Identifier to verify their identity."
        )

    except Exception as e:
        return f"Database error while accessing Global Bank records: {str(e)}"


@function_tool
async def resolve_fraud_case(
    ctx: RunContext[Userdata],
    status: Annotated[str, Field(description="confirmed_safe or confirmed_fraud")],
    notes: Annotated[str, Field(description="Notes on the user's confirmation")],
) -> str:
    """
    Update the fraud case in the DB as confirmed_safe or confirmed_fraud.
    Uses ctx.userdata.active_case.
    """

    if not ctx.userdata.active_case:
        return "Error: No active case selected for this Global Bank customer."

    case = ctx.userdata.active_case
    case.case_status = status
    case.notes = notes

    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE fraud_cases
            SET case_status = ?, notes = ?, updated_at = datetime('now')
            WHERE userName = ?
            """,
            (case.case_status, case.notes, case.userName),
        )
        conn.commit()

        cur.execute("SELECT * FROM fraud_cases WHERE userName = ?", (case.userName,))
        updated_row = dict(cur.fetchone())
        conn.close()

        print(f"✅ GLOBAL BANK CASE UPDATED: {case.userName} -> {status}")

        if status == "confirmed_fraud":
            return (
                f"Thank you. We’ve confirmed this as fraud on your Global Bank account. "
                f"The card ending in {case.cardEnding} has been blocked immediately, and "
                f"a replacement card will be issued to your registered address.\n"
                f"Case notes: {case.notes}\n"
                f"Updated At: {updated_row['updated_at']}"
            )
        else:
            return (
                "Thank you for confirming. We’ve marked this transaction as safe on your "
                "Global Bank account and lifted any temporary restrictions.\n"
                f"Case notes: {case.notes}\n"
                f"Updated At: {updated_row['updated_at']}"
            )

    except Exception as e:
        return f"Error saving the Global Bank fraud case to the database: {e}"


# ======================================================
# 🤖 4. AGENT DEFINITION
# ======================================================


class FraudAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions="""
            You are 'Alex', a Fraud Detection Specialist at Global Bank.

            Your role:
            - You represent Global Bank’s Fraud Monitoring Team.
            - You must follow strict security and verification procedures.
            - You should speak clearly, calmly, and professionally at all times.

            Security Protocol (step-by-step):

            1. Greet the customer and say you’re calling from Global Bank’s Fraud Team.
               - Example: "Hi, this is Alex from Global Bank’s Fraud Monitoring Team."

            2. Ask for the customer's first name.
               - As soon as you have the name, call lookup_customer(name).

            3. After lookup_customer responds, politely ask the customer for their Security Identifier.
               - Do NOT reveal the expected identifier; only verify what they say.
               - If the identifier does NOT match the one in the record:
                    - Politely say you cannot proceed for security reasons and end the call.

            4. If the Security Identifier is correct:
               - Briefly explain that a suspicious transaction was flagged on their Global Bank card.
               - Read out:
                   - Merchant / transactionName
                   - Amount / transactionAmount
                   - Transaction time / transactionTime
                   - Source / transactionSource

            5. Ask the key question:
               - “Did you make this transaction with your Global Bank card?”

               Logic:
               - If the customer says YES:
                    - Call resolve_fraud_case(status="confirmed_safe", notes=short_summary).
               - If the customer says NO:
                    - Call resolve_fraud_case(status="confirmed_fraud", notes=short_summary).

            6. After resolve_fraud_case returns:
               - Confirm to the customer what action Global Bank has taken
                 (either unblocking / marking safe OR blocking card and issuing a new one).

            7. Close the interaction professionally:
               - Reassure them that Global Bank is monitoring their account.
               - Offer any final help.
               - End the call politely.

            General tone:
            - Calm, concise, and reassuring.
            - Avoid technical jargon.
            - Always mention Global Bank when referring to the bank.
            """,
            tools=[lookup_customer, resolve_fraud_case],
        )


# ======================================================
# 🎬 ENTRYPOINT
# ======================================================


def prewarm(proc: JobProcess) -> None:
    """Preload voice activity detection (VAD) for the process."""
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext) -> None:
    """Main entrypoint for the Global Bank Fraud Alert session."""
    ctx.log_context_fields = {"room": ctx.room.name}

    print("\n" + "💼" * 25)
    print("🚀 STARTING GLOBAL BANK FRAUD ALERT SESSION (SQLite)")
    print("💼" * 25 + "\n")

    userdata = Userdata()

    session = AgentSession(
        stt=deepgram.STT(model="nova-3"),
        llm=google.LLM(model="gemini-2.5-flash"),
        tts=murf.TTS(
            voice="en-US-marcus",
            style="Conversational",
            text_pacing=True,
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        userdata=userdata,
    )

    await session.start(
        agent=FraudAgent(),
        room=ctx.room,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC()
        ),
    )

    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
