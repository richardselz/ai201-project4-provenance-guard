"""Provenance Guard — Flask API.

M3 scope: POST /submit runs the first detection signal (Groq) and writes a
structured audit entry; GET /log surfaces recent entries.

Confidence scoring (M4), the second signal (M4), transparency labels and the
appeal endpoint (M5) are added later. Where a value is not yet real it is
returned as a clearly-marked placeholder.
"""

import uuid

from flask import Flask, jsonify, request

import audit
from detection import groq_signal

app = Flask(__name__)


def _interim_attribution(p_ai):
    """Map a probability to an attribution label using the M2 threshold table.

    Interim only: in M3 this runs on the Groq score alone. In M4 it will run on
    the combined P(AI) from both signals.
    """
    if p_ai < 0.20:
        return "human"
    if p_ai < 0.30:
        return "likely-human"
    if p_ai < 0.73:
        return "uncertain"
    if p_ai < 0.85:
        return "likely-AI"
    return "AI"


@app.route("/submit", methods=["POST"])
def submit():
    body = request.get_json(silent=True) or {}
    text = body.get("text")
    creator_id = body.get("creator_id")

    if not text or not creator_id:
        return jsonify({"error": "Both 'text' and 'creator_id' are required."}), 400

    content_id = str(uuid.uuid4())

    try:
        signal = groq_signal(text)
    except Exception as exc:  # network/parse failure -> surface cleanly
        return jsonify({"error": f"Detection failed: {exc}"}), 502

    p_ai = signal["p_ai"]
    attribution = _interim_attribution(p_ai)

    # Placeholders until M4 (confidence) and M5 (label).
    confidence = None
    label = "(placeholder — transparency label added in M5)"

    audit.append_entry(
        {
            "event_type": "classification",
            "content_id": content_id,
            "creator_id": creator_id,
            "attribution": attribution,
            "confidence": confidence,
            "groq_score": p_ai,
            "groq_reasoning": signal["reasoning"],
            "status": "classified",
        }
    )

    return jsonify(
        {
            "content_id": content_id,
            "attribution": attribution,
            "confidence": confidence,
            "label": label,
            "signals": {"groq_score": p_ai, "groq_reasoning": signal["reasoning"]},
        }
    )


@app.route("/log", methods=["GET"])
def log():
    """Return recent audit-log entries. In production this would require auth;
    here it exists for documentation and grading visibility."""
    return jsonify({"entries": audit.get_recent()})


if __name__ == "__main__":
    # Port 8000 (not 5000): on macOS the AirPlay Receiver squats on port 5000.
    app.run(debug=True, port=8000)
