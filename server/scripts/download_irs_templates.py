"""Download IRS fillable PDF templates for all supported forms.

Downloads to resources/irs_forms/2025/ (the established template directory).
Skips files that already exist.
"""
import os
import time
import urllib.request

TEMPLATE_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "resources", "irs_forms", "2025"
)

# (local_filename, irs_pdf_path)
FORMS = [
    # S-Corp Schedules
    ("f1120ssk2.pdf", "f1120ssk2.pdf"),       # Schedule K-2 (1120-S)
    ("f1120ssk3.pdf", "f1120ssk3.pdf"),       # Schedule K-3 (1120-S)
    # Partnership (1065 family)
    ("f1065sd.pdf", "f1065sd.pdf"),            # Schedule D (1065)
    ("f1065sk2.pdf", "f1065sk2.pdf"),          # Schedule K-2 (1065)
    ("f1065sk3.pdf", "f1065sk3.pdf"),          # Schedule K-3 (1065)
    # QBI
    ("f8995.pdf", "f8995.pdf"),                # QBI Simplified
    ("f8995a.pdf", "f8995a.pdf"),              # QBI Detailed
    # Common supporting forms
    ("f6252.pdf", "f6252.pdf"),                # Installment Sales
    ("f8582.pdf", "f8582.pdf"),                # Passive Activity Limitations
    ("f6198.pdf", "f6198.pdf"),                # At-Risk Limitations
    ("f3800.pdf", "f3800.pdf"),                # General Business Credit
    ("f8941.pdf", "f8941.pdf"),                # Small Employer Health Insurance Credit
    ("f4684.pdf", "f4684.pdf"),                # Casualties and Thefts
    ("f2553.pdf", "f2553.pdf"),                # S Election
    ("f4136.pdf", "f4136.pdf"),                # Credit for Federal Tax Paid on Fuels
    ("f8050.pdf", "f8050.pdf"),                # Direct Deposit of Corporate Tax Refund
    ("f2220.pdf", "f2220.pdf"),                # Underpayment of Estimated Tax
    ("f8990.pdf", "f8990.pdf"),                # Business Interest Limitation
    ("f8997.pdf", "f8997.pdf"),                # QOF Investments
    ("f8283.pdf", "f8283.pdf"),                # Noncash Charitable Contributions
    ("f8824.pdf", "f8824.pdf"),                # Like-Kind Exchanges
    ("f8821.pdf", "f8821.pdf"),                # Tax Information Authorization
    ("f2848.pdf", "f2848.pdf"),                # Power of Attorney
    ("f8822b.pdf", "f8822b.pdf"),              # Change of Address
]

BASE_URL = "https://www.irs.gov/pub/irs-pdf/"
PRIOR_URL = "https://www.irs.gov/pub/irs-prior/"


def download():
    os.makedirs(TEMPLATE_DIR, exist_ok=True)
    downloaded = 0
    skipped = 0
    failed = 0

    for local_name, irs_name in FORMS:
        dest = os.path.join(TEMPLATE_DIR, local_name)
        if os.path.exists(dest):
            print(f"  SKIP {local_name} (already exists)")
            skipped += 1
            continue

        url = BASE_URL + irs_name
        print(f"  Downloading {local_name} from {url}...")
        try:
            urllib.request.urlretrieve(url, dest)
            size = os.path.getsize(dest)
            # Check for HTML error pages (IRS returns HTML for 404s)
            if size < 5000:
                with open(dest, "rb") as f:
                    header = f.read(20)
                if b"<" in header or b"html" in header.lower():
                    os.remove(dest)
                    raise Exception("Got HTML error page instead of PDF")
            print(f"  OK — {size:,} bytes")
            downloaded += 1
        except Exception as e:
            print(f"  FAIL primary URL: {e}")
            # Try prior-year archive
            alt_name = irs_name.replace(".pdf", "--2025.pdf")
            alt_url = PRIOR_URL + alt_name
            print(f"  Trying {alt_url}...")
            try:
                urllib.request.urlretrieve(alt_url, dest)
                size = os.path.getsize(dest)
                if size < 5000:
                    with open(dest, "rb") as f:
                        header = f.read(20)
                    if b"<" in header or b"html" in header.lower():
                        os.remove(dest)
                        raise Exception("Got HTML error page instead of PDF")
                print(f"  OK (prior) — {size:,} bytes")
                downloaded += 1
            except Exception as e2:
                print(f"  FAIL both URLs: {e2}")
                failed += 1

        time.sleep(0.5)  # Be polite to IRS servers

    print(f"\nDone: {downloaded} downloaded, {skipped} skipped, {failed} failed")


if __name__ == "__main__":
    download()
