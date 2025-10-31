"""Test segmentation reliability across different temperature values."""
import asyncio
import sys
from pathlib import Path
from benchmark_segmentation import main as run_single_test, TEST_CASES_DIR


async def main():
    """Run tests for temperatures from 0.0 to 1.0 in 0.1 increments."""
    # Get available test cases
    test_cases = [d.name for d in TEST_CASES_DIR.iterdir() if d.is_dir()]

    print("=" * 70)
    print("TEMPERATURE SWEEP TEST")
    print("=" * 70)
    print(f"Test cases: {', '.join(test_cases)}")
    print("Testing temperatures: 0.0, 0.1, 0.2, ..., 1.0")
    print("10 attempts per temperature per test case")
    print()

    temperatures = [round(t * 0.1, 1) for t in range(11)]  # 0.0 to 1.0 in 0.1 increments

    # Store results by test case
    all_results = {test_case: [] for test_case in test_cases}

    for test_case in test_cases:
        print(f"\n{'=' * 70}")
        print(f"TEST CASE: {test_case}")
        print(f"{'=' * 70}")

        for temp in temperatures:
            print(f"\nTesting temperature: {temp}")

            try:
                result = await run_single_test(test_case=test_case, temperature=temp)
                all_results[test_case].append(result)
            except Exception as e:
                print(f"Error testing temperature {temp}: {e}")
                all_results[test_case].append({
                    "test_case": test_case,
                    "temperature": temp,
                    "error": str(e)
                })

    # Print individual test case summaries
    for test_case in test_cases:
        print("\n\n" + "=" * 70)
        print(f"SUMMARY: {test_case.upper()}")
        print("=" * 70)
        print()
        print(f"{'Temp':>6} | {'Success':>7} | {'Failed':>6} | {'Success %':>10} | {'Good':>4} | {'Bad':>4} | {'Quality %':>10}")
        print("-" * 70)

        results = all_results[test_case]
        for result in results:
            if "error" in result:
                print(f"{result['temperature']:>6.1f} | ERROR: {result['error']}")
            else:
                temp = result['temperature']
                successful = result['successful']
                failed = result['failed']
                success_rate = result['success_rate']
                good = result['good_quality']
                bad = result['bad_quality']
                quality_rate = result['quality_rate']

                print(f"{temp:>6.1f} | {successful:>7} | {failed:>6} | {success_rate:>9.1f}% | {good:>4} | {bad:>4} | {quality_rate:>9.1f}%")

        print()

        # Find best temperature for this test case
        valid_results = [r for r in results if "error" not in r and r['successful'] > 0]

        if valid_results:
            best_quality = max(valid_results, key=lambda r: r['quality_rate'])
            best_success = max(valid_results, key=lambda r: r['success_rate'])

            print(f"Best quality rate:  Temperature {best_quality['temperature']} ({best_quality['quality_rate']:.1f}%)")
            print(f"Best success rate:  Temperature {best_success['temperature']} ({best_success['success_rate']:.1f}%)")

    # Print combined summary
    print("\n\n" + "=" * 70)
    print("COMBINED SUMMARY (ALL TEST CASES)")
    print("=" * 70)
    print()
    print(f"{'Temp':>6} | {'Success':>7} | {'Failed':>6} | {'Success %':>10} | {'Good':>4} | {'Bad':>4} | {'Quality %':>10}")
    print("-" * 70)

    for temp in temperatures:
        # Aggregate across all test cases for this temperature
        total_successful = 0
        total_failed = 0
        total_good = 0
        total_bad = 0
        has_error = False

        for test_case in test_cases:
            results = all_results[test_case]
            result = next((r for r in results if r.get('temperature') == temp), None)
            if result and "error" not in result:
                total_successful += result['successful']
                total_failed += result['failed']
                total_good += result['good_quality']
                total_bad += result['bad_quality']
            elif result:
                has_error = True

        if has_error:
            print(f"{temp:>6.1f} | ERROR")
        else:
            total_attempts = total_successful + total_failed
            success_rate = (total_successful / total_attempts * 100) if total_attempts > 0 else 0
            quality_rate = (total_good / total_successful * 100) if total_successful > 0 else 0

            print(f"{temp:>6.1f} | {total_successful:>7} | {total_failed:>6} | {success_rate:>9.1f}% | {total_good:>4} | {total_bad:>4} | {quality_rate:>9.1f}%")

    print()

    # Find best overall temperature
    combined_results = []
    for temp in temperatures:
        total_successful = 0
        total_failed = 0
        total_good = 0
        total_bad = 0

        for test_case in test_cases:
            results = all_results[test_case]
            result = next((r for r in results if r.get('temperature') == temp), None)
            if result and "error" not in result:
                total_successful += result['successful']
                total_failed += result['failed']
                total_good += result['good_quality']
                total_bad += result['bad_quality']

        if total_successful > 0:
            total_attempts = total_successful + total_failed
            combined_results.append({
                'temperature': temp,
                'success_rate': (total_successful / total_attempts * 100),
                'quality_rate': (total_good / total_successful * 100)
            })

    if combined_results:
        best_quality = max(combined_results, key=lambda r: r['quality_rate'])
        best_success = max(combined_results, key=lambda r: r['success_rate'])

        print(f"Best combined quality rate:  Temperature {best_quality['temperature']} ({best_quality['quality_rate']:.1f}%)")
        print(f"Best combined success rate:  Temperature {best_success['temperature']} ({best_success['success_rate']:.1f}%)")
        print()


if __name__ == "__main__":
    asyncio.run(main())
