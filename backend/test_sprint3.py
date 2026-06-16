"""Quick validation tests for Sprint 3 Extractor changes."""

import sys
sys.path.insert(0, ".")

from app.extractors.requirement_extractor import requirement_extractor

print("=" * 60)
print("SPRINT 3 VALIDATION TESTS")
print("=" * 60)

# ── P1: Extractor Name Tests ─────────────────────────────────────────
print("\n[P1] Name Extraction:")
tests = [
    ("Build a website for Avengers", "Avengers"),
    ("Create an app for Movie Reviews", "Movie Reviews"),
    ("Build a dashboard for Stock Analytics", "Stock Analytics"),
    ("Make a portal for X", "X"),
    ("Build Avengers Website", "Avengers"),
]

for msg, expected in tests:
    state = {}
    updates = requirement_extractor.extract(msg, state)
    result = updates.get("project_name")
    status = "PASS" if result == expected else "FAIL"
    print(f"  [{status}] '{msg}' -> '{result}' (expected '{expected}')")

print("\n[P1] Name Synthesis:")
# Test missing name but other fields present
state = {
    "project_name": None,
    "theme": "Superhero / Marvel",
    "project_type": "Website",
}
inferred = requirement_extractor.infer(state)
expected = "Superhero Website"
result = inferred.get("project_name")
status = "PASS" if result == expected else "FAIL"
print(f"  [{status}] Synthesis 1 -> '{result}' (expected '{expected}')")

state = {
    "project_name": None,
    "purpose": "Entertainment",
    "project_type": "Dashboard",
}
inferred = requirement_extractor.infer(state)
expected = "Entertainment Dashboard"
result = inferred.get("project_name")
status = "PASS" if result == expected else "FAIL"
print(f"  [{status}] Synthesis 2 -> '{result}' (expected '{expected}')")

print("\n" + "=" * 60)
print("TESTS COMPLETED")
print("=" * 60)
