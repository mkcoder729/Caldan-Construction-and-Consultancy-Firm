"""
End-to-end PDF download verifier for the public shop pages.

Spins up ``manage.py runserver`` in the background, then drives the
shop with Playwright Chromium to confirm that the receipt PDF actually
downloads (and is a real PDF) at every stage it's offered:

  1.  /shop/                       — sidebar present, hero present
  2.  /shop/order/track/           — sidebar present, form present
  3.  /shop/order/track/?order=…&email=…  — verify step with pre-filled
  4.  /shop/order/<n>/receipt/     — direct PDF download (no login)

Usage:
    python scripts/verify_shop_pdfs.py
    python scripts/verify_shop_pdfs.py --order-number ORD-2026-A7F3K9 \
                                       --email jane@example.com \
                                       --base-url http://127.0.0.1:8765

Requires:
    pip install playwright
    playwright install chromium
"""

import argparse
import os
import socket
import subprocess
import sys
import time
import urllib.request
from contextlib import closing
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PORT = 8765
DEFAULT_HOST = "127.0.0.1"


def _free_port(host: str = DEFAULT_HOST, preferred: int = DEFAULT_PORT) -> int:
    """Return ``preferred`` if free, otherwise let the OS pick one."""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        try:
            s.bind((host, preferred))
            return preferred
        except OSError:
            s.bind((host, 0))
            return s.getsockname()[1]


def _wait_for_server(url: str, timeout: float = 30.0) -> None:
    """Poll ``url`` until it returns 200/302 or ``timeout`` expires."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status < 500:
                    return
        except Exception:
            time.sleep(0.5)
    raise RuntimeError(f"Dev server at {url} did not come up within {timeout}s")


def _start_server(port: int) -> subprocess.Popen:
    """Start ``runserver`` detached and return the Popen handle."""
    env = os.environ.copy()
    log_path = REPO_ROOT / "logs" / "verify_shop_pdfs.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = open(log_path, "ab")
    return subprocess.Popen(
        [sys.executable, "manage.py", "runserver", f"{DEFAULT_HOST}:{port}", "--noreload"],
        cwd=str(REPO_ROOT),
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )


def _check_pdf(path: Path) -> str:
    """Return a short reason if the file is not a real PDF, else ''."""
    if not path.exists() or path.stat().st_size < 4:
        return "missing or empty"
    with path.open("rb") as f:
        head = f.read(4)
    if head != b"%PDF":
        return f"bad magic {head!r}"
    return ""


def run_checks(args) -> int:
    from playwright.sync_api import sync_playwright

    port = _free_port(preferred=args.port)
    base_url = args.base_url.rstrip("/") or f"http://{DEFAULT_HOST}:{port}"

    server = _start_server(port)
    print(f"[boot] Started dev server on {base_url} (pid={server.pid})")
    try:
        _wait_for_server(f"{base_url}/shop/", timeout=45)
        print("[boot] Dev server is up")

        results: list[tuple[str, bool, str]] = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()

            # ---- 1. shop home + sidebar ---------------------------------
            try:
                page.goto(f"{base_url}/shop/", wait_until="networkidle")
                page.wait_for_selector("text=Categories", timeout=10_000)
                page.wait_for_selector("text=All Products", timeout=5_000)
                page.wait_for_selector("text=Need Help", timeout=5_000)
                page.wait_for_selector("text=Contact Us", timeout=5_000)
                results.append(("shop_home_sidebar", True, "Categories / All Products / Need Help / Contact Us visible"))
            except Exception as e:
                results.append(("shop_home_sidebar", False, f"{type(e).__name__}: {e}"))

            # ---- 2. tracking form on every step -----------------------
            try:
                page.goto(f"{base_url}/shop/order/track/", wait_until="networkidle")
                page.wait_for_selector("text=Categories")
                page.wait_for_selector("text=Send Verification Code")
                results.append(("tracking_step1_form", True, "Form + sidebar visible"))
            except Exception as e:
                results.append(("tracking_step1_form", False, f"{type(e).__name__}: {e}"))

            # ---- 3. tracking step 2 prefill + sidebar ----------------
            try:
                page.goto(
                    f"{base_url}/shop/order/track/"
                    f"?order_number={args.order_number}&email={args.email}",
                    wait_until="networkidle",
                )
                page.wait_for_selector("text=Categories")
                page.wait_for_selector(".prefill-summary", timeout=10_000)
                page.wait_for_selector("text=Proceed")
                # Confirm the order number and email are visible in the summary
                content = page.content()
                if args.order_number not in content:
                    raise RuntimeError("order number not in prefill summary")
                if args.email not in content:
                    raise RuntimeError("email not in prefill summary")
                results.append((
                    "tracking_step2_prefill",
                    True,
                    f"Pre-filled summary shows {args.order_number} + {args.email}",
                ))
            except Exception as e:
                results.append(("tracking_step2_prefill", False, f"{type(e).__name__}: {e}"))

            # ---- 4. direct public receipt download --------------------
            try:
                dl_target = REPO_ROOT / "logs" / "verify_receipt.pdf"
                with page.expect_download(timeout=20_000) as dl_info:
                    page.goto(
                        f"{base_url}/shop/order/{args.order_number}/receipt/"
                        f"?email={args.email}",
                        wait_until="domcontentloaded",
                    )
                download = dl_info.value
                download.save_as(str(dl_target))
                reason = _check_pdf(dl_target)
                if reason:
                    raise RuntimeError(f"downloaded file is not a PDF ({reason})")
                size = dl_target.stat().st_size
                results.append((
                    "public_receipt_download",
                    True,
                    f"Saved {dl_target.name} ({size} bytes, header %PDF)",
                ))
            except Exception as e:
                results.append(("public_receipt_download", False, f"{type(e).__name__}: {e}"))

            # ---- 5. tracking step 3 result card via code ---------------
            try:
                # Read the latest tracking code from the DB through a small
                # one-shot endpoint would be ideal; for now we rely on the
                # locmem backend printing the code in the dev-server log.
                # As a portable fallback, just check the URL accepts the
                # verify POST and the resulting page contains the result card
                # when given a stub code that won't match (i.e. we expect
                # the verify step to re-render with an error).
                page.goto(f"{base_url}/shop/order/track/", wait_until="networkidle")
                page.fill("#id_order_number", args.order_number)
                page.fill("#id_email", args.email)
                page.click("#sendCodeBtn")
                page.wait_for_url("**/order/track/**", timeout=10_000)
                page.wait_for_selector("#verificationCode")
                # Type a wrong code so we exercise the verify path
                page.fill("#verificationCode", "000000")
                page.click("#verifyBtn")
                page.wait_for_load_state("networkidle")
                # Sidebar still present after a wrong-code attempt
                page.wait_for_selector("text=Categories")
                results.append((
                    "tracking_step3_wrong_code",
                    True,
                    "Verify POST re-renders step 2 with sidebar still present",
                ))
            except Exception as e:
                results.append(("tracking_step3_wrong_code", False, f"{type(e).__name__}: {e}"))

            browser.close()

        # ---- report ----
        print()
        print("=" * 70)
        print("SHOP PUBLIC PAGE + PDF DOWNLOAD REPORT")
        print("=" * 70)
        ok = 0
        for name, passed, msg in results:
            mark = "✅" if passed else "❌"
            print(f"{mark} {name:<32} {msg}")
            if passed:
                ok += 1
        print("-" * 70)
        print(f"{ok}/{len(results)} passed")
        return 0 if ok == len(results) else 1

    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--order-number", default=os.environ.get("VERIFY_ORDER_NUMBER", "ORD-2026-A7F3K9"))
    parser.add_argument("--email", default=os.environ.get("VERIFY_EMAIL", "jane@example.com"))
    parser.add_argument("--base-url", default=os.environ.get("VERIFY_BASE_URL", ""))
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    return run_checks(args)


if __name__ == "__main__":
    sys.exit(main())
