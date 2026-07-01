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
from detection import combine_signals, groq_signal, interpret, stylometric_signal

app = Flask(__name__)


@app.route("/submit", methods=["POST"])
def submit():
    body = request.get_json(silent=True) or {}
    text = body.get("text")
    creator_id = body.get("creator_id")

    if not text or not creator_id:
        return jsonify({"error": "Both 'text' and 'creator_id' are required."}), 400

    content_id = str(uuid.uuid4())

    try:
        groq = groq_signal(text)
    except Exception as exc:  # network/parse failure -> surface cleanly
        return jsonify({"error": f"Detection failed: {exc}"}), 502

    styl = stylometric_signal(text)
    combined = combine_signals(groq["p_ai"], styl["p_ai"], styl)
    confidence = combined["p_ai"]
    attribution = interpret(confidence)

    # Label still a placeholder until M5.
    label = "(placeholder — transparency label added in M5)"

    audit.append_entry(
        {
            "event_type": "classification",
            "content_id": content_id,
            "creator_id": creator_id,
            "attribution": attribution,
            "confidence": confidence,
            "groq_score": groq["p_ai"],
            "groq_reasoning": groq["reasoning"],
            "heuristic_score": styl["p_ai"],
            "heuristic_metrics": styl["metrics"],
            "adjustments": combined["adjustments"],
            "status": "classified",
        }
    )

    return jsonify(
        {
            "content_id": content_id,
            "attribution": attribution,
            "confidence": confidence,
            "label": label,
            "signals": {
                "groq_score": groq["p_ai"],
                "groq_reasoning": groq["reasoning"],
                "heuristic_score": styl["p_ai"],
                "heuristic_metrics": styl["metrics"],
            },
            "adjustments": combined["adjustments"],
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
