"""Transparency labels shown to readers on the platform.

One label per attribution state (planning.md "Definitions"). The AI-leaning
labels are deliberately careful and offer a path to contest the result, since
a false accusation against a human writer is the worst outcome on a creative
platform.
"""

LABELS = {
    "human": (
        "This sample appears to be human generated and did not have any "
        "tell-tale signs of AI. Excellent job!"
    ),
    "likely-human": (
        "We believe that this sample is probably human generated, but cannot "
        "be certain."
    ),
    "uncertain": (
        "We could not determine whether this sample was AI or human generated. "
        "Thus we have given it the uncertain label."
    ),
    "likely-AI": (
        "We believe that this may have been AI generated, but cannot "
        "definitively determine it at this time. If you believe this is wrong, "
        "then please let us know."
    ),
    "AI": (
        "We apologize, but we determined that this sample is AI generated. If "
        "you believe this is wrong, then please let us know."
    ),
}


def label_for(attribution):
    """Return the transparency-label text for an attribution state."""
    return LABELS.get(attribution, LABELS["uncertain"])
