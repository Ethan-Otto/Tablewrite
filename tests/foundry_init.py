"""
Foundry initialization script for pytest.

Ensures backend is running and Foundry is connected before tests.
If not connected, starts backend and opens Foundry in Chrome.

Key features:
- Kills stuck backend processes before starting new ones
- Health checks with retries (not just port checks)
- Stores PID for cleanup
- Auto-restarts if backend becomes unresponsive
"""

import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Optional, List

import httpx


# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
FOUNDRY_URL = os.getenv("FOUNDRY_URL", "http://localhost:30000")
BACKEND_STARTUP_TIMEOUT = 30  # seconds
FOUNDRY_CONNECTION_TIMEOUT = 60  # seconds to wait for Foundry module connection
HEALTH_CHECK_TIMEOUT = 3.0  # seconds per health check request
HEALTH_CHECK_RETRIES = 3  # number of retries for health checks


def find_backend_pids() -> List[int]:
    """Find PIDs of any running uvicorn backend processes on port 8000."""
    pids = []
    try:
        result = subprocess.run(
            ["lsof", "-t", "-i", ":8000"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            pids = [int(pid) for pid in result.stdout.strip().split('\n') if pid]
    except (subprocess.TimeoutExpired, ValueError, FileNotFoundError):
        pass
    return pids


def kill_stuck_backends() -> int:
    """Kill any stuck backend processes on port 8000. Returns count killed."""
    pids = find_backend_pids()
    killed = 0
    for pid in pids:
        try:
            os.kill(pid, signal.SIGKILL)
            killed += 1
            print(f"  Killed stuck process PID {pid}")
        except (ProcessLookupError, PermissionError):
            pass
    if killed:
        time.sleep(1)  # Give OS time to release port
    return killed


def check_backend_health(retries: int = HEALTH_CHECK_RETRIES) -> bool:
    """
    Check if backend is running and responsive.

    Uses retries to handle transient failures.
    """
    for attempt in range(retries):
        try:
            response = httpx.get(
                f"{BACKEND_URL}/health",
                timeout=HEALTH_CHECK_TIMEOUT
            )
            if response.status_code == 200:
                return True
        except (httpx.ConnectError, httpx.TimeoutException, httpx.ReadTimeout):
            if attempt < retries - 1:
                time.sleep(0.5)
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


def start_backend(kill_existing: bool = True) -> subprocess.Popen | None:
    """
    Start the backend server in the background.

    Args:
        kill_existing: If True, kill any stuck processes on port 8000 first

    Returns:
        Popen process or None if already running (and healthy)
    """
    # First check if backend is already running AND responsive
    if check_backend_health():
        print(f"  Backend already running and healthy at {BACKEND_URL}")
        return None

    # Kill stuck processes if requested
    if kill_existing:
        pids = find_backend_pids()
        if pids:
            print(f"  Found {len(pids)} process(es) on port 8000 but not responding")
            killed = kill_stuck_backends()
            if killed:
                print(f"  Killed {killed} stuck process(es)")

    print(f"  Starting backend at {BACKEND_URL}...")

    # Find the backend directory
    project_root = Path(__file__).parent.parent
    backend_dir = project_root / "ui" / "backend"

    # Start uvicorn in background with output captured for debugging
    log_file = project_root / "tests" / "output" / "backend.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    with open(log_file, "w") as log:
        process = subprocess.Popen(
            ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
            cwd=backend_dir,
            stdout=log,
            stderr=subprocess.STDOUT,
        )

    # Wait for backend to be ready with progress indication
    start_time = time.time()
    last_dot = start_time
    while time.time() - start_time < BACKEND_STARTUP_TIMEOUT:
        if check_backend_health(retries=1):
            print(f"\n  Backend started successfully (PID: {process.pid})")
            print(f"  Log file: {log_file}")
            return process

        # Print dots to show progress
        if time.time() - last_dot >= 2:
            print(".", end="", flush=True)
            last_dot = time.time()

        time.sleep(0.5)

    print(f"\n  WARNING: Backend did not start within {BACKEND_STARTUP_TIMEOUT}s")
    print(f"  Check log file for errors: {log_file}")
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


def verify_backend_responsive() -> bool:
    """
    Quick health check to verify backend is still responsive.

    Use this mid-test to check if backend has become stuck.
    If unresponsive, will attempt to restart.

    Returns:
        True if backend is responsive, False if restart failed
    """
    if check_backend_health():
        return True

    print("\n  ⚠️  Backend became unresponsive, attempting restart...")
    process = start_backend(kill_existing=True)

    if process or check_backend_health():
        # Need to reconnect Foundry after restart
        print("  Backend restarted, waiting for Foundry reconnection...")
        wait_for_foundry_connection(timeout=30)
        return check_backend_health()

    return False


def get_backend_pid() -> Optional[int]:
    """Get the PID of the running backend, if any."""
    pids = find_backend_pids()
    return pids[0] if pids else None


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Initialize Foundry for testing")
    parser.add_argument(
        "--force-refresh", "-f",
        action="store_true",
        help="Force refresh Foundry even if already connected (reloads module code)"
    )
    parser.add_argument(
        "--kill-stuck",
        action="store_true",
        help="Kill any stuck backend processes before starting"
    )
    args = parser.parse_args()

    if args.kill_stuck:
        killed = kill_stuck_backends()
        if killed:
            print(f"Killed {killed} stuck process(es)")
        else:
            print("No stuck processes found")

    result = ensure_foundry_ready(force_refresh=args.force_refresh)
    print(f"\nResult: {result}")

    if result["error"]:
        print(f"\nFailed: {result['error']}")
        exit(1)
    else:
        pid = get_backend_pid()
        print(f"\nSuccess! Foundry is ready for testing.")
        if pid:
            print(f"Backend PID: {pid}")
