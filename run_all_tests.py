"""
Saans Unified Test Runner
Executes the full test suite covering:
1. The 10 Mandatory Planner & Rules Tests (test_planner.py)
2. The Tamper-Evident Hash Chain Audit Tests (test_audit.py)
3. The Circular Validator & Hostile Input Refusal Tests (test_circular_validator.py)
"""

import sys
import unittest

def run_tests():
    # Windows consoles default to cp1252, which cannot print the status emoji below.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Discover and add all tests from tests/
    discovered = loader.discover(start_dir="tests", pattern="test_*.py")
    suite.addTests(discovered)

    runner = unittest.TextTestRunner(verbosity=2)
    print("=" * 70)
    print("SAANS HACKATHON TEST SUITE - DAY 1, DAY 2 & DAY 3 VALIDATION")
    print("=" * 70)
    result = runner.run(suite)
    
    print("\n" + "=" * 70)
    if result.wasSuccessful():
        print(f"✅ ALL {result.testsRun} TESTS PASSED! GATES ARE GREEN.")
    else:
        print(f"❌ {len(result.failures)} FAILURES, {len(result.errors)} ERRORS out of {result.testsRun} tests.")
    print("=" * 70)

    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(run_tests())
