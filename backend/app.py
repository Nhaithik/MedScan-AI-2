from flask import Flask, request, jsonify
from flask_cors import CORS

from google import genai
from google.genai import types

from dotenv import load_dotenv

import os
import base64
import requests
import re
import time


# =========================================================
# LOAD ENVIRONMENT VARIABLES
# =========================================================

load_dotenv()


# =========================================================
# FLASK APP
# =========================================================

app = Flask(__name__)
CORS(app)


# =========================================================
# API KEYS
# =========================================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
QWEN_API_KEY = os.getenv("QWEN_API_KEY")
NEMOTRON_API_KEY = os.getenv("NEMOTRON_API_KEY")


if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is missing from environment variables")


if not QWEN_API_KEY:
    raise ValueError("QWEN_API_KEY is missing from environment variables")


if not NEMOTRON_API_KEY:
    raise ValueError("NEMOTRON_API_KEY is missing from environment variables")


# =========================================================
# GEMINI CLIENT
# =========================================================

gemini_client = genai.Client(
    api_key=GEMINI_API_KEY
)


# =========================================================
# MODEL NAMES
# =========================================================

GEMINI_MODEL = "gemini-3.6-flash"

QWEN_MODEL = "qwen/qwen3.8-27b:free"

NEMOTRON_MODEL = (
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"
)


# =========================================================
# OPENROUTER CONFIGURATION
# =========================================================

OPENROUTER_URL = (
    "https://openrouter.ai/api/v1/chat/completions"
)

OPENROUTER_SITE_URL = os.getenv(
    "OPENROUTER_SITE_URL",
    "https://medscan-ai-2-eg67.onrender.com"
)

OPENROUTER_APP_NAME = os.getenv(
    "OPENROUTER_APP_NAME",
    "MediScan AI"
)


# =========================================================
# REQUEST SETTINGS
# =========================================================

MAX_RETRIES = 3

REQUEST_TIMEOUT = 90

RETRY_DELAY_SECONDS = 4


# =========================================================
# SAFETY INSTRUCTIONS
# =========================================================

SAFETY_INSTRUCTIONS = """
IMPORTANT SAFETY RULES:

- This system provides preliminary AI-generated health information.
- Do NOT provide a definitive diagnosis.
- Do NOT claim certainty.
- Do NOT prescribe medicines or dosages.
- Do NOT invent symptoms or image findings.
- Clearly distinguish visible observations from possible conditions.
- Mention uncertainty when appropriate.
- Preserve important warning signs or red flags.
- Recommend consultation with a qualified healthcare professional
  or veterinarian when appropriate.
- For potentially serious or emergency situations, advise
  immediate professional medical attention.
- Never claim that agreement between AI models proves a diagnosis.
"""


# =========================================================
# UTILITY FUNCTIONS
# =========================================================

def clean_error_message(error_text):
    """
    Convert long provider errors into a shorter readable message.
    """

    if not error_text:
        return "Unknown error"

    text = str(error_text)

    # Remove excessive whitespace
    text = re.sub(r"\s+", " ", text).strip()

    # Keep errors reasonably short
    if len(text) > 1200:
        text = text[:1200] + "..."

    return text


def is_retryable_error(error_text):
    """
    Detect temporary provider/API errors where retrying may help.
    """

    if not error_text:
        return False

    text = str(error_text).lower()

    retry_keywords = [
        "429",
        "502",
        "503",
        "504",
        "rate limit",
        "rate_limit",
        "too many requests",
        "resourceexhausted",
        "resource exhausted",
        "temporarily unavailable",
        "service unavailable",
        "high demand",
        "provider_unavailable",
        "timeout",
        "timed out",
        "connection reset",
        "connection error",
        "upstream error"
    ]

    return any(
        keyword in text
        for keyword in retry_keywords
    )


def extract_openrouter_text(result_data):
    """
    Safely extract text from OpenRouter responses.
    Supports normal strings and structured content lists.
    """

    if not isinstance(result_data, dict):
        return ""

    choices = result_data.get("choices")

    if not choices:
        return ""

    first_choice = choices[0]

    if not isinstance(first_choice, dict):
        return ""

    message = first_choice.get("message", {})

    if not isinstance(message, dict):
        return ""

    content = message.get("content")

    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):

        parts = []

        for part in content:

            if isinstance(part, dict):

                text_value = part.get("text")

                if text_value:
                    parts.append(str(text_value))

            elif isinstance(part, str):

                parts.append(part)

        return "\n".join(parts).strip()

    return ""


# =========================================================
# GEMINI ANALYSIS
# =========================================================

def analyze_with_gemini(
    image_bytes,
    mime_type,
    case_prompt
):

    last_error = ""

    for attempt in range(1, MAX_RETRIES + 1):

        try:

            print(
                f"[Gemini] Attempt {attempt}/{MAX_RETRIES}"
            )

            response = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[
                    types.Part.from_bytes(
                        data=image_bytes,
                        mime_type=mime_type
                    ),
                    case_prompt
                ]
            )

            result_text = response.text

            if not result_text:
                raise Exception(
                    "Gemini returned no text content."
                )

            print(
                "[Gemini] SUCCESS"
            )

            return {
                "model": "Gemini",
                "success": True,
                "result": result_text.strip()
            }

        except Exception as error:

            last_error = clean_error_message(error)

            print(
                f"[Gemini] ERROR attempt {attempt}:"
            )
            print(last_error)

            if attempt < MAX_RETRIES and is_retryable_error(
                last_error
            ):

                print(
                    f"[Gemini] Temporary error. "
                    f"Retrying in {RETRY_DELAY_SECONDS} seconds..."
                )

                time.sleep(RETRY_DELAY_SECONDS)

            else:
                break

    return {
        "model": "Gemini",
        "success": False,
        "result": "",
        "error": last_error
    }


# =========================================================
# OPENROUTER ANALYSIS
# =========================================================

def analyze_with_openrouter(
    api_key,
    model_name,
    model_display_name,
    image_bytes,
    mime_type,
    case_prompt
):

    last_error = ""

    # -----------------------------------------------------
    # Convert image to Base64
    # -----------------------------------------------------

    image_base64 = base64.b64encode(
        image_bytes
    ).decode("utf-8")

    image_url = (
        f"data:{mime_type};base64,{image_base64}"
    )

    # -----------------------------------------------------
    # Headers
    # -----------------------------------------------------

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": OPENROUTER_SITE_URL,
        "X-Title": OPENROUTER_APP_NAME
    }

    # -----------------------------------------------------
    # Request payload
    # -----------------------------------------------------

    payload = {
        "model": model_name,

        "messages": [
            {
                "role": "user",

                "content": [
                    {
                        "type": "text",
                        "text": case_prompt
                    },

                    {
                        "type": "image_url",

                        "image_url": {
                            "url": image_url
                        }
                    }
                ]
            }
        ],

        "temperature": 0.2,

        "max_tokens": 2500,

        # Allow OpenRouter to try another provider
        # when the first provider is unavailable.
        "provider": {
            "allow_fallbacks": True
        }
    }

    # -----------------------------------------------------
    # Retry loop
    # -----------------------------------------------------

    for attempt in range(1, MAX_RETRIES + 1):

        try:

            print(
                f"[{model_display_name}] "
                f"Attempt {attempt}/{MAX_RETRIES}"
            )

            response = requests.post(
                OPENROUTER_URL,
                headers=headers,
                json=payload,
                timeout=REQUEST_TIMEOUT
            )

            # -------------------------------------------------
            # Read response body before raising errors
            # -------------------------------------------------

            try:

                result_data = response.json()

            except Exception:

                result_data = {
                    "raw_response": response.text
                }

            # -------------------------------------------------
            # HTTP ERROR
            # -------------------------------------------------

            if response.status_code >= 400:

                error_message = (
                    result_data
                    .get("error", {})
                    .get("message")
                    if isinstance(result_data, dict)
                    else None
                )

                if not error_message:

                    error_message = (
                        result_data
                        .get("raw_response", response.text)
                        if isinstance(result_data, dict)
                        else response.text
                    )

                last_error = (
                    f"HTTP {response.status_code}: "
                    f"{clean_error_message(error_message)}"
                )

                print(
                    f"[{model_display_name}] ERROR:"
                )
                print(last_error)

                if (
                    attempt < MAX_RETRIES
                    and (
                        response.status_code in [
                            429,
                            500,
                            502,
                            503,
                            504
                        ]
                        or is_retryable_error(last_error)
                    )
                ):

                    print(
                        f"[{model_display_name}] "
                        f"Retrying in {RETRY_DELAY_SECONDS} seconds..."
                    )

                    time.sleep(RETRY_DELAY_SECONDS)

                    continue

                break

            # -------------------------------------------------
            # Validate response
            # -------------------------------------------------

            if not isinstance(result_data, dict):

                raise Exception(
                    "OpenRouter returned an invalid response."
                )

            if "choices" not in result_data:

                provider_error = result_data.get(
                    "error",
                    result_data
                )

                raise Exception(
                    "OpenRouter returned no choices: "
                    + clean_error_message(provider_error)
                )

            if not result_data["choices"]:

                raise Exception(
                    "OpenRouter returned an empty choices array."
                )

            # -------------------------------------------------
            # Extract response text
            # -------------------------------------------------

            result_text = extract_openrouter_text(
                result_data
            )

            if not result_text:

                raise Exception(
                    "Model returned no text content."
                )

            print(
                f"[{model_display_name}] SUCCESS"
            )

            return {
                "model": model_display_name,
                "success": True,
                "result": result_text
            }

        except Exception as error:

            last_error = clean_error_message(error)

            print(
                f"[{model_display_name}] "
                f"ERROR attempt {attempt}:"
            )

            print(last_error)

            if (
                attempt < MAX_RETRIES
                and is_retryable_error(last_error)
            ):

                print(
                    f"[{model_display_name}] "
                    f"Temporary error. "
                    f"Retrying in {RETRY_DELAY_SECONDS} seconds..."
                )

                time.sleep(RETRY_DELAY_SECONDS)

            else:

                break

    return {
        "model": model_display_name,
        "success": False,
        "result": "",
        "error": last_error
    }


# =========================================================
# EXTRACT POSSIBLE CONDITIONS
# =========================================================

def extract_possible_conditions(text):

    if not text:
        return []

    keywords = [
        "possible conditions",
        "possible conditions or causes",
        "possible causes",
        "possible concern",
        "possible concerns",
        "conditions",
        "causes",
        "abnormalities"
    ]

    extracted = []

    lines = text.splitlines()

    collecting = False

    for line in lines:

        clean = line.strip()

        if not clean:
            continue

        # Remove markdown
        clean = clean.replace("**", "")
        clean = clean.replace("###", "")
        clean = clean.replace("##", "")
        clean = clean.replace("#", "")
        clean = clean.strip()

        lower = clean.lower()

        # Find the section
        if any(
            keyword in lower
            for keyword in keywords
        ):

            collecting = True
            continue

        if collecting:

            # Stop at another obvious heading
            if re.match(
                r"^\d+\.\s+",
                clean
            ):

                heading_words = [
                    "visible",
                    "reported",
                    "evidence",
                    "reasoning",
                    "red flags",
                    "urgency",
                    "recommended",
                    "uncertainty"
                ]

                if any(
                    word in lower
                    for word in heading_words
                ):

                    break

            clean = re.sub(
                r"^[-•*]\s*",
                "",
                clean
            )

            clean = re.sub(
                r"^\d+[\.\):\-]\s*",
                "",
                clean
            )

            clean = clean.strip()

            if len(clean) > 3:

                extracted.append(clean)

            if len(extracted) >= 5:
                break

    return extracted[:5]


# =========================================================
# CALCULATE TEXTUAL AGREEMENT
# =========================================================

def calculate_textual_agreement(results):

    successful_results = [
        item
        for item in results
        if item.get("success") is True
        and item.get("result")
        and str(item.get("result")).strip()
    ]

    if len(successful_results) < 2:

        return {
            "available": False,
            "agreement_level": "Insufficient data",
            "message": (
                "Not enough successful model responses "
                "to calculate agreement."
            )
        }

    model_conditions = {}

    for item in successful_results:

        model_conditions[
            item["model"]
        ] = extract_possible_conditions(
            item.get("result", "")
        )

    agreement = {}

    all_conditions = []

    for conditions in model_conditions.values():

        for condition in conditions:

            all_conditions.append(
                condition.lower()
            )

    for condition in set(all_conditions):

        count = 0

        for conditions in model_conditions.values():

            if any(
                condition in c.lower()
                or c.lower() in condition
                for c in conditions
            ):

                count += 1

        if count >= 2:

            agreement[condition] = count

    if len(successful_results) == 3:

        agreement_level = (
            "Multi-model comparison available"
        )

    else:

        agreement_level = (
            "Partial multi-model comparison"
        )

    return {
        "available": True,
        "agreement_level": agreement_level,
        "model_conditions": model_conditions,
        "shared_possible_conditions": agreement
    }


# =========================================================
# FINAL MEDISCAN CONSENSUS REPORT
# =========================================================

def build_consensus_report(
    results,
    case_type
):

    """
    MediScan rule-based multi-model consensus engine.

    This engine:
    - collects successful model outputs
    - extracts common sections
    - groups similar findings
    - preserves red flags
    - preserves uncertainty
    - produces one consolidated report

    It does NOT determine which model is medically correct.
    It is NOT clinical validation.
    """

    successful = [
        item
        for item in results
        if item.get("success") is True
        and item.get("result")
        and str(item.get("result")).strip()
    ]

    total_models = len(successful)

    # =====================================================
    # NO SUCCESSFUL MODELS
    # =====================================================

    if not successful:

        return """
# MEDISCAN AI

## Consolidated Preliminary Assessment

No usable AI analysis was available for this case.

All configured AI models were temporarily unavailable
or returned an error.

Please try again later.

### MediScan Safety Note

This system provides preliminary AI-generated
information and does not replace evaluation by
a qualified healthcare professional or veterinarian.
        """.strip()

    # =====================================================
    # SECTION ALIASES
    # =====================================================

    section_aliases = {

        "visible_observations": [
            "Visible Observations"
        ],

        "reported_symptoms": [
            "Reported Symptoms"
        ],

        "possible_conditions": [
            "Possible Conditions or Causes",
            "Possible Conditions",
            "Possible Abnormalities or Concerns"
        ],

        "reasoning": [
            "Evidence / Reasoning",
            "Supporting Reasoning"
        ],

        "red_flags": [
            "Red Flags",
            "Important Red Flags"
        ],

        "urgency": [
            "Preliminary Urgency"
        ],

        "next_steps": [
            "Recommended Next Steps"
        ],

        "uncertainty": [
            "Uncertainty and Limitations"
        ]
    }

    # =====================================================
    # EXTRACT SECTIONS FROM ONE MODEL
    # =====================================================

    def extract_sections(text):

        sections = {
            key: []
            for key in section_aliases
        }

        current_section = None

        for raw_line in text.splitlines():

            line = raw_line.strip()

            if not line:
                continue

            clean = line

            # Remove markdown
            clean = clean.replace("**", "")
            clean = clean.replace("__", "")
            clean = clean.replace("###", "")
            clean = clean.replace("##", "")
            clean = clean.replace("#", "")
            clean = clean.strip()

            # Remove numbered heading
            clean_for_matching = re.sub(
                r"^\d+\s*[\.\):\-]\s*",
                "",
                clean
            ).strip()

            matched_section = None

            for section_key, aliases in section_aliases.items():

                for alias in aliases:

                    if clean_for_matching.lower().startswith(
                        alias.lower()
                    ):

                        matched_section = section_key
                        break

                if matched_section:
                    break

            if matched_section:

                current_section = matched_section
                continue

            if current_section:

                clean_content = re.sub(
                    r"^[-•*]\s*",
                    "",
                    clean
                ).strip()

                if not clean_content:
                    continue

                if clean_content in [
                    "---",
                    "___",
                    "***"
                ]:
                    continue

                sections[current_section].append(
                    clean_content
                )

        return sections

    # =====================================================
    # EXTRACT ALL MODEL SECTIONS
    # =====================================================

    model_sections = []

    for item in successful:

        model_sections.append(
            {
                "model": item["model"],
                "sections": extract_sections(
                    item["result"]
                )
            }
        )

    # =====================================================
    # NORMALIZE TEXT
    # =====================================================

    def normalize(text):

        text = text.lower()

        punctuation = (
            ".",
            ",",
            ":",
            ";",
            "!",
            "?",
            "(",
            ")",
            "[",
            "]",
            "{",
            "}",
            "-",
            "_",
            "*"
        )

        for char in punctuation:

            text = text.replace(
                char,
                " "
            )

        words = text.split()

        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "of",
            "to",
            "is",
            "are",
            "may",
            "can",
            "be",
            "with",
            "for",
            "in",
            "on",
            "this",
            "that",
            "from",
            "as",
            "it",
            "not",
            "by"
        }

        words = [
            word
            for word in words
            if word not in stop_words
        ]

        return set(words)

    # =====================================================
    # TEXT SIMILARITY
    # =====================================================

    def similarity(
        text_a,
        text_b
    ):

        words_a = normalize(text_a)
        words_b = normalize(text_b)

        if not words_a or not words_b:
            return 0

        intersection = words_a.intersection(
            words_b
        )

        union = words_a.union(
            words_b
        )

        if not union:
            return 0

        return (
            len(intersection)
            /
            len(union)
        )

    # =====================================================
    # COMBINE SECTION
    # =====================================================

    def combine_section(section_key):

        entries = []

        for model in model_sections:

            for text in model["sections"].get(
                section_key,
                []
            ):

                if len(text) < 4:
                    continue

                entries.append(
                    {
                        "text": text,
                        "model": model["model"]
                    }
                )

        groups = []

        for entry in entries:

            placed = False

            for group in groups:

                representative = group[0]["text"]

                if similarity(
                    entry["text"],
                    representative
                ) >= 0.30:

                    group.append(entry)

                    placed = True
                    break

            if not placed:

                groups.append(
                    [entry]
                )

        # Sort by number of supporting models
        groups.sort(
            key=lambda group: len(
                set(
                    item["model"]
                    for item in group
                )
            ),
            reverse=True
        )

        final_items = []

        for group in groups:

            unique_models = set(
                item["model"]
                for item in group
            )

            representative = min(
                group,
                key=lambda item: len(
                    item["text"]
                )
            )["text"]

            final_items.append(
                {
                    "text": representative,
                    "count": len(unique_models)
                }
            )

        return final_items

    # =====================================================
    # BUILD REPORT
    # =====================================================

    report = []

    report.append(
        "# MEDISCAN AI"
    )

    report.append(
        "## Consolidated Preliminary Assessment"
    )

    report.append("")

    report.append(
        "MediScan independently analyzed this case "
        "using multiple AI models and consolidated "
        "the available findings into one preliminary "
        "assessment."
    )

    # =====================================================
    # VISIBLE OBSERVATIONS
    # =====================================================

    observations = combine_section(
        "visible_observations"
    )

    if observations:

        report.append(
            "### 1. Visible Observations"
        )

        for item in observations[:6]:

            report.append(
                f"- {item['text']}"
            )

    # =====================================================
    # REPORTED SYMPTOMS
    # =====================================================

    symptoms = combine_section(
        "reported_symptoms"
    )

    if symptoms:

        report.append(
            "### 2. Reported Symptoms"
        )

        for item in symptoms[:6]:

            report.append(
                f"- {item['text']}"
            )

    # =====================================================
    # POSSIBLE CONDITIONS
    # =====================================================

    conditions = combine_section(
        "possible_conditions"
    )

    if conditions:

        report.append(
            "### 3. Possible Conditions or Causes"
        )

        for item in conditions[:7]:

            if item["count"] >= 2:

                report.append(
                    f"- {item['text']} "
                    f"({item['count']}/{total_models} "
                    f"models mentioned a similar possibility)"
                )

            else:

                report.append(
                    f"- {item['text']} "
                    "(mentioned as a possibility)"
                )

    # =====================================================
    # REASONING
    # =====================================================

    reasoning = combine_section(
        "reasoning"
    )

    if reasoning:

        report.append(
            "### 4. Supporting Reasoning"
        )

        for item in reasoning[:5]:

            report.append(
                f"- {item['text']}"
            )

    # =====================================================
    # RED FLAGS
    # =====================================================

    red_flags = combine_section(
        "red_flags"
    )

    if red_flags:

        report.append(
            "### 5. Important Red Flags"
        )

        for item in red_flags[:8]:

            report.append(
                f"- {item['text']}"
            )

    # =====================================================
    # URGENCY
    # =====================================================

    urgency = combine_section(
        "urgency"
    )

    if urgency:

        report.append(
            "### 6. Preliminary Urgency"
        )

        for item in urgency[:3]:

            report.append(
                f"- {item['text']}"
            )

    # =====================================================
    # NEXT STEPS
    # =====================================================

    next_steps = combine_section(
        "next_steps"
    )

    if next_steps:

        report.append(
            "### 7. Recommended Next Steps"
        )

        for item in next_steps[:7]:

            report.append(
                f"- {item['text']}"
            )

    # =====================================================
    # MODEL AGREEMENT + UNCERTAINTY
    # =====================================================

    report.append(
        "### 8. Model Agreement and Uncertainty"
    )

    if total_models == 3:

        report.append(
            "- Three independent AI models provided "
            "usable analyses for this case."
        )

    elif total_models == 2:

        report.append(
            "- Two independent AI models provided "
            "usable analyses for this case."
        )

    elif total_models == 1:

        report.append(
            "- One independent AI model provided "
            "a usable analysis for this case."
        )

    else:

        report.append(
            "- No independent AI model provided "
            "a usable analysis."
        )

    agreed_conditions = [
        item
        for item in conditions
        if item["count"] >= 2
    ]

    if agreed_conditions:

        report.append(
            "- Some findings were mentioned by "
            "more than one model, indicating internal "
            "agreement across those model outputs."
        )

    else:

        report.append(
            "- The models did not show strong textual "
            "agreement on the possible-condition findings."
        )

    uncertainty = combine_section(
        "uncertainty"
    )

    for item in uncertainty[:4]:

        report.append(
            f"- {item['text']}"
        )

    # =====================================================
    # SAFETY NOTE
    # =====================================================

    report.append(
        "### 9. MediScan Safety Note"
    )

    report.append(
        "This is a consolidated AI-generated "
        "preliminary assessment, not a medical "
        "or veterinary diagnosis. Agreement between "
        "AI models does not medically confirm a "
        "condition. A qualified healthcare professional "
        "or veterinarian should evaluate the case "
        "when appropriate."
    )

    return "\n\n".join(report)


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return "MediScan AI Backend is Running!"


# =========================================================
# TEST
# =========================================================

@app.route("/test")
def test():

    return jsonify(
        {
            "success": True,
            "message": "Backend connection is working!"
        }
    )


# =========================================================
# MAIN ANALYZE ENDPOINT
# =========================================================

@app.route(
    "/analyze",
    methods=["POST"]
)
def analyze():

    try:

        image_bytes = None

        mime_type = "image/jpeg"

        # =================================================
        # ANIMAL REQUEST
        # =================================================

        if "image" in request.files:

            image_file = request.files["image"]

            if image_file.filename == "":

                return jsonify(
                    {
                        "success": False,
                        "error": "No animal image selected"
                    }
                ), 400

            image_bytes = image_file.read()

            if not image_bytes:

                return jsonify(
                    {
                        "success": False,
                        "error": "Animal image is empty"
                    }
                ), 400

            # ---------------------------------------------
            # Animal information
            # ---------------------------------------------

            animal_type = request.form.get(
                "animal_type",
                "Unknown"
            )

            breed = request.form.get(
                "breed",
                "Not provided"
            )

            age = request.form.get(
                "age",
                "Not provided"
            )

            age_unit = request.form.get(
                "age_unit",
                "Years"
            )

            symptoms = request.form.get(
                "symptoms",
                "Not provided"
            )

            behaviour = request.form.get(
                "behaviour",
                "Not provided"
            )

            mime_type = image_file.mimetype

            if mime_type not in [
                "image/jpeg",
                "image/png",
                "image/webp"
            ]:

                mime_type = "image/jpeg"

            case_type = "animal"

            # ---------------------------------------------
            # Animal AI prompt
            # ---------------------------------------------

            case_prompt = f"""
You are one of three independent AI models participating
in the MediScan AI multi-model health analysis system.

Analyze the provided animal image together with the
information below.

Animal information:

Animal type: {animal_type}

Breed: {breed}

Age: {age} {age_unit}

Symptoms: {symptoms}

Behaviour: {behaviour}

Provide a structured preliminary analysis.

Include exactly these sections:

1. Visible Observations
2. Reported Symptoms
3. Possible Conditions or Causes
4. Evidence / Reasoning
5. Red Flags
6. Preliminary Urgency
7. Recommended Next Steps
8. Uncertainty and Limitations

{SAFETY_INSTRUCTIONS}
"""

        # =================================================
        # HUMAN REQUEST
        # =================================================

        else:

            data = request.get_json(
                silent=True
            )

            if not data or "image" not in data:

                return jsonify(
                    {
                        "success": False,
                        "error": "No image provided"
                    }
                ), 400

            image_data = data["image"]

            if not isinstance(image_data, str):

                return jsonify(
                    {
                        "success": False,
                        "error": "Invalid image data"
                    }
                ), 400

            # ---------------------------------------------
            # Detect MIME type
            # ---------------------------------------------

            if "," in image_data:

                header, image_data = image_data.split(
                    ",",
                    1
                )

                if "image/png" in header:

                    mime_type = "image/png"

                elif "image/webp" in header:

                    mime_type = "image/webp"

                else:

                    mime_type = "image/jpeg"

            image_bytes = base64.b64decode(
                image_data
            )

            if not image_bytes:

                return jsonify(
                    {
                        "success": False,
                        "error": "Decoded image is empty"
                    }
                ), 400

            case_type = "human"

            # ---------------------------------------------
            # Human AI prompt
            # ---------------------------------------------

            case_prompt = f"""
You are one of three independent AI models participating
in the MediScan AI multi-model health analysis system.

Analyze the provided human health image carefully.

Provide a structured preliminary analysis.

Include exactly these sections:

1. Visible Observations
2. Possible Abnormalities or Concerns
3. Possible Conditions or Causes
4. Evidence / Reasoning
5. Red Flags
6. Preliminary Urgency
7. Recommended Next Steps
8. Uncertainty and Limitations

{SAFETY_INSTRUCTIONS}
"""

        # =================================================
        # START MULTI-MODEL ANALYSIS
        # =================================================

        print("")
        print("==============================================")
        print("MEDISCAN AI - STARTING MULTI-MODEL ANALYSIS")
        print("==============================================")
        print("")

        results = []

        # =================================================
        # MODEL 1 - GEMINI
        # =================================================

        print("----------------------------------------------")
        print("MODEL 1/3: GEMINI")
        print("----------------------------------------------")

        gemini_result = analyze_with_gemini(
            image_bytes,
            mime_type,
            case_prompt
        )

        results.append(
            gemini_result
        )

        # Small delay before next provider
        time.sleep(2)

        # =================================================
        # MODEL 2 - QWEN
        # =================================================

        print("----------------------------------------------")
        print("MODEL 2/3: QWEN")
        print("----------------------------------------------")

        qwen_result = analyze_with_openrouter(
            QWEN_API_KEY,
            QWEN_MODEL,
            "Qwen",
            image_bytes,
            mime_type,
            case_prompt
        )

        results.append(
            qwen_result
        )

        # Small delay before next provider
        time.sleep(2)

        # =================================================
        # MODEL 3 - NEMOTRON
        # =================================================

        print("----------------------------------------------")
        print("MODEL 3/3: NEMOTRON")
        print("----------------------------------------------")

        nemotron_result = analyze_with_openrouter(
            NEMOTRON_API_KEY,
            NEMOTRON_MODEL,
            "Nemotron",
            image_bytes,
            mime_type,
            case_prompt
        )

        results.append(
            nemotron_result
        )

        # =================================================
        # KEEP CONSISTENT MODEL ORDER
        # =================================================

        model_order = {
            "Gemini": 1,
            "Qwen": 2,
            "Nemotron": 3
        }

        results.sort(
            key=lambda x: model_order.get(
                x.get("model"),
                99
            )
        )

        # =================================================
        # PRINT MODEL STATUS
        # =================================================

        print("")
        print("==============================================")
        print("MODEL RESULTS")
        print("==============================================")

        for item in results:

            if item.get("success"):

                print(
                    f"✓ {item['model']} analysis included"
                )

            else:

                print(
                    f"✗ {item['model']} analysis failed"
                )

                print(
                    f"  Error: "
                    f"{item.get('error', 'Unknown error')}"
                )

        successful_models = [
            item
            for item in results
            if item.get("success") is True
            and item.get("result")
            and str(item.get("result")).strip()
        ]

        successful_count = len(
            successful_models
        )

        print("")
        print(
            f"SUCCESSFUL MODELS: "
            f"{successful_count}/3"
        )
        print("")

        # =================================================
        # ALL MODELS FAILED
        # =================================================

        if successful_count == 0:

            return jsonify(
                {
                    "success": False,

                    "type": case_type,

                    "result": (
                        "MediScan could not obtain a usable "
                        "AI analysis at this time. "
                        "Please try again later."
                    ),

                    "models": results,

                    "successful_models": 0,

                    "total_models": 3,

                    "consensus": {
                        "available": False,
                        "agreement_level": (
                            "No usable model responses"
                        ),
                        "message": (
                            "All three AI model requests "
                            "failed or were unavailable."
                        )
                    },

                    "error": (
                        "All configured AI models "
                        "were unavailable."
                    )
                }
            ), 503

        # =================================================
        # BUILD FINAL REPORT
        # =================================================

        final_report = build_consensus_report(
            results,
            case_type
        )

        # =================================================
        # CONSENSUS
        # =================================================

        consensus = calculate_textual_agreement(
            results
        )

        # =================================================
        # FINAL RESPONSE
        # =================================================

        return jsonify(
            {
                "success": True,

                "type": case_type,

                # Existing frontend uses this
                "result": final_report,

                # Individual model responses
                "models": results,

                # Successful model count
                "successful_models": successful_count,

                # Total configured models
                "total_models": 3,

                # Consensus information
                "consensus": consensus
            }
        )

    except Exception as error:

        print("")
        print("===================================")
        print("MEDISCAN AI ERROR:")
        print("===================================")
        print(error)
        print("===================================")
        print("")

        return jsonify(
            {
                "success": False,
                "error": str(error)
            }
        ), 500


# =========================================================
# CHAT ENDPOINT
# =========================================================

@app.route(
    "/chat",
    methods=["POST"]
)
def chat():

    try:

        data = request.get_json(
            silent=True
        ) or {}

        message = str(
            data.get(
                "message",
                ""
            )
        ).strip()

        if not message:

            return jsonify(
                {
                    "success": False,
                    "error": "Message is required."
                }
            ), 400

        prompt = f"""
You are MediScan AI Assistant.

You are a helpful healthcare information assistant
for the MediScan AI website.

Rules:

- Give clear, simple and safe health information.
- Do not claim to diagnose diseases.
- Do not prescribe medicines or doses.
- For emergencies, advise the user to seek immediate
  professional medical care.
- Keep answers concise and easy to understand.

User message:

{message}

Answer:
"""

        last_error = ""

        for attempt in range(
            1,
            MAX_RETRIES + 1
        ):

            try:

                print(
                    f"[Chat/Gemini] "
                    f"Attempt {attempt}/{MAX_RETRIES}"
                )

                response = (
                    gemini_client.models.generate_content(
                        model=GEMINI_MODEL,
                        contents=prompt
                    )
                )

                if not response.text:

                    raise Exception(
                        "Gemini returned no chat response."
                    )

                return jsonify(
                    {
                        "success": True,
                        "reply": response.text
                    }
                )

            except Exception as error:

                last_error = clean_error_message(
                    error
                )

                print(
                    "[Chat/Gemini] ERROR:"
                )

                print(last_error)

                if (
                    attempt < MAX_RETRIES
                    and is_retryable_error(last_error)
                ):

                    time.sleep(
                        RETRY_DELAY_SECONDS
                    )

                else:

                    break

        return jsonify(
            {
                "success": False,
                "error": last_error
            }
        ), 503

    except Exception as error:

        print(
            "CHAT ERROR:"
        )

        print(error)

        return jsonify(
            {
                "success": False,
                "error": str(error)
            }
        ), 500


# =========================================================
# START SERVER
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5002
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )