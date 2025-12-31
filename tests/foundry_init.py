"""
Foundry initialization script for pytest.

Ensures backend is running and Foundry is connected before tests.
If not connected, starts backend and opens Foundry in Chrome.
"""

import os
import subprocess
import time
from pathlib import Path

import httpx


# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
FOUNDRY_URL = os.getenv("FOUNDRY_URL", "http://localhost:30000")
BACKEND_STARTUP_TIMEOUT = 30  # seconds
FOUNDRY_CONNECTION_TIMEOUT = 60  # seconds to wait for Foundry module connection


def check_backend_health() -> bool:
    """Check if backend is running and healthy."""
    try:
        response = httpx.get(f"{BACKEND_URL}/health", timeout=5.0)
        return response.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


def check_foundry_connected() -> tuple[bool, int]:
    """
    Check if Foundry is connected via WebSocket.

    Returns:
        Tuple of (is_connected, connected_clients_count)
    """
    try:
        response = httpx.get(f"{BACKEND_URL}/api/foundry/status", timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            is_connected = data.get("status") == "connected"
            client_count = data.get("connected_clients", 0)
            return is_connected and client_count > 0, client_count
        return False, 0
    except (httpx.ConnectError, httpx.TimeoutException):
        return False, 0


def start_backend() -> subprocess.Popen | None:
    """
    Start the backend server in the background.

    Returns:
        Popen process or None if already running
    """
    if check_backend_health():
        print(f"  Backend already running at {BACKEND_URL}")
        return None

    print(f"  Starting backend at {BACKEND_URL}...")

    # Find the backend directory
    project_root = Path(__file__).parent.parent
    backend_dir = project_root / "ui" / "backend"

    # Start uvicorn in background
    process = subprocess.Popen(
        ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
        cwd=backend_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Wait for backend to be ready
    start_time = time.time()
    while time.time() - start_time < BACKEND_STARTUP_TIMEOUT:
        if check_backend_health():
            print(f"  Backend started successfully (PID: {process.pid})")
            return process
        time.sleep(0.5)

    print(f"  WARNING: Backend did not start within {BACKEND_STARTUP_TIMEOUT}s")
    process.terminate()
    return None


def open_foundry_in_chrome() -> bool:
    """
    Open Foundry URL in Chrome (macOS only).

    Returns:
        True if command succeeded
    """
    print(f"  Opening Foundry in Chrome: {FOUNDRY_URL}")
    try:
        subprocess.run(
            ["open", "-a", "Google Chrome", FOUNDRY_URL],
            check=True,
            timeout=10
        )
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"  WARNING: Failed to open Chrome: {e}")
        return False


def refresh_chrome_foundry() -> bool:
    """
    Refresh Foundry tab in Chrome using AppleScript (macOS only).

    Returns:
        True if refresh succeeded
    """
    print(f"  Refreshing Foundry tab in Chrome...")

    # AppleScript to find and refresh tab with Foundry URL
    script = f'''
    tell application "Google Chrome"
        set foundTab to missing value
        repeat with w in windows
            repeat with t in tabs of w
                if URL of t contains "localhost:30000" then
                    set foundTab to t
                    exit repeat
                end if
            end repeat
            if foundTab is not missing value then exit repeat
        end repeat

        if foundTab is not missing value then
            tell foundTab to reload
            return "refreshed"
        else
            return "not_found"
        end if
    end tell
    '''

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            output = result.stdout.strip()
            if output == "refreshed":
                print("  Foundry tab refreshed")
                return True
            else:
                print("  Foundry tab not found in Chrome, opening new tab...")
                return open_foundry_in_chrome()
        return False
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"  WARNING: Failed to refresh Chrome: {e}")
        return False


def wait_for_foundry_connection(timeout: int = FOUNDRY_CONNECTION_TIMEOUT) -> bool:
    """
    Wait for Foundry module to connect via WebSocket.

    Args:
        timeout: Maximum seconds to wait

    Returns:
        True if connected within timeout
    """
    print(f"  Waiting for Foundry WebSocket connection (up to {timeout}s)...")
    start_time = time.time()
    last_status = ""

    while time.time() - start_time < timeout:
        is_connected, client_count = check_foundry_connected()

        # Print status updates
        elapsed = int(time.time() - start_time)
        status = f"connected={is_connected}, clients={client_count}"
        if status != last_status:
            print(f"    [{elapsed}s] {status}")
            last_status = status

        if is_connected:
            print(f"  Foundry connected with {client_count} client(s)")
            return True

        time.sleep(2)

    print(f"  WARNING: Foundry did not connect within {timeout}s")
    return False


def ensure_foundry_ready(force_refresh: bool = False) -> dict:
    """
    Main initialization function. Ensures Foundry is ready for testing.

    Steps:
    1. Check if backend is running, start if not
    2. Check if Foundry is connected
    3. If not connected OR force_refresh: open/refresh Chrome with Foundry URL
    4. Wait for Foundry module to connect

    Args:
        force_refresh: If True, always refresh Foundry even if already connected.
                       Useful when module code has been updated.

    Returns:
        Dict with status info:
        - backend_running: bool
        - foundry_connected: bool
        - backend_process: Popen or None
        - error: str or None
    """
    print("\n" + "=" * 60)
    print("FOUNDRY INITIALIZATION" + (" (FORCE REFRESH)" if force_refresh else ""))
    print("=" * 60)

    result = {
        "backend_running": False,
        "foundry_connected": False,
        "backend_process": None,
        "error": None,
    }

    # Step 1: Ensure backend is running
    print("\n[1/3] Checking backend...")
    backend_process = start_backend()
    result["backend_process"] = backend_process

    if not check_backend_health():
        result["error"] = "Backend failed to start"
        print(f"\n  ERROR: {result['error']}")
        return result

    result["backend_running"] = True
    print("  Backend is healthy")

    # Step 2: Check Foundry connection
    print("\n[2/3] Checking Foundry connection...")
    is_connected, client_count = check_foundry_connected()

    if is_connected and not force_refresh:
        print(f"  Foundry already connected ({client_count} clients)")
        result["foundry_connected"] = True
        print("\n" + "=" * 60)
        print("FOUNDRY READY")
        print("=" * 60 + "\n")
        return result

    # Step 3: Not connected OR force_refresh - open/refresh Chrome
    if force_refresh and is_connected:
        print(f"\n[3/3] Force refreshing Foundry ({client_count} clients connected)...")
    else:
        print("\n[3/3] Foundry not connected. Opening Chrome...")

    # Try to refresh existing tab first, or open new one
    refresh_chrome_foundry()

    # Wait for connection
    if wait_for_foundry_connection():
        result["foundry_connected"] = True
        print("\n" + "=" * 60)
        print("FOUNDRY READY")
        print("=" * 60 + "\n")
    else:
        result["error"] = "Foundry module did not connect. Please ensure Tablewrite Assistant module is enabled in FoundryVTT."
        print(f"\n  ERROR: {result['error']}")

    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Initialize Foundry for testing")
    parser.add_argument(
        "--force-refresh", "-f",
        action="store_true",
        help="Force refresh Foundry even if already connected (reloads module code)"
    )
    args = parser.parse_args()

    result = ensure_foundry_ready(force_refresh=args.force_refresh)
    print(f"\nResult: {result}")

    if result["error"]:
        print(f"\nFailed: {result['error']}")
        exit(1)
    else:
        print("\nSuccess! Foundry is ready for testing.")
