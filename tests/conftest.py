"""
Shared pytest fixtures for D&D Module Converter tests.
"""

import os
import shutil
import sys
import time
from datetime import datetime
import pytest
from pathlib import Path

from tests.foundry_init import ensure_foundry_ready as _ensure_foundry_ready

# Store session timing information
_session_start_time = None


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--skip-foundry-init",
        action="store_true",
        default=False,
        help="Skip Foundry initialization (useful for unit tests only)"
    )
    parser.addoption(
        "--full",
        action="store_true",
        default=False,
        help="Run full test suite (skip smoke-only mode)"
    )


def pytest_configure(config):
    """Configure test run based on flags"""
    is_ci = os.getenv("CI", "").lower() == "true"

    if config.getoption("--full"):
        # Only clear default marker if no explicit -m flag was provided
        # Check if markexpr is the default from pytest.ini
        if config.option.markexpr == "smoke":
            config.option.markexpr = ""  # Run all tests

    # In CI, run non-integration tests (most smoke tests require Foundry)
    if is_ci:
        config.option.markexpr = "not integration and not slow"
        print(f"\n[CI] Running non-integration tests")


def pytest_sessionstart(session):
    """Log test session start time."""
    global _session_start_time
    _session_start_time = time.time()
    start_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Get worker info if running with xdist
    worker_id = os.environ.get("PYTEST_XDIST_WORKER", "main")

    if worker_id == "main":
        print(f"\n{'='*70}")
        print(f"TEST SESSION START: {start_str}")
        print(f"{'='*70}")


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Store test outcomes on items for later inspection."""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


def pytest_sessionfinish(session, exitstatus):
    """Log session end time and auto-escalate to full suite if smoke tests fail."""
    global _session_start_time

    # Log session end time (only on main process)
    worker_id = os.environ.get("PYTEST_XDIST_WORKER", "main")
    if worker_id == "main" and _session_start_time:
        end_time = time.time()
        duration = end_time - _session_start_time
        end_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Format duration nicely
        minutes, seconds = divmod(int(duration), 60)
        if minutes > 0:
            duration_str = f"{minutes}m {seconds}s"
        else:
            duration_str = f"{duration:.1f}s"

        print(f"\n{'='*70}")
        print(f"TEST SESSION END: {end_str}")
        print(f"TOTAL DURATION: {duration_str}")
        print(f"{'='*70}")

    # Check if auto-escalation is enabled (default: enabled, but shows errors first)
    auto_escalate = os.getenv("AUTO_ESCALATE", "true").lower() == "true"

    # Check if we're already running full suite or using default markers
    is_full_run = session.config.getoption("--full")
    is_default_markers = session.config.option.markexpr == "smoke"

    # Only escalate if a SMOKE test specifically failed
    if not is_full_run and is_default_markers and exitstatus != 0:
        # Collect failed smoke tests with their error details
        failed_smoke_tests = []
        for item in session.items:
            if item.get_closest_marker("smoke"):
                # Check if test failed and get the report
                report = None
                if hasattr(item, "rep_call") and item.rep_call.failed:
                    report = item.rep_call
                elif hasattr(item, "rep_setup") and item.rep_setup.failed:
                    report = item.rep_setup
                elif hasattr(item, "rep_teardown") and item.rep_teardown.failed:
                    report = item.rep_teardown

                if report:
                    failed_smoke_tests.append((item.nodeid, report))

        if failed_smoke_tests:
            # Print prominent failure summary with actual errors
            print("\n" + "="*70)
            print("SMOKE TEST FAILURE - ERRORS SHOWN BELOW")
            print("="*70)

            for nodeid, report in failed_smoke_tests:
                print(f"\n{'─'*70}")
                print(f"FAILED: {nodeid}")
                print(f"{'─'*70}")
                # Show the actual error/traceback
                if hasattr(report, 'longreprtext'):
                    # Limit to last 30 lines to keep it readable
                    lines = report.longreprtext.split('\n')
                    if len(lines) > 30:
                        print("... (truncated, showing last 30 lines)")
                        print('\n'.join(lines[-30:]))
                    else:
                        print(report.longreprtext)

            print("\n" + "="*70)

            if auto_escalate:
                print("AUTO_ESCALATE=true: Running full test suite in 3 seconds...")
                print("(Set AUTO_ESCALATE=false to stop here)")
                print("="*70 + "\n")
                time.sleep(3)  # Give user time to see the error
                # Re-run pytest with full suite
                sys.exit(pytest.main(["--full"] + sys.argv[1:]))
            else:
                print("To run full test suite: pytest --full")
                print("To enable auto-escalation: AUTO_ESCALATE=true pytest")
                print("="*70)


# Store the initialization result at module level to avoid re-running
_foundry_init_result = None
_foundry_init_done = False


@pytest.fixture(scope="session", autouse=True)
def ensure_foundry_connected(request):
    """
    Session-scoped fixture that ensures Foundry is connected before tests run.

    Runs automatically for smoke and full test runs. Skipped when:
    - --skip-foundry-init flag is passed
    - Running only unit tests (no smoke/integration markers)
    - SKIP_FOUNDRY_INIT environment variable is set

    If Foundry is not connected, this fixture will:
    1. Start the backend if not running
    2. Open/refresh Chrome to Foundry URL
    3. Wait for Foundry module to connect via WebSocket
    """
    global _foundry_init_result, _foundry_init_done

    # Skip if already initialized this session
    if _foundry_init_done:
        if _foundry_init_result and _foundry_init_result.get("error"):
            pytest.fail(f"Foundry initialization failed: {_foundry_init_result['error']}")
        yield _foundry_init_result
        return

    # Check skip conditions - including CI environment
    is_ci = os.getenv("CI", "").lower() == "true"
    skip_init = (
        request.config.getoption("--skip-foundry-init", default=False)
        or os.getenv("SKIP_FOUNDRY_INIT", "").lower() == "true"
        or is_ci  # Always skip in CI - no Foundry available
    )

    if skip_init:
        reason = "CI environment" if is_ci else "--skip-foundry-init or SKIP_FOUNDRY_INIT"
        print(f"\nSkipping Foundry initialization ({reason})")
        _foundry_init_done = True
        yield None
        return

    # Check if any tests require Foundry (smoke, integration, or requires_foundry markers)
    # or if running full suite
    is_full_run = request.config.getoption("--full", default=False)
    has_foundry_tests = False

    for item in request.session.items:
        if (item.get_closest_marker("smoke")
            or item.get_closest_marker("integration")
            or item.get_closest_marker("requires_foundry")):
            has_foundry_tests = True
            break

    if not is_full_run and not has_foundry_tests:
        print("\nNo smoke/integration/requires_foundry tests - skipping Foundry init")
        _foundry_init_done = True
        yield None
        return

    # Run initialization
    _foundry_init_result = _ensure_foundry_ready()
    _foundry_init_done = True

    # If initialization failed, FAIL the test session with clear error
    if _foundry_init_result.get("error"):
        error_msg = _foundry_init_result["error"]
        print("\n" + "=" * 70)
        print("FOUNDRY INITIALIZATION FAILED")
        print("=" * 70)
        print(f"\nError: {error_msg}")
        print("\nTo fix this issue:")
        print("  1. Ensure FoundryVTT is running at http://localhost:30000")
        print("  2. Enable the 'Tablewrite Assistant' module in FoundryVTT")
        print("  3. Refresh the FoundryVTT page in your browser")
        print("  4. Check that the backend is running: curl http://localhost:8000/health")
        print("\nTo skip Foundry initialization (unit tests only):")
        print("  uv run pytest --skip-foundry-init")
        print("  # or: SKIP_FOUNDRY_INIT=true uv run pytest")
        print("=" * 70 + "\n")

        pytest.fail(
            f"Foundry initialization failed: {error_msg}\n\n"
            "Possible causes:\n"
            "  - FoundryVTT is not running at http://localhost:30000\n"
            "  - Tablewrite Assistant module is not enabled in FoundryVTT\n"
            "  - Backend failed to start at http://localhost:8000\n"
            "  - WebSocket connection timed out (waited 60s)\n\n"
            "Run with --skip-foundry-init to skip Foundry tests."
        )

    yield _foundry_init_result

    # Cleanup: terminate backend if we started it
    if _foundry_init_result and _foundry_init_result.get("backend_process"):
        print("\nTerminating backend process started by test session...")
        _foundry_init_result["backend_process"].terminate()


@pytest.fixture(scope="session")
def foundry_status(ensure_foundry_connected):
    """
    Provides Foundry connection status for tests.

    Use this fixture in tests that need to check Foundry connectivity.
    """
    return ensure_foundry_connected


@pytest.fixture
def require_foundry(ensure_foundry_connected):
    """
    FAIL test if Foundry is not connected.

    Use this fixture in tests that require a live Foundry connection.
    Integration tests must FAIL (not skip) if Foundry is unavailable.
    """
    if not ensure_foundry_connected:
        pytest.fail("Foundry not connected - start backend and connect Foundry module")
    if ensure_foundry_connected.get("error"):
        pytest.fail(f"Foundry not available: {ensure_foundry_connected['error']} - start backend and connect Foundry module")
    if not ensure_foundry_connected.get("foundry_connected"):
        pytest.fail("Foundry is not connected - start backend and connect Foundry module")
    return ensure_foundry_connected


# Project root
PROJECT_ROOT = Path(__file__).parent.parent

# Test paths
TEST_PDF_PATH = PROJECT_ROOT / "data" / "pdfs" / "Lost_Mine_of_Phandelver_test.pdf"
FULL_PDF_PATH = PROJECT_ROOT / "data" / "pdfs" / "Lost_Mine_of_Phandelver.pdf"
TEST_OUTPUT_DIR = PROJECT_ROOT / "tests" / "output"
TEST_RUNS_DIR = PROJECT_ROOT / "tests" / "test_runs"


@pytest.fixture(scope="session")
def project_root():
    """Return the project root directory."""
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def test_pdf_path():
    """Return path to the test PDF file."""
    if not TEST_PDF_PATH.exists():
        pytest.skip(f"Test PDF not found: {TEST_PDF_PATH}")
    return TEST_PDF_PATH


@pytest.fixture(scope="session")
def full_pdf_path():
    """Return path to the full PDF file (for TOC tests)."""
    if not FULL_PDF_PATH.exists():
        pytest.skip(f"Full PDF not found: {FULL_PDF_PATH}")
    return FULL_PDF_PATH


@pytest.fixture(scope="function")
def test_output_dir(tmp_path):
    """
    Return a clean test output directory for each test.
    Uses pytest's tmp_path fixture which is automatically cleaned up.
    """
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


@pytest.fixture(scope="session")
def persistent_test_output_dir():
    """
    Return the persistent tests/output directory.
    This directory is NOT cleaned up automatically.
    """
    TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return TEST_OUTPUT_DIR


@pytest.fixture(scope="session")
def integration_test_output_dir():
    """
    Return a persistent output directory for integration tests.
    Creates a single timestamped directory under tests/test_runs/ for the
    entire test session to preserve artifacts for inspection.
    All tests in the session share this directory.
    """
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = TEST_RUNS_DIR / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


@pytest.fixture(scope="function")
def clean_test_output():
    """
    Clean the persistent tests/output directory before each test.
    Use this when you want to inspect output after test runs.
    """
    if TEST_OUTPUT_DIR.exists():
        shutil.rmtree(TEST_OUTPUT_DIR)
    TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    yield TEST_OUTPUT_DIR
    # Don't clean up after - keep for inspection


@pytest.fixture(scope="session")
def check_api_key():
    """Check if Gemini API key is available."""
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
    api_key = os.getenv("GeminiImageAPI")
    if not api_key:
        pytest.skip("Gemini API key not found. Set GeminiImageAPI in .env file.")
    return api_key


@pytest.fixture(scope="session")
def check_foundry_credentials():
    """Check if FoundryVTT backend connection is available."""
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")

    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")

    return {
        "backend_url": backend_url
    }


@pytest.fixture(scope="session")
def backend_url():
    """
    Get the backend URL from environment or use default.

    In Docker, this will be http://host.docker.internal:8000
    Locally, this will be http://localhost:8000

    Usage:
        def test_something(backend_url):
            response = httpx.get(f"{backend_url}/health")
    """
    return os.getenv("BACKEND_URL", "http://localhost:8000")


@pytest.fixture(scope="session")
def sample_xml_content():
    """Return sample XML content for testing."""
    return """<Chapter_01_Introduction>
    <page number="1">
        <section>Introduction</section>
        <p>This is a test paragraph with some **bold** text and *italic* text.</p>
        <list>
            <item>First item</item>
            <item>Second item</item>
        </list>
    </page>
</Chapter_01_Introduction>"""


@pytest.fixture(scope="session")
def sample_malformed_xml():
    """Return malformed XML for testing error handling."""
    return """<Chapter_01_Introduction>
    <page number="1">
        <heading>Introduction</heading>
        <paragraph>Unclosed paragraph
        <list>
            <item>First item
        </list>
    </page>"""
