import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
CHUNKS_FILE = ROOT / "data" / "chunks.jsonl"

LLM_MODE = os.getenv("LLM_MODE", "live")          # "live" or "fake"
ANSWER_MODEL = os.getenv("ANSWER_MODEL", "claude-sonnet-5-5")
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "claude-sonnet-5-5")
ANSWER_EFFORT = os.getenv("ANSWER_EFFORT", "low")
JUDGE_EFFORT = os.getenv("JUDGE_EFFORT", "medium")

TOP_K = 5
PROMPT_VERSION = "rag-v1"

# USD per million tokens (input, output). Check the pricing page when you change models.
PRICES = {"claude-sonnet-5-5": (2.0, 10.0)}
