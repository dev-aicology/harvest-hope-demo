"""Optional real-browser synthetic workflow smoke test.

Start an isolated demo server first, then run:
    python tests/ui_smoke.py --base-url http://127.0.0.1:8000

Requires the optional Playwright Python package and Chromium. This script is
deliberately not collected by unittest; the main suite has no browser dependency.
It creates one synthetic receipt in the supplied server. Never point it at a
real operational system.
"""
import argparse
import json
from pathlib import Path
import shutil
import tempfile
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright, expect


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--browser-executable", default=shutil.which("chromium"))
    parser.add_argument("--screenshot-dir")
    args = parser.parse_args()
    origin = urlparse(args.base_url)
    if origin.hostname not in {"127.0.0.1", "localhost", "::1"}:
        parser.error("Only a loopback demo URL is permitted.")
    screenshot_dir = Path(args.screenshot_dir) if args.screenshot_dir else None
    if screenshot_dir:
        screenshot_dir.mkdir(parents=True, exist_ok=True)
    errors = []
    external_requests = []
    with sync_playwright() as playwright:
        options = {"headless": True}
        if args.browser_executable:
            options["executable_path"] = args.browser_executable
        browser = playwright.chromium.launch(**options)
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("request", lambda request: external_requests.append(request.url)
                if urlparse(request.url).hostname not in {origin.hostname, None} else None)
        page.goto(args.base_url, wait_until="networkidle")
        expect(page.get_by_role("button", name="Use demo example")).to_be_enabled()
        page.keyboard.press("Tab")
        expect(page.get_by_role("link", name="Skip to receipt")).to_be_focused()
        page.get_by_role("button", name="Use demo example").click()
        reference = page.locator("#delivery_ref").input_value()
        page.get_by_role("button", name="Suggest catalog item").click()
        expect(page.get_by_role("button", name="Use this item")).to_be_visible()
        page.get_by_role("button", name="Use this item").click()
        confirmation = page.locator('input[data-field="checked"]')
        expect(confirmation).not_to_be_checked()
        confirmation.check()
        page.get_by_role("button", name="Save draft", exact=True).click()
        expect(page.locator("#validation-list")).to_contain_text("Required record checks passed")

        fixture = Path(__file__).resolve().parents[1] / "data/synthetic/labels/demo-beans-case.png"
        page.locator("#photo-file").set_input_files(fixture)
        expect(page.locator("#photos img")).to_be_visible()
        expect(page.locator("#message")).to_contain_text("Supporting photo saved locally")
        if screenshot_dir:
            page.screenshot(path=str(screenshot_dir / "receiver-desktop.png"), full_page=True)

        page.get_by_role("button", name="Send for review").click()
        expect(page.locator("#receipt-status")).to_have_text("Needs review")
        page.locator("#identity").select_option("reviewer")
        expect(page.get_by_role("button", name="Approve receipt", exact=True)).to_be_visible()
        expect(page.locator("#supplier")).to_be_disabled()
        page.locator("#review-note").fill("Checked the synthetic receipt in a browser smoke test.")
        page.get_by_role("button", name="Approve receipt", exact=True).click()
        expect(page.locator("#receipt-status")).to_have_text("Approved")
        page.get_by_role("button", name="Create mock handoff").click()
        expect(page.locator("#receipt-status")).to_have_text("Mock handoff created")
        page.get_by_role("button", name="Test a mismatched response").click()
        expect(page.locator("#receipt-status")).to_have_text("Mock mismatch")
        page.get_by_role("button", name="Run mock comparison").click()
        expect(page.locator("#receipt-status")).to_have_text("Mock records match")
        page.get_by_role("button", name="View audit history").click()
        expect(page.locator("#audit-result")).to_contain_text("Audit hash chain verified")
        with page.expect_download() as download_info:
            page.get_by_role("button", name="Download JSON").click()
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "receipt.json"
            download_info.value.save_as(destination)
            exported = json.loads(destination.read_text())
            assert reference in json.dumps(exported), "Export must contain the delivery reference."

        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(150)
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "Mobile page has horizontal overflow."
        expect(page.locator("#receipt-title")).to_have_text(reference)
        if screenshot_dir:
            page.screenshot(path=str(screenshot_dir / "reviewer-mobile.png"), full_page=True)
        assert not errors, errors
        assert not external_requests, external_requests
        context.close()
        browser.close()
    print(json.dumps({"result": "passed", "delivery_ref": reference,
        "checks": ["keyboard skip link", "explicit suggestion acceptance", "staff check", "save",
                   "photo upload", "submit", "reviewer approval", "mock handoff", "mismatch detection",
                   "mock reconciliation", "audit verification", "JSON download", "390px mobile overflow",
                   "no browser errors", "no external requests"]}, indent=2))


if __name__ == "__main__":
    main()
