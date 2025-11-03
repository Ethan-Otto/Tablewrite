#!/usr/bin/env python3
"""
Measure the failure rate of the weapon upload bug by running multiple trials.

This script runs the multiple actor test repeatedly and tracks:
- How often each actor configuration fails
- Total failure rate
- Patterns in which weapons are lost
"""

import sys
import subprocess
from pathlib import Path
from collections import defaultdict

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


def run_single_trial():
    """Run one trial and return results."""
    result = subprocess.run(
        ["uv", "run", "python", "scripts/test_multiple_actors.py"],
        cwd=project_root,
        capture_output=True,
        text=True
    )

    # Parse output
    output = result.stdout + result.stderr

    # Extract results for each actor
    actors = {
        "2_weapons": None,
        "3_weapons": None,
        "4_weapons": None
    }

    if "✓ PASS: Actor 1: Two Weapons" in output:
        actors["2_weapons"] = "pass"
    elif "✗ FAIL: Actor 1: Two Weapons" in output:
        actors["2_weapons"] = "fail"

    if "✓ PASS: Actor 2: Three Weapons" in output:
        actors["3_weapons"] = "pass"
    elif "✗ FAIL: Actor 2: Three Weapons" in output:
        actors["3_weapons"] = "fail"

    if "✓ PASS: Actor 3: Four Weapons" in output:
        actors["4_weapons"] = "pass"
    elif "✗ FAIL: Actor 3: Four Weapons" in output:
        actors["4_weapons"] = "fail"

    return actors


def main():
    num_trials = int(sys.argv[1]) if len(sys.argv) > 1 else 10

    print("=" * 70)
    print(f"FAILURE RATE MEASUREMENT - {num_trials} TRIALS")
    print("=" * 70)
    print()

    results = defaultdict(lambda: {"pass": 0, "fail": 0})

    for i in range(1, num_trials + 1):
        print(f"Running trial {i}/{num_trials}...", end=" ", flush=True)
        trial_results = run_single_trial()

        # Track results
        for actor_type, result in trial_results.items():
            if result:
                results[actor_type][result] += 1

        # Show inline status
        status_symbols = {
            "2_weapons": "✓" if trial_results["2_weapons"] == "pass" else "✗",
            "3_weapons": "✓" if trial_results["3_weapons"] == "pass" else "✗",
            "4_weapons": "✓" if trial_results["4_weapons"] == "pass" else "✗",
        }
        print(f"[2w:{status_symbols['2_weapons']} 3w:{status_symbols['3_weapons']} 4w:{status_symbols['4_weapons']}]")

    print()
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    print()

    for actor_type in ["2_weapons", "3_weapons", "4_weapons"]:
        total = results[actor_type]["pass"] + results[actor_type]["fail"]
        pass_count = results[actor_type]["pass"]
        fail_count = results[actor_type]["fail"]

        if total > 0:
            pass_rate = (pass_count / total) * 100
            fail_rate = (fail_count / total) * 100

            print(f"{actor_type.replace('_', ' ').title()}:")
            print(f"  Pass: {pass_count}/{total} ({pass_rate:.1f}%)")
            print(f"  Fail: {fail_count}/{total} ({fail_rate:.1f}%)")
            print()

    # Overall stats
    total_tests = sum(r["pass"] + r["fail"] for r in results.values())
    total_failures = sum(r["fail"] for r in results.values())
    total_passes = sum(r["pass"] for r in results.values())

    if total_tests > 0:
        overall_fail_rate = (total_failures / total_tests) * 100
        print(f"Overall:")
        print(f"  Total tests: {total_tests}")
        print(f"  Passed: {total_passes} ({100 - overall_fail_rate:.1f}%)")
        print(f"  Failed: {total_failures} ({overall_fail_rate:.1f}%)")

    print()
    print("=" * 70)


if __name__ == "__main__":
    main()
