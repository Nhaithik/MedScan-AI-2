from flask import Flask, request, jsonify
from flask_cors import CORS
from google import genai
from google.genai import types
from dotenv import load_dotenv
import os
import base64

# Load .env
load_dotenv()

app = Flask(__name__)
CORS(app)

# Get Gemini API key
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY is missing from .env")

# Gemini client
client = genai.Client(api_key=api_key)


@app.route("/")
def home():
    return "MediScan AI Backend is Running!"


@app.route("/test")
def test():
    return jsonify({
        "success": True,
        "message": "Backend connection is working!"
    })


@app.route("/analyze", methods=["POST"])
def analyze():

    try:
        data = request.get_json()

        if not data or "image" not in data:
            return jsonify({
                "success": False,
                "error": "No image provided"
            }), 400

        # Get Base64 image from frontend
        image_data = data["image"]

        # Remove data:image/...;base64, if present
        if "," in image_data:
            image_data = image_data.split(",", 1)[1]

        image_bytes = base64.b64decode(image_data)

        # Send image to Gemini
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=[
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type="image/jpeg"
                ),
                """
                You are an AI medical image analysis assistant.

                Analyze the provided image carefully.

                Provide:
                1. What is visible in the image
                2. Possible observations
                3. Any notable abnormalities or areas that may need
                   professional review

                Do NOT provide a definitive diagnosis.
                Do NOT claim certainty.
                Clearly state that the result is informational and
                should be reviewed by a qualified healthcare professional.
                """
            ]
        )

        return jsonify({
            "success": True,
            "result": response.text
        })

    except Exception as e:

        print("ERROR:", e)

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5002,
        debug=True
    )