#!/usr/bin/env python3
"""
Verify battle map upload UI is working correctly.

Usage:
    python verify_battlemap_upload.py [--headed] [--map PATH]

Requires:
- Backend running at localhost:8000
- FoundryVTT running at localhost:30000
- Tablewrite module enabled

Screenshots saved to: /tmp/battlemap_upload/
"""

import argparse
import time
from pathlib import Path
from foundry_helper import FoundrySession

DEFAULT_MAP = Path(__file__).resolve().parent.parent.parent.parent.parent / "tests/scenes/fixtures/gridded_map.webp"
SCREENSHOT_DIR = Path("/tmp/battlemap_upload")


def verify_battlemap_upload(map_path: Path, headless: bool = True):
    """Run through the battle map upload flow and capture screenshots."""
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    results = {"success": False, "screenshots": [], "error": None}

    print(f"\n{'='*60}")
    print("BATTLE MAP UPLOAD VERIFICATION")
    print(f"{'='*60}")
    print(f"Map: {map_path}")
    print(f"Screenshots: {SCREENSHOT_DIR}")
    print(f"{'='*60}\n")

    with FoundrySession(headless=headless) as session:
        page = session.page

        try:
            # Step 1: Go to Tablewrite tab
            print("[1/7] Opening Tablewrite tab...")
            session.goto_tablewrite()
            time.sleep(0.5)
            shot = SCREENSHOT_DIR / "01_tablewrite_tab.png"
            page.locator("#sidebar").screenshot(path=str(shot))
            results["screenshots"].append(str(shot))
            print(f"      Screenshot: {shot}")

            # Step 2: Click Battle Map sub-tab
            print("[2/7] Switching to Battle Map tab...")
            battlemap_btn = page.locator('.tab-btn:has-text("Battle Map")')
            if battlemap_btn.count() == 0:
                raise Exception("Battle Map tab not found - is the UI implemented?")
            battlemap_btn.click()
            time.sleep(0.5)
            shot = SCREENSHOT_DIR / "02_battlemap_form.png"
            page.locator("#sidebar").screenshot(path=str(shot))
            results["screenshots"].append(str(shot))
            print(f"      Screenshot: {shot}")

            # Step 3: Upload map file
            print(f"[3/7] Uploading map: {map_path.name}...")
            file_input = page.locator('#battlemap-file')
            file_input.set_input_files(str(map_path))
            time.sleep(0.3)
            page.locator('#scene-name').fill("Verification Test Scene")
            shot = SCREENSHOT_DIR / "03_file_selected.png"
            page.locator("#sidebar").screenshot(path=str(shot))
            results["screenshots"].append(str(shot))
            print(f"      Screenshot: {shot}")

            # Step 4: Click Create Scene
            print("[4/7] Creating scene (this may take 60-90 seconds)...")
            page.locator('#create-scene-btn').click()
            time.sleep(1)
            shot = SCREENSHOT_DIR / "04_progress.png"
            page.locator("#sidebar").screenshot(path=str(shot))
            results["screenshots"].append(str(shot))
            print(f"      Screenshot: {shot}")

            # Step 5: Wait for completion
            print("      Waiting for wall detection...")
            start = time.time()
            result_container = page.locator('.result-container')
            while time.time() - start < 120:
                if result_container.count() > 0 and result_container.is_visible():
                    break
                time.sleep(2)
                elapsed = int(time.time() - start)
                print(f"      [{elapsed}s] Still processing...")

            if not result_container.is_visible():
                raise Exception("Timeout waiting for scene creation (120s)")

            # Step 6: Capture success
            print("[5/7] Scene created! Capturing result...")
            shot = SCREENSHOT_DIR / "05_scene_created.png"
            page.locator("#sidebar").screenshot(path=str(shot))
            results["screenshots"].append(str(shot))
            print(f"      Screenshot: {shot}")

            success_msg = page.locator('.success-message').text_content()
            print(f"      Result: {success_msg}")
            results["result_text"] = success_msg

            # Step 7: Open scene and capture with walls
            print("[6/7] Opening scene to view walls...")
            page.locator('#open-scene-btn').click()
            time.sleep(3)
            shot = SCREENSHOT_DIR / "06_scene_with_walls.png"
            page.screenshot(path=str(shot), full_page=True)
            results["screenshots"].append(str(shot))
            print(f"      Screenshot: {shot}")

            # Verify in scenes list
            print("[7/7] Verifying scene in scenes list...")
            page.locator('a[data-tab="scenes"]').click()
            time.sleep(0.5)
            shot = SCREENSHOT_DIR / "07_scenes_list.png"
            page.locator("#sidebar").screenshot(path=str(shot))
            results["screenshots"].append(str(shot))
            print(f"      Screenshot: {shot}")

            results["success"] = True
            print(f"\n{'='*60}")
            print("VERIFICATION PASSED")
            print(f"{'='*60}")
            print(f"Screenshots saved to: {SCREENSHOT_DIR}")
            print(f"Final scene: {SCREENSHOT_DIR / '06_scene_with_walls.png'}")

        except Exception as e:
            results["error"] = str(e)
            print(f"\nVERIFICATION FAILED: {e}")
            shot = SCREENSHOT_DIR / "error_state.png"
            page.screenshot(path=str(shot), full_page=True)
            results["screenshots"].append(str(shot))
            print(f"Error screenshot: {shot}")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify battle map upload UI")
    parser.add_argument("--headed", action="store_true", help="Run with visible browser")
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP, help="Path to test map")
    args = parser.parse_args()

    if not args.map.exists():
        print(f"Error: Map not found: {args.map}")
        exit(1)

    results = verify_battlemap_upload(args.map, headless=not args.headed)
    exit(0 if results["success"] else 1)
