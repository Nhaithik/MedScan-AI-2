from flask import Flask, request, jsonify
from flask_cors import CORS
from google import genai
from google.genai import types
from dotenv import load_dotenv
import os
import base64

# ---------------------------------------
# Load environment variables
# ---------------------------------------

load_dotenv()

app = Flask(__name__)
CORS(app)

# ---------------------------------------
# Gemini API
# ---------------------------------------

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY is missing from .env")

client = genai.Client(api_key=api_key)

# ---------------------------------------
# Home
# ---------------------------------------

@app.route("/")
def home():
    return "MediScan AI Backend is Running!"


# ---------------------------------------
# Test
# ---------------------------------------

@app.route("/test")
def test():
    return jsonify({
        "success": True,
        "message": "Backend connection is working!"
    })


# ---------------------------------------
# AI ANALYSIS
# Supports:
# 1. Human AI - JSON + Base64 image
# 2. Animal AI - FormData + image file
# ---------------------------------------

@app.route("/analyze", methods=["POST"])
def analyze():

    try:

        # =====================================================
        # ANIMAL AI
        # =====================================================

        if "image" in request.files:

            image_file = request.files["image"]

            if image_file.filename == "":
                return jsonify({
                    "success": False,
                    "error": "No animal image selected"
                }), 400

            # Read image
            image_bytes = image_file.read()

            if not image_bytes:
                return jsonify({
                    "success": False,
                    "error": "Animal image is empty"
                }), 400

            # Get animal information
            animal_type = request.form.get("animal_type", "Unknown")
            breed = request.form.get("breed", "Not provided")
            age = request.form.get("age", "Not provided")
            age_unit = request.form.get("age_unit", "Years")
            symptoms = request.form.get("symptoms", "Not provided")
            behaviour = request.form.get("behaviour", "Not provided")

            # Detect MIME type
            mime_type = image_file.mimetype

            if mime_type not in ["image/jpeg", "image/png", "image/webp"]:
                mime_type = "image/jpeg"

            # Animal AI prompt
            animal_prompt = f"""
You are MediScan AI, an AI-assisted animal health information system.

Analyze the provided animal image together with the information below.

Animal information:
- Animal type: {animal_type}
- Breed: {breed}
- Age: {age} {age_unit}
- Symptoms: {symptoms}
- Behaviour: {behaviour}

Provide a clear, structured informational assessment.

Include:

1. Visible observations
2. Possible concerns based on the image
3. Relationship between the reported symptoms and visible observations
4. Possible conditions or causes to discuss with a veterinarian
5. Recommended next steps
6. Signs that may require urgent veterinary attention

Important:
- Do NOT provide a definitive diagnosis.
- Do NOT claim certainty.
- Do NOT replace a veterinarian.
- Clearly explain that this is AI-generated informational guidance.
- If the image quality is insufficient, say so.
- Do not invent symptoms or findings that are not visible or provided.
- Use cautious language such as "may", "could", or "possible".
"""

            # Send image + prompt to Gemini
            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=[
                    types.Part.from_bytes(
                        data=image_bytes,
                        mime_type=mime_type
                    ),
                    animal_prompt
                ]
            )

            return jsonify({
                "success": True,
                "type": "animal",
                "result": response.text
            })


        # =====================================================
        # HUMAN AI
        # =====================================================

        data = request.get_json()

        if not data or "image" not in data:
            return jsonify({
                "success": False,
                "error": "No image provided"
            }), 400

        # Get Base64 image
        image_data = data["image"]

        # Remove data:image/...;base64,
        if "," in image_data:
            image_data = image_data.split(",", 1)[1]

        image_bytes = base64.b64decode(image_data)

        # Human AI prompt
        human_prompt = """
You are MediScan AI, an AI-assisted medical image analysis system.

Analyze the provided image carefully.

Provide:

1. What is visible in the image
2. Possible observations
3. Any notable abnormalities or areas that may need professional review
4. Recommended next steps

Important:
- Do NOT provide a definitive diagnosis.
- Do NOT claim certainty.
- Clearly state that the result is informational.
- Recommend review by a qualified healthcare professional.
- Do not invent findings that are not visible in the image.
"""

        # Send image + prompt to Gemini
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=[
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type="image/jpeg"
                ),
                human_prompt
            ]
        )

        return jsonify({
            "success": True,
            "type": "human",
            "result": response.text
        })


    # =====================================================
    # ERROR HANDLING
    # =====================================================

    except Exception as e:

        print("===================================")
        print("MediScan AI ERROR:")
        print(e)
        print("===================================")

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ---------------------------------------
# Start Flask
# ---------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5002))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )