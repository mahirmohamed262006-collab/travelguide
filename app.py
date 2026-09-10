import os

from flask import Flask, jsonify, render_template, request
from dotenv import load_dotenv
from google import genai

from chatbot_config import SYSTEM_PROMPT

load_dotenv()

app = Flask(__name__)

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")


def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    return genai.Client(api_key=api_key)


def normalize_history(history):
    """Keep only valid conversation messages and limit the history."""
    if not isinstance(history, list):
        return []

    cleaned = []

    for message in history[-20:]:
        if not isinstance(message, dict):
            continue

        role = message.get("role")
        content = message.get("content")

        if role in {"user", "assistant"} and isinstance(content, str):
            content = content.strip()
            if content:
                cleaned.append({"role": role, "content": content})

    return cleaned


def build_prompt(history, user_message):
    conversation = []

    for message in history:
        role = "Traveler" if message["role"] == "user" else "TravelGuide"
        conversation.append(f"{role}: {message['content']}")

    conversation.append(f"Traveler: {user_message}")

    return f"{SYSTEM_PROMPT}\n\nConversation:\n" + "\n".join(conversation)


@app.route("/")
def home():
    return render_template("index.html")


@app.post("/api/chat")
def chat():
    data = request.get_json(silent=True) or {}

    user_message = data.get("message", "")
    history = normalize_history(data.get("history", []))

    if not isinstance(user_message, str) or not user_message.strip():
        return jsonify({"error": "Please enter a travel or tourism-related question."}), 400

    user_message = user_message.strip()

    if len(user_message) > 4000:
        return jsonify({"error": "Please keep your message under 4000 characters."}), 400

    try:
        client = get_gemini_client()

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=build_prompt(history, user_message),
        )

        answer = getattr(response, "text", None)

        if not answer:
            return jsonify(
                {"error": "I could not generate a response. Please try again."}
            ), 502

        return jsonify({"answer": answer.strip()})

    except Exception:
        app.logger.exception("Gemini request failed")
        return jsonify(
            {"error": "Something went wrong while contacting the travel assistant."}
        ), 500


if __name__ == "__main__":
    app.run()
