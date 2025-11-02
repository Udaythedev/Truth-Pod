#!/usr/bin/env python3
"""Example script to call the configured verification provider.

This script is intentionally simple: it reads environment variables to determine
which provider to call (Vertex or Gemini), sends a small payload, and prints the
returned confidence. It's meant for local testing or CI runs gated by secrets.
"""
import os
import argparse
from app.verify import verify_text


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--text", default="Local test: The quick brown fox announced a breakthrough.", help="Text to verify")
    args = p.parse_args()

    provider = "none"
    if os.getenv("VERTEX_API_ENDPOINT") and os.getenv("VERTEX_API_KEY"):
        provider = "vertex"
    elif os.getenv("GEMINI_API_URL") and os.getenv("GEMINI_API_KEY"):
        provider = "gemini"

    print(f"Provider detected: {provider}")
    conf = verify_text(args.text)
    print(f"Verified confidence: {conf}")


if __name__ == "__main__":
    main()
