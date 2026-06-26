"""
services/llm_service.py — NVIDIA NIM LLM Client
Uses OpenAI-compatible SDK (NVIDIA NIM endpoint).
extract_commitment(): structured extraction from raw text
generate_recovery_plan(): recovery steps for high-risk commitments
"""
import json
from datetime import date, timedelta
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
from loguru import logger
from app.config import settings

class LLMService:
    def __init__(self):
        if settings.NVIDIA_API_KEY:
            self.client = AsyncOpenAI(api_key=settings.NVIDIA_API_KEY, base_url=settings.NVIDIA_BASE_URL)
        else:
            self.client = None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def extract_commitment(self, raw_text: str) -> dict:
        """
        Given raw text, returns structured commitment JSON.
        Returns mock data if no NVIDIA key configured (dev fallback).
        """
        if not self.client:
            return self._mock_extraction(raw_text)

        today_str = str(date.today())
        system_prompt = """You extract structured commitment data from text.
Return ONLY valid JSON with these keys:
- type: one of [bill, interview, assignment, event, other]
- title: short descriptive title (max 80 chars)
- description: brief context (max 200 chars) or null
- due_date: ISO date string YYYY-MM-DD
- amount: numeric amount in INR if present, else null
- confidence: float 0.0 to 1.0

If no clear due date is mentioned, use 7 days from today.
Return ONLY JSON, no other text."""

        user_msg = f"""Today is {today_str}. Extract commitment from:

{raw_text}"""
        response = await self.client.chat.completions.create(
            model=settings.NVIDIA_MODEL,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_msg}],
            max_tokens=400, temperature=0.1,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("\n", 1)[0]
        data = json.loads(raw)
        if "due_date" in data:
            data["due_date"] = date.fromisoformat(data["due_date"])
        return data

    async def generate_recovery_plan(self, commitment) -> str:
        """Generate step-by-step recovery plan for high-risk commitment."""
        if not self.client:
            days = (commitment.due_date - date.today()).days
            return f"Recovery Plan for '{commitment.title}':\n1. Break this into 3-4 smaller tasks\n2. Dedicate one Pomodoro session daily\n3. Track progress each morning\n4. Escalate if {days} days is not enough"

        prompt = f"""Create a concise, actionable recovery plan (4-6 bullet points) for:
Commitment: {commitment.title}
Type: {commitment.type}
Due: {commitment.due_date}
Risk: {commitment.root_cause or 'time pressure'}
Amount: {commitment.amount or 'N/A'}

Provide practical, specific steps. Start each with an action verb."""
        response = await self.client.chat.completions.create(
            model=settings.NVIDIA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300, temperature=0.3,
        )
        return response.choices[0].message.content.strip()

    def _mock_extraction(self, raw_text: str) -> dict:
        """Dev fallback when no LLM key — basic heuristic extraction."""
        lower = raw_text.lower()
        c_type = "bill" if any(w in lower for w in ["bill", "payment", "pay", "invoice"]) else                  "interview" if "interview" in lower else                  "assignment" if any(w in lower for w in ["assignment", "submit", "project"]) else "other"
        import re
        amount = None
        m = re.search(r"[₹rs\.\s](\d[\d,]*)", raw_text, re.IGNORECASE)
        if m:
            try:
                amount = float(m.group(1).replace(",", ""))
            except:
                pass
        due = date.today() + timedelta(days=7)
        title = raw_text[:80].strip().split("\n")[0]
        return {"type": c_type, "title": title, "description": raw_text[:200], "due_date": due, "amount": amount, "confidence": 0.7}
