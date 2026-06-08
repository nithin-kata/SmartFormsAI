"""
AI Service — SmartForms
Primary  : Google Gemini API (free tier, works everywhere after deployment)
Fallback : Smart Template Engine (pure Python, zero dependencies, always works)
"""

import json
import urllib.request
import urllib.error
from collections import Counter

# ─────────────────────────────────────────────
# Gemini REST API
# ─────────────────────────────────────────────

GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-1.5-flash:generateContent"
)


def call_gemini(api_key: str, system_prompt: str, user_message: str) -> dict:
    """Call the Gemini API and return {'success': True, 'content': str} or error."""
    if not api_key:
        return {"success": False, "error": "no_key"}

    payload = json.dumps({
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"parts": [{"text": user_message}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 2048
        }
    }).encode("utf-8")

    url = f"{GEMINI_API_URL}?key={api_key}"
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            print("[AI] Gemini API call succeeded.")
            return {"success": True, "content": text}

    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        print(f"[AI] Gemini HTTP error {e.code}: {body[:300]}")
        try:
            err_data = json.loads(body)
            msg = err_data.get("error", {}).get("message", "")
        except Exception:
            msg = body[:200]
        return {"success": False, "error": f"HTTP {e.code}: {msg}"}

    except Exception as e:
        print(f"[AI] Gemini connection error: {e}")
        return {"success": False, "error": str(e)}


# ─────────────────────────────────────────────
# Smart Template Engine — Form Generation
# ─────────────────────────────────────────────

_FORM_TEMPLATES = {
    "registration": {
        "keywords": ["registration", "register", "event", "conference", "seminar", "workshop", "signup", "sign up", "enroll"],
        "title_suffix": "Registration Form",
        "questions": [
            {"question_text": "Full Name", "question_type": "short_text", "is_required": True, "options": []},
            {"question_text": "Email Address", "question_type": "email", "is_required": True, "options": []},
            {"question_text": "Phone Number", "question_type": "phone", "is_required": False, "options": []},
            {"question_text": "Date of Event / Preferred Date", "question_type": "date", "is_required": True, "options": []},
            {"question_text": "Number of Attendees", "question_type": "multiple_choice", "is_required": True, "options": ["1", "2–5", "6–10", "More than 10"]},
            {"question_text": "Dietary Preferences / Special Requirements", "question_type": "long_text", "is_required": False, "options": []},
            {"question_text": "How did you hear about this event?", "question_type": "multiple_choice", "is_required": False, "options": ["Social Media", "Email", "Friend / Colleague", "Website", "Other"]},
            {"question_text": "Any additional comments or questions?", "question_type": "long_text", "is_required": False, "options": []},
        ]
    },
    "feedback": {
        "keywords": ["feedback", "survey", "review", "opinion", "satisfaction", "rating", "experience", "evaluate", "assessment"],
        "title_suffix": "Feedback Survey",
        "questions": [
            {"question_text": "Overall Satisfaction", "question_type": "rating", "is_required": True, "options": []},
            {"question_text": "How likely are you to recommend us to a friend or colleague?", "question_type": "rating", "is_required": True, "options": []},
            {"question_text": "What did you like most?", "question_type": "long_text", "is_required": False, "options": []},
            {"question_text": "What could we improve?", "question_type": "long_text", "is_required": False, "options": []},
            {"question_text": "How was the overall quality?", "question_type": "multiple_choice", "is_required": True, "options": ["Excellent", "Good", "Average", "Below Average", "Poor"]},
            {"question_text": "Would you use our service again?", "question_type": "yes_no", "is_required": True, "options": []},
            {"question_text": "Any other comments or suggestions?", "question_type": "long_text", "is_required": False, "options": []},
        ]
    },
    "job": {
        "keywords": ["job", "application", "apply", "hiring", "career", "employment", "vacancy", "position", "recruit", "resume", "cv"],
        "title_suffix": "Job Application",
        "questions": [
            {"question_text": "Full Name", "question_type": "short_text", "is_required": True, "options": []},
            {"question_text": "Email Address", "question_type": "email", "is_required": True, "options": []},
            {"question_text": "Phone Number", "question_type": "phone", "is_required": True, "options": []},
            {"question_text": "Position Applying For", "question_type": "short_text", "is_required": True, "options": []},
            {"question_text": "Years of Relevant Experience", "question_type": "multiple_choice", "is_required": True, "options": ["Less than 1 year", "1–3 years", "3–5 years", "5–10 years", "10+ years"]},
            {"question_text": "Highest Level of Education", "question_type": "multiple_choice", "is_required": True, "options": ["High School", "Bachelor's Degree", "Master's Degree", "PhD", "Other"]},
            {"question_text": "Key Skills (comma-separated)", "question_type": "long_text", "is_required": True, "options": []},
            {"question_text": "When can you start?", "question_type": "date", "is_required": False, "options": []},
            {"question_text": "Why are you interested in this position?", "question_type": "long_text", "is_required": True, "options": []},
        ]
    },
    "contact": {
        "keywords": ["contact", "inquiry", "enquiry", "message", "get in touch", "reach", "support", "help", "question"],
        "title_suffix": "Contact Form",
        "questions": [
            {"question_text": "Full Name", "question_type": "short_text", "is_required": True, "options": []},
            {"question_text": "Email Address", "question_type": "email", "is_required": True, "options": []},
            {"question_text": "Phone Number", "question_type": "phone", "is_required": False, "options": []},
            {"question_text": "Subject", "question_type": "short_text", "is_required": True, "options": []},
            {"question_text": "Type of Inquiry", "question_type": "multiple_choice", "is_required": True, "options": ["General Question", "Technical Support", "Billing", "Partnership", "Other"]},
            {"question_text": "Your Message", "question_type": "long_text", "is_required": True, "options": []},
            {"question_text": "Preferred contact method?", "question_type": "multiple_choice", "is_required": False, "options": ["Email", "Phone", "Either"]},
        ]
    },
    "order": {
        "keywords": ["order", "purchase", "buy", "product", "booking", "reservation", "shop", "request"],
        "title_suffix": "Order Form",
        "questions": [
            {"question_text": "Full Name", "question_type": "short_text", "is_required": True, "options": []},
            {"question_text": "Email Address", "question_type": "email", "is_required": True, "options": []},
            {"question_text": "Phone Number", "question_type": "phone", "is_required": True, "options": []},
            {"question_text": "Delivery Address", "question_type": "long_text", "is_required": True, "options": []},
            {"question_text": "Product / Service Requested", "question_type": "short_text", "is_required": True, "options": []},
            {"question_text": "Quantity", "question_type": "multiple_choice", "is_required": True, "options": ["1", "2–5", "6–10", "10+"]},
            {"question_text": "Special Instructions", "question_type": "long_text", "is_required": False, "options": []},
            {"question_text": "Preferred Delivery Date", "question_type": "date", "is_required": False, "options": []},
        ]
    },
    "quiz": {
        "keywords": ["quiz", "test", "exam", "assessment", "knowledge", "trivia", "questionnaire"],
        "title_suffix": "Quiz",
        "questions": [
            {"question_text": "Your Name", "question_type": "short_text", "is_required": True, "options": []},
            {"question_text": "Email Address", "question_type": "email", "is_required": True, "options": []},
            {"question_text": "Question 1: How familiar are you with this topic?", "question_type": "multiple_choice", "is_required": True, "options": ["Not at all", "Somewhat", "Moderately", "Very familiar", "Expert"]},
            {"question_text": "Question 2: Describe your experience with this subject", "question_type": "long_text", "is_required": True, "options": []},
            {"question_text": "Question 3: True or False — Continuous learning improves performance", "question_type": "yes_no", "is_required": True, "options": []},
            {"question_text": "How would you rate your confidence on this topic?", "question_type": "rating", "is_required": True, "options": []},
            {"question_text": "Any additional thoughts?", "question_type": "long_text", "is_required": False, "options": []},
        ]
    },
    "health": {
        "keywords": ["health", "medical", "patient", "clinic", "hospital", "doctor", "appointment", "symptom", "wellness"],
        "title_suffix": "Health Form",
        "questions": [
            {"question_text": "Full Name", "question_type": "short_text", "is_required": True, "options": []},
            {"question_text": "Date of Birth", "question_type": "date", "is_required": True, "options": []},
            {"question_text": "Email Address", "question_type": "email", "is_required": True, "options": []},
            {"question_text": "Phone Number", "question_type": "phone", "is_required": True, "options": []},
            {"question_text": "Primary Reason for Visit / Complaint", "question_type": "long_text", "is_required": True, "options": []},
            {"question_text": "Do you have any known allergies?", "question_type": "yes_no", "is_required": True, "options": []},
            {"question_text": "If yes, please list your allergies", "question_type": "long_text", "is_required": False, "options": []},
            {"question_text": "Current Medications (if any)", "question_type": "long_text", "is_required": False, "options": []},
            {"question_text": "Preferred Appointment Date", "question_type": "date", "is_required": True, "options": []},
        ]
    },
}

_DEFAULT_QUESTIONS = [
    {"question_text": "Full Name", "question_type": "short_text", "is_required": True, "options": []},
    {"question_text": "Email Address", "question_type": "email", "is_required": True, "options": []},
    {"question_text": "Phone Number", "question_type": "phone", "is_required": False, "options": []},
    {"question_text": "How did you find us?", "question_type": "multiple_choice", "is_required": False, "options": ["Social Media", "Search Engine", "Friend / Referral", "Advertisement", "Other"]},
    {"question_text": "How would you rate your experience?", "question_type": "rating", "is_required": True, "options": []},
    {"question_text": "Additional Comments", "question_type": "long_text", "is_required": False, "options": []},
]


def _detect_template(prompt: str) -> str:
    """Return the best matching template key for the given prompt."""
    prompt_lower = prompt.lower()
    best_key = None
    best_score = 0
    for key, tpl in _FORM_TEMPLATES.items():
        score = sum(1 for kw in tpl["keywords"] if kw in prompt_lower)
        if score > best_score:
            best_score = score
            best_key = key
    return best_key if best_score > 0 else None


def generate_form_from_template(prompt: str) -> dict:
    """Generate a form using the built-in template engine (no API needed)."""
    template_key = _detect_template(prompt)
    template = _FORM_TEMPLATES.get(template_key) if template_key else None

    # Build a clean title from the prompt
    prompt_clean = prompt.strip().rstrip(".")
    title = prompt_clean[:60] if len(prompt_clean) <= 60 else prompt_clean[:57] + "..."
    if template:
        title = title or template["title_suffix"]

    questions = template["questions"] if template else _DEFAULT_QUESTIONS
    description = f"Auto-generated form for: {prompt_clean}"

    return {
        "success": True,
        "data": {
            "title": title,
            "description": description,
            "questions": [dict(q) for q in questions],
        },
        "source": "template"
    }


# ─────────────────────────────────────────────
# Smart Template Engine — Response Analysis
# ─────────────────────────────────────────────

def analyze_responses_template(form_title: str, questions: list, responses_data: list) -> dict:
    """Generate a structured analysis report using pure Python stats (no API needed)."""
    total = len(responses_data)
    if total == 0:
        return {"success": False, "error": "No responses to analyze."}

    sections = {
        "ratings": [],
        "choices": [],
        "texts": [],
        "yes_no": [],
    }

    for q in questions:
        qtype = q.get("question_type", "short_text")
        qtext = q.get("question_text", "")
        q_answers = []

        for resp in responses_data:
            for ans in resp.get("answers", []):
                if ans.get("question_id") == q["id"] and ans.get("answer_value"):
                    q_answers.append(ans["answer_value"])

        if not q_answers:
            continue

        if qtype == "rating":
            try:
                nums = [float(v) for v in q_answers if v.strip().isdigit()]
                if nums:
                    avg = sum(nums) / len(nums)
                    sections["ratings"].append({"q": qtext, "avg": round(avg, 2), "count": len(nums)})
            except Exception:
                pass

        elif qtype in ("multiple_choice", "checkboxes", "dropdown"):
            dist = Counter(q_answers)
            sections["choices"].append({"q": qtext, "dist": dict(dist), "count": len(q_answers)})

        elif qtype == "yes_no":
            dist = Counter(q_answers)
            sections["yes_no"].append({"q": qtext, "dist": dict(dist)})

        else:  # short_text, long_text, email, phone, date, etc.
            sections["texts"].append({"q": qtext, "samples": q_answers[:3], "count": len(q_answers)})

    # Determine overall sentiment from ratings
    all_ratings = [r["avg"] for r in sections["ratings"]]
    if all_ratings:
        overall_avg = sum(all_ratings) / len(all_ratings)
        if overall_avg >= 4.0:
            sentiment = "Positive 😊"
            sentiment_pct = f"~{int(overall_avg / 5 * 100)}% positive"
        elif overall_avg >= 3.0:
            sentiment = "Neutral 😐"
            sentiment_pct = "Mixed responses"
        else:
            sentiment = "Negative 😟"
            sentiment_pct = f"~{int((5 - overall_avg) / 5 * 100)}% dissatisfied"
    else:
        sentiment = "Neutral 😐"
        sentiment_pct = "No rating questions found"

    # Build markdown report
    lines = [
        f"## Executive Summary",
        f"",
        f"This report analyzes **{total} response(s)** collected for the form **\"{form_title}\"**. "
        f"The data was processed automatically using SmartForms' built-in analytics engine.",
        f"",
        f"## Sentiment Analysis",
        f"",
        f"**Overall Sentiment: {sentiment}**",
        f"",
        f"{sentiment_pct}. Based on {len(all_ratings)} rating question(s) across all responses.",
        f"",
        f"## Key Insights",
        f"",
        f"- **Total Responses Collected:** {total}",
    ]

    for r in sections["ratings"]:
        lines.append(f"- **{r['q']}:** Average rating **{r['avg']}/5** across {r['count']} responses")

    for c in sections["choices"]:
        top = max(c["dist"], key=c["dist"].get)
        top_pct = round(c["dist"][top] / c["count"] * 100)
        lines.append(f"- **{c['q']}:** Most common answer — \"{top}\" ({top_pct}%)")

    for yn in sections["yes_no"]:
        yes_count = yn["dist"].get("Yes", yn["dist"].get("yes", 0))
        yes_pct = round(yes_count / total * 100)
        lines.append(f"- **{yn['q']}:** {yes_pct}% answered Yes")

    lines += [
        f"",
        f"## Trends & Patterns",
        f"",
    ]

    if sections["choices"]:
        for c in sections["choices"]:
            dist_str = ", ".join([f'"{k}": {v}' for k, v in sorted(c["dist"].items(), key=lambda x: -x[1])])
            lines.append(f"- **{c['q']}** distribution: {dist_str}")
    else:
        lines.append("- Insufficient structured data to identify strong trends.")

    if sections["texts"]:
        lines.append("")
        lines.append("**Sample open-ended responses:**")
        for t in sections["texts"][:2]:
            if t["samples"]:
                sample_list = "; ".join([f'"{s[:80]}"' for s in t["samples"]])
                lines.append(f"- *{t['q']}*: {sample_list}")

    lines += [
        f"",
        f"## Recommendations",
        f"",
    ]

    recommendations = [
        f"1. **Continue monitoring responses** — with {total} response(s) so far, more data will reveal stronger trends.",
    ]

    if sections["ratings"]:
        low_ratings = [r for r in sections["ratings"] if r["avg"] < 3.5]
        high_ratings = [r for r in sections["ratings"] if r["avg"] >= 4.0]
        if low_ratings:
            recommendations.append(f"2. **Focus on improvement** — \"{low_ratings[0]['q']}\" scored below average ({low_ratings[0]['avg']}/5). Investigate root causes.")
        if high_ratings:
            recommendations.append(f"3. **Leverage strengths** — \"{high_ratings[0]['q']}\" scored highly ({high_ratings[0]['avg']}/5). Highlight this in communications.")

    if len(recommendations) < 3:
        recommendations.append("2. **Increase response volume** — share the form on more channels to get statistically significant data.")
        recommendations.append("3. **Follow up** with respondents who left open-ended feedback for deeper qualitative insights.")
    recommendations.append(f"{len(recommendations) + 1}. **Export the data** to CSV for deeper analysis in spreadsheet tools.")

    lines += recommendations
    lines += [
        f"",
        f"---",
        f"*Report generated automatically by SmartForms Analytics Engine. {total} responses analyzed.*"
    ]

    return {"success": True, "content": "\n".join(lines), "source": "template"}


# ─────────────────────────────────────────────
# Public API — Form Generation
# ─────────────────────────────────────────────

GEMINI_FORM_SYSTEM = """You are an expert form designer. When given a description, generate a well-structured form with appropriate questions.

Return ONLY valid JSON with this exact structure:
{
    "title": "Form Title",
    "description": "Brief description of the form",
    "questions": [
        {
            "question_text": "Question text here",
            "question_type": "short_text|long_text|email|phone|multiple_choice|checkboxes|dropdown|rating|yes_no|date",
            "is_required": true,
            "options": ["Option 1", "Option 2"]
        }
    ]
}

Guidelines:
- Generate 6-12 relevant questions
- Use varied question types appropriate to the content
- For rating questions, no options needed (1-5 scale)
- For yes_no questions, no options needed
- Make questions clear and professional
- Return ONLY the JSON, no markdown, no explanation"""


def generate_form_from_prompt(api_key: str, prompt: str) -> dict:
    """
    Generate a form from a natural language prompt.
    Uses Gemini API if key is available, otherwise falls back to template engine.
    """
    # Try Gemini first
    if api_key:
        result = call_gemini(api_key, GEMINI_FORM_SYSTEM, f"Create a form for: {prompt}")
        if result["success"]:
            try:
                content = result["content"].strip()
                # Strip markdown fences if present
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                form_data = json.loads(content)
                return {"success": True, "data": form_data, "source": "gemini"}
            except json.JSONDecodeError as e:
                print(f"[AI] Gemini returned invalid JSON, falling back to template. Error: {e}")
        else:
            print(f"[AI] Gemini failed ({result['error']}), falling back to template engine.")

    # Fallback: template engine
    print("[AI] Using built-in template engine.")
    return generate_form_from_template(prompt)


# ─────────────────────────────────────────────
# Public API — Response Analysis
# ─────────────────────────────────────────────

GEMINI_ANALYSIS_SYSTEM = """You are an expert data analyst specializing in survey analysis and business intelligence.
Analyze the form response data and provide comprehensive insights.

Structure your response with these EXACT sections using markdown:

## Executive Summary
[2-3 sentences summarizing overall findings]

## Sentiment Analysis
[Analyze the overall sentiment - Positive/Neutral/Negative with percentage estimates and reasoning]

## Key Insights
[5-7 bullet points with the most important findings]

## Trends & Patterns
[Notable patterns, correlations, or trends in the data]

## Recommendations
[3-5 actionable recommendations based on the data]

Be specific, data-driven, and professional. Reference actual numbers and percentages where possible."""


def analyze_responses(api_key: str, form_title: str, questions: list, responses_data: list) -> dict:
    """
    Analyze form responses and return a markdown insight report.
    Uses Gemini API if key is available, otherwise falls back to built-in stats engine.
    """
    if not responses_data:
        return {"success": False, "error": "No responses to analyze."}

    # Try Gemini first
    if api_key:
        # Build summary for Gemini
        summary_parts = [f"Form: {form_title}", f"Total Responses: {len(responses_data)}", "\nQuestions and Answers Summary:"]
        for q in questions:
            q_answers = []
            for resp in responses_data:
                for ans in resp.get("answers", []):
                    if ans.get("question_id") == q["id"] and ans.get("answer_value"):
                        q_answers.append(ans["answer_value"])
            summary_parts.append(f"\nQ: {q['question_text']} ({q['question_type']})")
            if q_answers:
                if q["question_type"] in ("multiple_choice", "dropdown", "yes_no", "rating", "checkboxes"):
                    counts = Counter(q_answers)
                    summary_parts.append(f"Distribution: {dict(counts)}")
                else:
                    summary_parts.append(f"Sample responses ({len(q_answers)} total): {'; '.join(q_answers[:3])}")
            else:
                summary_parts.append("No responses")

        data_summary = "\n".join(summary_parts)
        result = call_gemini(api_key, GEMINI_ANALYSIS_SYSTEM, f"Please analyze this form response data:\n\n{data_summary}")

        if result["success"]:
            return {"success": True, "content": result["content"], "source": "gemini"}
        else:
            print(f"[AI] Gemini analysis failed ({result['error']}), falling back to template engine.")

    # Fallback: built-in stats analysis
    print("[AI] Using built-in template analysis engine.")
    return analyze_responses_template(form_title, questions, responses_data)
