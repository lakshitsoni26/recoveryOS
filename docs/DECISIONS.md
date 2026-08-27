# Architectural Tradeoffs & Engineering Decisions
### Razorpay AI Buildathon — Track 3

---

## 1. Why a Deterministic Persona Bank over Live LLM Roleplay?

**The Flaw in Competitor Submissions:**
Most AI agent submissions have one LLM playing the agent and a second LLM playing the customer in a live loop. This creates **circular self-grading**: the LLM customer cooperates because it wants the agent to succeed, and running the eval twice produces completely different numbers.

**Our Architecture:**
We generated a 50-record deterministic persona bank with pre-written multi-turn response scripts and fixed `outcome_ground_truth` labels. Running our batch evaluation 100 times yields the **exact same 56.0% recovery rate and ₹221,700 capital recovery**, with SHA256 audit hashes proving non-tampering.

---

## 2. Why Drafting & Queuing over an Autonomous Autodialer?

TRAI regulations and RBI guidelines strictly regulate automated debt-collection dialers. Framing our solution as an **intelligent recovery queuing and drafting engine** allows fintech merchants to safely deploy this in production with human-in-the-loop oversight, strict calling windows (9 AM - 7 PM), and rigorous compliance logs.

---

## 3. What Broke During Development & How We Resolved It

### 🔴 Issue 1: Sarvam TTS Free-Tier Rate Limits (HTTP 429)
- **Symptom:** Sequential TTS synthesis failed after ~15 rapid calls during full batch runs.
- **Root Cause:** Rate-limit window saturation on Sarvam endpoints.
- **Resolution:** Engineered exponential backoff with jitter (`audio/sarvam_client.py`) and added a cost-aware toggle (`ENABLE_TTS=false`) with zero-latency sandbox synthesis for bulk evaluation.

### 🔴 Issue 2: LLM Slipping from Hinglish into Pure English
- **Symptom:** Generic LLMs often drift into formal English ("Your payment of ₹4500 is past due").
- **Root Cause:** English-heavy pre-training biases in default foundation models.
- **Resolution:** Crafted a culturally grounded system prompt (`agent/prompts/system.txt`) using Romanized Hinglish opening templates and strict tone boundaries ("Namaste Rohit ji! Main Razorpay accounts team se...").

### 🔴 Issue 3: Payment Link Expiration Mismatches
- **Symptom:** Standard test-mode links expired in 24 hours, causing stale links during multi-day demo evaluations.
- **Root Cause:** Default `expire_by` parameter was too tight.
- **Resolution:** Configured dynamic 48-hour to 7-day TTL with ISO UTC timestamp validation in `integrations/razorpay_client.py`.

### 🔴 Issue 4: Conversational Rigidity in Fixed Response Trees
- **Symptom:** Minor phrasing changes from the LLM agent failed to match strict dictionary keys in response scripts.
- **Root Cause:** Exact string matching between turns.
- **Resolution:** Implemented `HinglishIntentClassifier` with fuzzy regex intent clustering (`agree_to_pay`, `dispute_charge`, `reschedule_request`, `ghost_no_response`), mapping variable agent turns to canonical customer responses.
