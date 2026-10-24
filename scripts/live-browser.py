#!/usr/bin/env python3
"""Exercise the clean bench through its public and authenticated web UI."""
import json
import os
import pathlib
import re
import urllib.error
import urllib.parse
import urllib.request

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROOF = pathlib.Path(os.environ.get("HELIOS_PROOF_ROOT", ROOT / "proof"))
runtime_path = PROOF / "live/seed-runtime.json"
meta = json.loads((runtime_path if runtime_path.exists() else PROOF / "live/seed-metadata.json").read_text())
base = "http://127.0.0.1:8000"
COMPANY = meta["company"]
CONFIRM_DATE = meta["confirm_date"]
# Runtime pages are what real suppliers and customers open: no demo, sample
# or test wording may reach them.
FORBIDDEN = re.compile(r"fictional|sample|review surface|proof|demo", re.I)


def request(path, data=None):
    body = None if data is None else urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(base + path, data=body, method="POST" if body else "GET")
    with urllib.request.urlopen(req) as response:
        return response.status, response.headers, response.read().decode()


def anonymous_status(path):
    try:
        request(path)
    except urllib.error.HTTPError as exc:
        return exc.code
    return 200


def guest_state(token):
    status, _headers, body = request("/api/method/helios_order_visibility.api.get_supplier_confirmation?token=" + urllib.parse.quote(token))
    assert status == 200
    return json.loads(body)["message"]


def check_runtime_page(page, name):
    text = page.locator("body").inner_text()
    assert COMPANY in text, (name, "company name missing", text[:500])
    assert meta["today_display"] in text, (name, "site-local today missing", text[:500])
    assert not FORBIDDEN.search(text), (name, FORBIDDEN.search(text).group(0), text[:2000])
    return text


supplier_url = base + "/helios/confirm?token=" + urllib.parse.quote(meta["supplier_token"])
late_url = base + "/helios/confirm?token=" + urllib.parse.quote(meta["late_token"])
tracking_url = base + "/helios/track?token=" + urllib.parse.quote(meta["customer_token"])

# The reports are authenticated: an anonymous request must not disclose
# supplier, item or schedule data.
anonymous_otd = anonymous_status("/helios/otd")
assert anonymous_otd == 403

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True, executable_path="/usr/bin/chromium", args=["--no-sandbox"])
    context = browser.new_context(viewport={"width": 1280, "height": 720}, device_scale_factor=1)
    page = context.new_page()

    response = page.goto(supplier_url, wait_until="networkidle")
    assert response.headers.get("x-from-cache", "False") == "False"
    text = check_runtime_page(page, "supplier")
    assert "PO-1042" in text and page.locator("form").count() == 1
    page.screenshot(path=str(PROOF / "screenshots/supplier-confirmation-1280.png"), full_page=True)
    page.set_viewport_size({"width": 390, "height": 844})
    page.screenshot(path=str(PROOF / "screenshots/supplier-confirmation-390.png"), full_page=True)

    # A second signed link must render its own PO, not a cached copy of the
    # first page (Frappe's website cache is keyed by path only).
    page.goto(late_url, wait_until="networkidle")
    late_text = page.locator("body").inner_text()
    assert "PO-1043" in late_text and "PO-1042" not in late_text, late_text[:500]

    # Submit the real guest form. The writeback must come from this UI POST.
    page.set_viewport_size({"width": 1280, "height": 720})
    page.goto(supplier_url, wait_until="networkidle")
    page.locator('select[name="confirmed"]').select_option("true")
    page.locator('input[name="schedule_date"]').fill(CONFIRM_DATE)
    page.locator('textarea[name="note"]').fill("Ships in two boxes.")
    page.locator('button[type="submit"]').click()
    page.wait_for_load_state("networkidle")
    post_text = check_runtime_page(page, "supplier-post")
    (PROOF / "live/post-body.txt").write_text(post_text)
    print("POST_BODY", post_text[:4000].replace("\n", " | "))
    assert "Thank you" in post_text, post_text[:1000]
    state = guest_state(meta["supplier_token"])
    assert state["status"] == "Confirmed" and state["schedule_date"] == CONFIRM_DATE, state
    assert state["items"] and all(item["schedule_date"] == CONFIRM_DATE for item in state["items"]), state
    page.screenshot(path=str(PROOF / "screenshots/supplier-confirmed-1280.png"), full_page=True)
    # The late PO is untouched by the first supplier's answer.
    assert guest_state(meta["late_token"])["status"] == "Pending"

    # Replaying the same answer through the documented API is idempotent.
    replay_status, _headers, replay_body = request("/api/method/helios_order_visibility.api.confirm_supplier_purchase_order", {
        "token": meta["supplier_token"], "confirmed": "true", "schedule_date": CONFIRM_DATE,
    })
    replay = json.loads(replay_body)["message"]
    assert replay_status == 200 and replay["idempotent"] is True

    page.goto(tracking_url, wait_until="networkidle")
    track_text = check_runtime_page(page, "tracking")
    assert "SO-2007" in track_text
    page.screenshot(path=str(PROOF / "screenshots/customer-tracking-1280.png"), full_page=True)
    page.set_viewport_size({"width": 390, "height": 844})
    page.screenshot(path=str(PROOF / "screenshots/customer-tracking-390.png"), full_page=True)

    auth = context.request.post(base + "/api/method/login", form={"usr": "Administrator", "pwd": "sample-admin"})
    assert auth.ok, auth.text()
    page.set_viewport_size({"width": 1280, "height": 720})
    page.goto(base + "/helios/otd", wait_until="networkidle")
    otd_text = check_runtime_page(page, "otd")
    assert "PO-1042" in otd_text and "Open" in otd_text and "Late open" in otd_text
    page.screenshot(path=str(PROOF / "screenshots/supplier-otd-1280.png"), full_page=True)
    page.set_viewport_size({"width": 390, "height": 844})
    page.screenshot(path=str(PROOF / "screenshots/supplier-otd-390.png"), full_page=True)
    page.set_viewport_size({"width": 1280, "height": 720})
    page.goto(base + "/helios/late_lines", wait_until="networkidle")
    late_lines_text = check_runtime_page(page, "late-lines")
    assert "PO-1043" in late_lines_text and "PO-1042" not in late_lines_text
    page.screenshot(path=str(PROOF / "screenshots/late-lines-1280.png"), full_page=True)
    page.set_viewport_size({"width": 390, "height": 844})
    page.screenshot(path=str(PROOF / "screenshots/late-lines-390.png"), full_page=True)
    browser.close()

# After a signed-in user rendered the reports, a guest still gets 403, not a
# cached copy.
anonymous_otd_after_login = anonymous_status("/helios/otd")
anonymous_late_after_login = anonymous_status("/helios/late_lines")
assert anonymous_otd_after_login == 403 and anonymous_late_after_login == 403

proof = {
    "company": COMPANY,
    "time_zone": meta["time_zone"],
    "site_today": meta["today"],
    "anonymous_otd": anonymous_otd,
    "anonymous_otd_after_login": anonymous_otd_after_login,
    "anonymous_late_lines_after_login": anonymous_late_after_login,
    "supplier_get": 200,
    "second_link_not_cached": True,
    "supplier_ui_post_writeback": state,
    "supplier_api_replay": replay,
    "tracking_get": 200,
    "otd_ui": 200,
    "late_lines_ui": 200,
    "runtime_pages_free_of_demo_wording": True,
    "screenshots": "PASS",
}
(PROOF / "live/http-ui.log").write_text(json.dumps(proof, indent=2, default=str) + "\n")
print(json.dumps(proof, indent=2, default=str))
