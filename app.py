"""Provenance Guard — Flask API.

M3 scope: POST /submit runs the first detection signal (Groq) and writes a
structured audit entry; GET /log surfaces recent entries.

Confidence scoring (M4), the second signal (M4), transparency labels and the
appeal endpoint (M5) are added later. Where a value is not yet real it is
returned as a clearly-marked placeholder.
"""

import uuid

from flask import Flask, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

import audit
from detection import combine_signals, groq_signal, interpret, stylometric_signal
from labels import label_for

app = Flask(__name__)

# Rate limiting. Limits are per client IP. See README for the reasoning behind
# these specific values (realistic creator usage vs. flood protection).
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)


@app.route("/submit", methods=["POST"])
@limiter.limit("10 per minute;100 per day")
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
    label = label_for(attribution)

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


@app.route("/appeal", methods=["POST"])
@limiter.limit("20 per hour")
def appeal():
    """Let a creator contest a classification.

    Captures their reasoning, flips the content's status to "under_review", and
    logs the appeal alongside a snapshot of the original decision (which is
    preserved). Does not re-classify — a human reviewer handles it later.
    """
    body = request.get_json(silent=True) or {}
    content_id = body.get("content_id")
    reasoning = body.get("creator_reasoning")

    if not content_id or not reasoning:
        return (
            jsonify({"error": "Both 'content_id' and 'creator_reasoning' are required."}),
            400,
        )

    original = audit.find_by_content_id(content_id)
    if original is None:
        return jsonify({"error": f"No classification found for content_id {content_id}."}), 404

    audit.update_status(content_id, "under_review")

    audit.append_entry(
        {
            "event_type": "appeal",
            "content_id": content_id,
            "creator_id": original.get("creator_id"),
            "appeal_reasoning": reasoning,
            "status": "under_review",
            "original_decision": {
                "attribution": original.get("attribution"),
                "confidence": original.get("confidence"),
                "groq_score": original.get("groq_score"),
                "heuristic_score": original.get("heuristic_score"),
            },
        }
    )

    return jsonify(
        {
            "content_id": content_id,
            "status": "under_review",
            "message": "Your appeal has been received and the content is now under review.",
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
