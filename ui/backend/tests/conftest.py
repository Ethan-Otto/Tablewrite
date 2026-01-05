"""Pytest configuration for UI backend tests."""
import os
import sys
import pytest
from pathlib import Path
from dotenv import load_dotenv

# Add backend root to path so imports work
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

# Load env from project root for API keys
project_root = backend_root.parent.parent
load_dotenv(project_root / ".env")

# Add tests directory to path for foundry_init import
tests_dir = project_root / "tests"
sys.path.insert(0, str(tests_dir))


# Store the initialization result at module level to avoid re-running
_foundry_init_result = None
_foundry_init_done = False


@pytest.fixture(scope="session", autouse=True)
def ensure_foundry_connected(request):
    """
    Session-scoped fixture that ensures Foundry is connected for integration tests.

    Uses the same initialization as the main project tests.
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

    # Check if any tests require Foundry (integration, smoke, or requires_foundry markers)
    has_foundry_tests = False
    for item in request.session.items:
        if (item.get_closest_marker("smoke")
            or item.get_closest_marker("integration")
            or item.get_closest_marker("requires_foundry")):
            has_foundry_tests = True
            break

    if not has_foundry_tests:
        print("\nNo integration/smoke tests - skipping Foundry init")
        _foundry_init_done = True
        yield None
        return

    # Import and run initialization
    try:
        from foundry_init import ensure_foundry_ready
    except ImportError:
        print("\nCould not import foundry_init - Foundry tests may fail")
        _foundry_init_done = True
        yield None
        return

    _foundry_init_result = ensure_foundry_ready()
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
        print("\nTo skip Foundry initialization (unit tests only):")
        print("  SKIP_FOUNDRY_INIT=true uv run pytest")
        print("=" * 70 + "\n")

        pytest.fail(f"Foundry initialization failed: {error_msg}")

    yield _foundry_init_result

    # Cleanup: terminate backend if we started it
    if _foundry_init_result and _foundry_init_result.get("backend_process"):
        print("\nTerminating backend process started by test session...")
        _foundry_init_result["backend_process"].terminate()


@pytest.fixture(autouse=True)
def disable_actor_image_generation():
    """Disable image generation for actor creation in all tests."""
    from app.tools.actor_creator import set_image_generation_enabled
    set_image_generation_enabled(False)
    yield
    set_image_generation_enabled(True)


# Cache for test folder IDs to avoid repeated creation attempts
_test_folder_ids = {}


@pytest.fixture(scope="session")
def test_folders(ensure_foundry_connected):
    """
    Session-scoped fixture that ensures /tests folders exist for each document type.

    Creates folders for: Actor, Scene, JournalEntry

    Returns a dict mapping document type to folder ID.
    """
    global _test_folder_ids

    if _test_folder_ids:
        return _test_folder_ids

    # Skip if Foundry isn't connected
    if not ensure_foundry_connected:
        return {}

    import httpx
    import asyncio

    async def create_test_folders():
        folder_types = ["Actor", "Scene", "JournalEntry"]
        folder_ids = {}

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Check if connected
            status = await client.get("http://localhost:8000/api/foundry/status")
            if status.json().get("status") != "connected":
                return {}

            for folder_type in folder_types:
                response = await client.post(
                    "http://localhost:8000/api/foundry/folder",
                    json={"name": "tests", "type": folder_type}
                )
                if response.status_code == 200:
                    data = response.json()
                    folder_ids[folder_type] = data.get("folder_id")
                    print(f"[TEST SETUP] Created/found {folder_type} tests folder: {data.get('folder_id')}")

        return folder_ids

    try:
        _test_folder_ids = asyncio.get_event_loop().run_until_complete(create_test_folders())
    except RuntimeError:
        # No event loop - create one
        _test_folder_ids = asyncio.run(create_test_folders())

    return _test_folder_ids


async def get_or_create_test_folder(folder_type: str) -> str:
    """
    Helper to get or create a /tests folder for a given document type.

    Args:
        folder_type: "Actor", "Scene", or "JournalEntry"

    Returns:
        Folder ID string
    """
    import httpx

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "http://localhost:8000/api/foundry/folder",
            json={"name": "tests", "type": folder_type}
        )
        if response.status_code == 200:
            return response.json().get("folder_id")
    return None


# Alias for backwards compatibility with existing tests
get_or_create_tests_folder = get_or_create_test_folder


async def check_backend_and_foundry():
    """
    Check backend health and Foundry connection.

    Raises assertion errors with helpful messages if:
    - Backend is not running on localhost:8000
    - Foundry is not connected via WebSocket
    """
    import httpx

    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")

    async with httpx.AsyncClient() as client:
        try:
            health = await client.get(f"{backend_url}/health")
            assert health.status_code == 200, \
                "Backend not running - start with: cd ui/backend && uvicorn app.main:app --reload"
        except httpx.ConnectError:
            pytest.fail("Backend not running - start with: cd ui/backend && uvicorn app.main:app --reload")

        status = await client.get(f"{backend_url}/api/foundry/status")
        status_data = status.json()
        assert status_data.get("connected_clients", 0) > 0, \
            "Foundry not connected - ensure Tablewrite module is enabled"
