from flask import Flask, request, jsonify
from flask_cors import CORS

from google import genai
from google.genai import types

from dotenv import load_dotenv

import os
import base64
import requests
import re

from concurrent.futures import ThreadPoolExecutor, as_completed


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
    raise ValueError("GEMINI_API_KEY is missing from .env")

if not QWEN_API_KEY:
    raise ValueError("QWEN_API_KEY is missing from .env")

if not NEMOTRON_API_KEY:
    raise ValueError("NEMOTRON_API_KEY is missing from .env")


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
"""


# =========================================================
# GEMINI ANALYSIS
# =========================================================

def analyze_with_gemini(
    image_bytes,
    mime_type,
    case_prompt
):

    try:

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

        return {
            "model": "Gemini",
            "success": True,
            "result": result_text
        }

    except Exception as error:

        print("GEMINI ERROR:")
        print(error)

        return {
            "model": "Gemini",
            "success": False,
            "result": "",
            "error": str(error)
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

    try:

        # -------------------------------------------------
        # Convert image to Base64
        # -------------------------------------------------

        image_base64 = base64.b64encode(
            image_bytes
        ).decode("utf-8")


        image_url = (
            f"data:{mime_type};base64,{image_base64}"
        )


        # -------------------------------------------------
        # Headers
        # -------------------------------------------------

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }


        # -------------------------------------------------
        # Request payload
        # -------------------------------------------------

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

            ]
        }


        # -------------------------------------------------
        # Send request
        # -------------------------------------------------

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=120
        )


        response.raise_for_status()


        result_data = response.json()


        print(
            f"\n{model_display_name} OPENROUTER RESPONSE:"
        )

        print(result_data)


        # -------------------------------------------------
        # Validate response
        # -------------------------------------------------

        if "choices" not in result_data:

            raise Exception(
                "OpenRouter returned an unexpected response: "
                f"{result_data}"
            )


        if not result_data["choices"]:

            raise Exception(
                "OpenRouter returned no choices: "
                f"{result_data}"
            )


        message = result_data["choices"][0].get(
            "message",
            {}
        )


        result_text = message.get("content")


        # -------------------------------------------------
        # Some reasoning models can return content
        # as a list / structured format.
        # -------------------------------------------------

        if isinstance(result_text, list):

            text_parts = []

            for part in result_text:

                if isinstance(part, dict):

                    text_value = part.get("text")

                    if text_value:
                        text_parts.append(
                            str(text_value)
                        )

                elif isinstance(part, str):

                    text_parts.append(part)


            result_text = "\n".join(text_parts)


        # -------------------------------------------------
        # Validate final text
        # -------------------------------------------------

        if not result_text:

            raise Exception(
                "Model returned no text content: "
                f"{result_data}"
            )


        return {
            "model": model_display_name,
            "success": True,
            "result": result_text
        }


    except Exception as error:

        print(
            f"{model_display_name} ERROR:"
        )

        print(error)


        return {
            "model": model_display_name,
            "success": False,
            "result": "",
            "error": str(error)
        }


# =========================================================
# EXTRACT POSSIBLE CONDITIONS
# =========================================================

def extract_possible_conditions(text):

    """
    Demonstration-level extraction.

    This is NOT medical validation.

    It looks for content following headings such as:
    possible conditions, possible causes, concerns, etc.
    """

    if not text:
        return []


    text_lower = text.lower()


    keywords = [

        "possible conditions",

        "possible causes",

        "possible concern",

        "possible concerns",

        "conditions",

        "causes"

    ]


    extracted = []

    lines = text.split("\n")

    collecting = False


    for line in lines:

        clean = line.strip()


        if not clean:
            continue


        lower = clean.lower()


        if any(
            keyword in lower
            for keyword in keywords
        ):

            collecting = True

            continue


        if collecting:

            if clean.startswith(
                (
                    "1.",
                    "2.",
                    "3.",
                    "4.",
                    "5.",
                    "-",
                    "*"
                )
            ):

                clean = clean.lstrip(
                    "0123456789.-* "
                )


                if len(clean) > 3:

                    extracted.append(clean)


            elif len(extracted) >= 3:

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

        conditions = extract_possible_conditions(
            item.get("result", "")
        )

        model_conditions[
            item["model"]
        ] = conditions


    all_conditions = []


    for conditions in model_conditions.values():

        for condition in conditions:

            all_conditions.append(
                condition.lower()
            )


    agreement = {}


    for condition in set(all_conditions):

        count = 0


        for conditions in model_conditions.values():

            condition_lower = condition.lower()


            if any(

                condition_lower in c.lower()

                or

                c.lower() in condition_lower

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
    MediScan rule-based consensus engine.

    It:

    1. Collects successful model outputs
    2. Extracts common sections
    3. Groups similar findings
    4. Detects repeated findings
    5. Preserves red flags
    6. Preserves uncertainty
    7. Produces ONE consolidated report

    This does NOT determine which AI model is medically correct.

    This is NOT clinical validation.
    """


    # =====================================================
    # COLLECT SUCCESSFUL MODELS
    # =====================================================

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

Please try again later.

### MediScan Safety Note

This system provides preliminary AI-generated
information and does not replace evaluation by
a qualified healthcare professional or veterinarian.

""".strip()


    # =====================================================
    # SECTION NAMES
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


        lines = text.splitlines()


        for raw_line in lines:

            line = raw_line.strip()


            if not line:
                continue


            # ---------------------------------------------
            # Remove markdown formatting
            # ---------------------------------------------

            clean = line

            clean = clean.replace("**", "")
            clean = clean.replace("__", "")

            clean = clean.replace("###", "")
            clean = clean.replace("##", "")
            clean = clean.replace("#", "")

            clean = clean.strip()


            # ---------------------------------------------
            # Remove numbered heading prefix
            #
            # Examples:
            # 1. Visible Observations
            # 2. Reported Symptoms
            # 8. Uncertainty and Limitations
            # ---------------------------------------------

            clean_for_matching = re.sub(
                r"^\d+\s*[\.\):\-]\s*",
                "",
                clean
            ).strip()


            # ---------------------------------------------
            # Check section heading
            # ---------------------------------------------

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


            # ---------------------------------------------
            # Start new section
            # ---------------------------------------------

            if matched_section:

                current_section = matched_section

                continue


            # ---------------------------------------------
            # Store content
            # ---------------------------------------------

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


        # -------------------------------------------------
        # Sort by model support
        # -------------------------------------------------

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


            # ---------------------------------------------
            # Use shortest / clearest statement
            # ---------------------------------------------

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
    # BUILD FINAL REPORT
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


    # -----------------------------------------------------
    # IMPORTANT:
    # This count is calculated dynamically from the actual
    # successful model responses.
    # -----------------------------------------------------

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


    # -----------------------------------------------------
    # Shared condition groups
    # -----------------------------------------------------

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


    # -----------------------------------------------------
    # Uncertainty
    # -----------------------------------------------------

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


    # =====================================================
    # RETURN REPORT
    # =====================================================

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

    return jsonify({

        "success": True,

        "message": (
            "Backend connection is working!"
        )

    })


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

                return jsonify({

                    "success": False,

                    "error": (
                        "No animal image selected"
                    )

                }), 400


            image_bytes = image_file.read()


            if not image_bytes:

                return jsonify({

                    "success": False,

                    "error": (
                        "Animal image is empty"
                    )

                }), 400


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

                return jsonify({

                    "success": False,

                    "error": (
                        "No image provided"
                    )

                }), 400


            image_data = data["image"]


            # ---------------------------------------------
            # Detect MIME type from data URL
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
        # RUN ALL THREE MODELS
        # =================================================

        print("")
        print("==============================================")
        print("MEDISCAN AI - STARTING MULTI-MODEL ANALYSIS")
        print("==============================================")
        print("")


        results = []


        with ThreadPoolExecutor(
            max_workers=3
        ) as executor:

            futures = [

                executor.submit(

                    analyze_with_gemini,

                    image_bytes,

                    mime_type,

                    case_prompt

                ),

                executor.submit(

                    analyze_with_openrouter,

                    QWEN_API_KEY,

                    QWEN_MODEL,

                    "Qwen",

                    image_bytes,

                    mime_type,

                    case_prompt

                ),

                executor.submit(

                    analyze_with_openrouter,

                    NEMOTRON_API_KEY,

                    NEMOTRON_MODEL,

                    "Nemotron",

                    image_bytes,

                    mime_type,

                    case_prompt

                )

            ]


            for future in as_completed(futures):

                try:

                    results.append(
                        future.result()
                    )

                except Exception as error:

                    print(
                        "MODEL THREAD ERROR:"
                    )

                    print(error)


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
                    f"  Error: {item.get('error', 'Unknown error')}"
                )


        successful_count = len([

            item

            for item in results

            if item.get("success") is True
            and item.get("result")
            and str(item.get("result")).strip()

        ])


        print("")
        print(
            f"SUCCESSFUL MODELS: "
            f"{successful_count}/3"
        )

        print("")


        # =================================================
        # BUILD FINAL REPORT
        # =================================================

        final_report = build_consensus_report(
            results,
            case_type
        )


        # =================================================
        # RESPONSE
        # =================================================

        return jsonify({

            "success": True,

            "type": case_type,

            # Existing frontend can continue using this
            "result": final_report,

            # Individual model responses
            "models": results,

            # Number of successful models
            "successful_models": successful_count,

            "total_models": 3,

            # Consensus information
            "consensus":
                calculate_textual_agreement(
                    results
                )

        })


    except Exception as error:

        print(
            "==================================="
        )

        print(
            "MEDISCAN AI ERROR:"
        )

        print(error)

        print(
            "==================================="
        )


        return jsonify({

            "success": False,

            "error": str(error)

        }), 500


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

            return jsonify({

                "success": False,

                "error": (
                    "Message is required."
                )

            }), 400


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


        response = gemini_client.models.generate_content(

            model=GEMINI_MODEL,

            contents=prompt

        )


        return jsonify({

            "success": True,

            "reply": response.text

        })


    except Exception as error:

        print(
            "CHAT ERROR:"
        )

        print(error)


        return jsonify({

            "success": False,

            "error": str(error)

        }), 500


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