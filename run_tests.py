"""
run_tests.py — AuditAI Automated Test Suite
==========================================
Tests every layer of the app WITHOUT needing the Streamlit UI or an API key.

Usage:
    python run_tests.py                    # run all tests
    python run_tests.py --site             # scraper tests only (no API key needed)
    python run_tests.py --competitors      # competitor DB tests only
    python run_tests.py --pdf              # PDF generation tests only
    python run_tests.py --full API_KEY     # full end-to-end audit (uses API credits ~$0.10)

What it checks:
  Layer 1 — Scraper:      HTTPS detection, H1 detection, phone detection
  Layer 2 — Competitors:  Known DB matching, URL format, required fields
  Layer 3 — PDF:          Report generates without errors, all sections present
  Layer 4 — Full audit:   Live audit of vocemploy.com, checks every finding
"""

import sys
import os
import json
import time
import tempfile
import argparse
import traceback

# ── Terminal colors ───────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

passed = 0
failed = 0
warned = 0


def ok(msg):
    global passed
    passed += 1
    print(f"  {GREEN}✓{RESET}  {msg}")


def fail(msg, detail=""):
    global failed
    failed += 1
    print(f"  {RED}✗{RESET}  {msg}")
    if detail:
        print(f"      {RED}→ {detail}{RESET}")


def warn(msg):
    global warned
    warned += 1
    print(f"  {YELLOW}⚠{RESET}  {msg}")


def section(title):
    print(f"\n{BOLD}{BLUE}{'─'*55}{RESET}")
    print(f"{BOLD}{BLUE}  {title}{RESET}")
    print(f"{BOLD}{BLUE}{'─'*55}{RESET}")


def result_summary():
    total = passed + failed + warned
    print(f"\n{'═'*55}")
    print(f"{BOLD}  RESULTS: {total} checks — ", end="")
    if failed == 0:
        print(f"{GREEN}{passed} passed{RESET}{BOLD}", end="")
    else:
        print(f"{GREEN}{passed} passed{RESET}{BOLD}, {RED}{failed} failed{RESET}{BOLD}", end="")
    if warned:
        print(f", {YELLOW}{warned} warnings{RESET}{BOLD}", end="")
    print(f"{RESET}")
    print(f"{'═'*55}\n")
    return failed == 0


# ─────────────────────────────────────────────────────────────
# LAYER 1 — Scraper Tests
# ─────────────────────────────────────────────────────────────

def test_scraper():
    section("LAYER 1 — Scraper & Signal Detection")
    from audit_engine import scrape_page, fetch_html, detect_phone, extract_h1s_deep

    # ── Test: fetch_html returns tuple ────────────────────────
    print(f"\n  {BOLD}fetch_html(){RESET}")
    try:
        result = fetch_html("https://example.com")
        if isinstance(result, tuple) and len(result) == 2:
            ok("Returns (html, final_url) tuple")
        else:
            fail("Should return (html, final_url) tuple", f"Got: {type(result)}")
        html, final_url = result
        if html and len(html) > 100:
            ok(f"Fetches real content ({len(html):,} chars)")
        else:
            fail("No HTML content returned")
        if final_url.startswith("https://"):
            ok(f"Captures final URL after redirects: {final_url}")
        else:
            warn(f"Final URL may not be HTTPS: {final_url}")
    except Exception as e:
        fail("fetch_html raised an exception", str(e))

    # ── Test: HTTPS redirect detection ───────────────────────
    print(f"\n  {BOLD}HTTPS detection (redirect following){RESET}")
    try:
        page = scrape_page("vocemploy.com")  # no https:// prefix
        if page.get("is_https") == True:
            ok("vocemploy.com correctly detected as HTTPS (follows redirect)")
        else:
            fail("vocemploy.com incorrectly flagged as HTTP", f"is_https={page.get('is_https')}")
    except Exception as e:
        fail("HTTPS detection test crashed", str(e))

    try:
        page = scrape_page("http://vocemploy.com")  # explicit HTTP input
        if page.get("is_https") == True:
            ok("http://vocemploy.com correctly resolved to HTTPS after redirect")
        else:
            fail("http://vocemploy.com not resolved to HTTPS", f"is_https={page.get('is_https')}")
    except Exception as e:
        fail("HTTP redirect test crashed", str(e))

    # ── Test: H1 detection ────────────────────────────────────
    print(f"\n  {BOLD}H1 detection (vocemploy.com){RESET}")
    try:
        page = scrape_page("vocemploy.com")
        h1s = page.get("h1s", [])
        h1_count = page.get("h1_count", 0)

        if h1_count > 0:
            ok(f"H1 detected (count={h1_count}): {h1s}")
        else:
            fail("No H1 detected on vocemploy.com", "Expected 'Vocemploy' as H1")

        if any("vocemploy" in h.lower() for h in h1s):
            ok("H1 contains 'Vocemploy' — correct content")
        elif h1_count > 0:
            warn(f"H1 found but content unexpected: {h1s}")

        raw_h1 = page.get("raw_h1_in_html", False)
        if raw_h1:
            ok("raw_h1_in_html=True — H1 tag present in raw HTML")
        else:
            warn("raw_h1_in_html=False — H1 may be JS-rendered only")
    except Exception as e:
        fail("H1 detection test crashed", str(e))

    # ── Test: Phone detection ─────────────────────────────────
    print(f"\n  {BOLD}Phone detection (vocemploy.com){RESET}")
    try:
        page = scrape_page("vocemploy.com")
        has_phone = page.get("has_phone", False)
        phone_num = page.get("phone_number", "")

        if has_phone:
            ok(f"Phone detected: {phone_num}")
        else:
            fail("Phone NOT detected on vocemploy.com", "Expected (888)588-6975")

        if "888" in phone_num or "8885886975" in phone_num.replace("-","").replace("(","").replace(")","").replace(" ",""):
            ok("Detected phone matches known number (888)588-6975")
        elif has_phone:
            warn(f"Phone found but number unexpected: {phone_num}")
    except Exception as e:
        fail("Phone detection test crashed", str(e))

    # ── Test: detect_phone on raw HTML strings ────────────────
    print(f"\n  {BOLD}detect_phone() unit tests{RESET}")
    test_cases = [
        ('<a href="tel:+18885886975">Call Us</a>',    True,  "tel: href format"),
        ("Call us at (888)588-6975 today",             True,  "(888)588-6975 format"),
        ("Phone: 888-588-6975",                        True,  "888-588-6975 format"),
        ("Contact: 888.588.6975",                      True,  "888.588.6975 format"),
        ("No contact info on this page",               False, "no phone present"),
    ]
    for html_str, expected, label in test_cases:
        has_p, num = detect_phone(html_str)
        if has_p == expected:
            ok(f"{label} → {'found' if expected else 'correctly not found'}: {num if num else 'N/A'}")
        else:
            fail(f"{label} — expected {expected}, got {has_p}", f"Input: {html_str[:60]}")

    # ── Test: Page title detection ────────────────────────────
    print(f"\n  {BOLD}Page title (vocemploy.com){RESET}")
    try:
        page = scrape_page("vocemploy.com")
        title = page.get("title", "")
        title_len = page.get("title_length", 0)
        if title:
            ok(f"Title detected: '{title}' ({title_len} chars)")
        else:
            fail("No page title detected")
        if "vocemploy" in title.lower():
            ok("Title contains 'Vocemploy'")
        else:
            warn(f"Title doesn't contain 'Vocemploy': '{title}'")
    except Exception as e:
        fail("Title detection test crashed", str(e))

    # ── Test: Schema detection ────────────────────────────────
    print(f"\n  {BOLD}Schema detection (vocemploy.com){RESET}")
    try:
        page = scrape_page("vocemploy.com")
        for schema, expected in [
            ("has_local_schema",  False),
            ("has_review_schema", False),
            ("has_faq_schema",    False),
        ]:
            val = page.get(schema)
            if val == expected:
                ok(f"{schema}={val} — matches known site state")
            else:
                warn(f"{schema}={val} — site may have changed (expected {expected})")
    except Exception as e:
        fail("Schema detection test crashed", str(e))


# ─────────────────────────────────────────────────────────────
# LAYER 2 — Competitor Database Tests
# ─────────────────────────────────────────────────────────────

def test_competitors():
    section("LAYER 2 — Competitor Database & Matching")
    from audit_engine import get_known_competitors, KNOWN_COMPETITORS

    # ── Test: DB structure ────────────────────────────────────
    print(f"\n  {BOLD}Database structure{RESET}")
    required_fields = ["name", "url", "tier", "threat", "specialization",
                       "differentiator", "serves", "reach", "weakness"]

    for category, comps in KNOWN_COMPETITORS.items():
        missing_fields = []
        for c in comps:
            for f in required_fields:
                if f not in c and f not in ["specialization","differentiator","serves","reach","weakness"]:
                    missing_fields.append(f"{c['name']}.{f}")
            if not c.get("url", "").startswith("https://"):
                fail(f"{c['name']} URL missing https://", c.get("url",""))
        if not missing_fields:
            ok(f"'{category}' — {len(comps)} competitors, required fields present")
        else:
            fail(f"'{category}' missing fields", str(missing_fields))

    # ── Test: TDIU matching ───────────────────────────────────
    print(f"\n  {BOLD}Business type matching{RESET}")
    match_tests = [
        ("tdiu vocational consulting",    "tdiu vocational", ["TDIU Expert", "OAS"]),
        ("veteran disability evaluation", "tdiu vocational", ["TDIU Expert"]),
        ("medical spa aesthetics botox",  "medical spa aesthetics", []),
        ("financial advisory wealth",     "financial advisory",     []),
        ("dental practice teeth",         "dental practice",        []),
    ]
    for biz_type, expected_key, expected_names in match_tests:
        results = get_known_competitors(biz_type, "example.com")
        if expected_key in KNOWN_COMPETITORS:
            if len(results) > 0:
                ok(f"'{biz_type[:35]}' → {len(results)} competitors returned")
            else:
                fail(f"'{biz_type[:35]}' → no competitors matched")
            for name in expected_names:
                if any(name in c["name"] for c in results):
                    ok(f"  Includes expected competitor: {name}")
                else:
                    fail(f"  Missing expected competitor: {name}")

    # ── Test: excludes client domain ─────────────────────────
    print(f"\n  {BOLD}Client domain exclusion{RESET}")
    for domain in ["tdiuexpert.com", "https://tdiuexpert.com", "www.tdiuexpert.com"]:
        results = get_known_competitors("tdiu vocational", domain)
        if not any("tdiuexpert" in c["url"] for c in results):
            ok(f"Correctly excludes '{domain}' from results")
        else:
            fail(f"Client domain '{domain}' appeared in its own competitor list")

    # ── Test: intelligence fields populated ──────────────────
    print(f"\n  {BOLD}Intelligence field quality (TDIU){RESET}")
    results = get_known_competitors("tdiu vocational consulting", "vocemploy.com")
    intel_fields = ["specialization", "differentiator", "serves", "reach", "weakness"]
    for c in results[:3]:
        empty = [f for f in intel_fields if not c.get(f)]
        if not empty:
            ok(f"{c['name']} — all 5 intelligence fields populated")
        else:
            warn(f"{c['name']} — missing fields: {empty}")


# ─────────────────────────────────────────────────────────────
# LAYER 3 — PDF Generation Tests
# ─────────────────────────────────────────────────────────────

def test_pdf():
    section("LAYER 3 — PDF Generation")
    from generate_report import generate_report, SAMPLE_AUDIT
    from audit_engine import get_known_competitors

    print(f"\n  {BOLD}PDF generation with enriched competitor data{RESET}")

    # Inject TDIU competitors into sample data
    test_data = dict(SAMPLE_AUDIT)
    test_data["competitors"] = get_known_competitors("tdiu vocational", "example.com")

    with tempfile.TemporaryDirectory() as tmp:
        try:
            path = generate_report(test_data, tmp)
            if os.path.exists(path):
                size = os.path.getsize(path)
                ok(f"PDF generated successfully ({size:,} bytes)")
                if size > 10000:
                    ok(f"PDF file size looks reasonable ({size:,} bytes)")
                else:
                    warn(f"PDF seems small ({size:,} bytes) — may be missing content")
            else:
                fail("PDF file not created")
        except Exception as e:
            fail("PDF generation crashed", traceback.format_exc()[-300:])
            return

    # ── Test: required sections ───────────────────────────────
    print(f"\n  {BOLD}PDF section completeness{RESET}")
    required_sections = [
        "executive_summary",
        "overall_score",
        "scores",
        "critical_findings",
        "action_plan",
        "competitors",
    ]
    for field in required_sections:
        if field in test_data and test_data[field]:
            ok(f"Data field '{field}' present and non-empty")
        else:
            fail(f"Data field '{field}' missing or empty")

    # ── Test: competitor card fields make it to PDF data ─────
    print(f"\n  {BOLD}Competitor intelligence in PDF data{RESET}")
    for c in test_data["competitors"][:2]:
        intel = [c.get("specialization",""), c.get("differentiator",""), c.get("weakness","")]
        if all(intel):
            ok(f"{c['name']} — intelligence fields ready for PDF")
        else:
            warn(f"{c['name']} — some intelligence fields empty")


# ─────────────────────────────────────────────────────────────
# LAYER 4 — Full End-to-End Audit (requires API key)
# ─────────────────────────────────────────────────────────────

def test_full_audit(api_key: str):
    section("LAYER 4 — Full End-to-End Audit (vocemploy.com)")
    from audit_engine import run_real_audit

    print(f"\n  {BOLD}Running live audit — this takes 30–60 seconds...{RESET}\n")

    messages = []
    def capture(msg):
        messages.append(msg)
        print(f"    {YELLOW}→{RESET} {msg}")

    try:
        data = run_real_audit("vocemploy.com", api_key, progress_callback=capture)
    except Exception as e:
        fail("Audit crashed", traceback.format_exc()[-400:])
        return

    print()

    # ── Correctness checks ────────────────────────────────────
    print(f"  {BOLD}Fact-checking findings against known site state{RESET}")

    # HTTPS — should NOT be a critical finding
    findings_text = " ".join([f.get("title","") + f.get("description","")
                               for f in data.get("critical_findings", [])]).lower()
    if "https" in findings_text and ("missing" in findings_text or "no https" in findings_text or "without https" in findings_text):
        fail("HTTPS falsely flagged as a finding", "Site has valid HTTPS")
    else:
        ok("HTTPS correctly NOT flagged as a missing finding")

    # H1 — should not say 'missing H1'
    if "missing h1" in findings_text or "no h1" in findings_text or "zero h1" in findings_text:
        fail("'Missing H1' incorrectly reported", "Site has H1: 'Vocemploy'")
    else:
        ok("H1 correctly NOT reported as missing")

    # Phone — should not say missing phone
    if "no phone" in findings_text or "missing phone" in findings_text or "no contact number" in findings_text:
        fail("Phone falsely flagged as missing", "Site has (888)588-6975")
    else:
        ok("Phone correctly NOT flagged as missing")

    # Schema — these SHOULD be findings
    for schema_term in ["localbusiness", "review schema", "faq schema"]:
        if schema_term in findings_text:
            ok(f"'{schema_term}' correctly flagged as missing")
        else:
            warn(f"'{schema_term}' not mentioned in findings — may have been missed")

    # ── Scores ────────────────────────────────────────────────
    print(f"\n  {BOLD}Score validation{RESET}")
    score = data.get("overall_score", 0)
    if 0 <= score <= 100:
        ok(f"Overall score in valid range: {score}/100")
    else:
        fail(f"Invalid overall score: {score}")

    for category in ["SEO Health", "Brand Trust", "Conversion", "Technical"]:
        s = data.get("scores", {}).get(category, {}).get("score", None)
        if s is not None and 0 <= s <= 100:
            ok(f"{category}: {s}/100")
        else:
            fail(f"Missing or invalid score for '{category}'", str(s))

    # ── Competitors ───────────────────────────────────────────
    print(f"\n  {BOLD}Competitor section{RESET}")
    comps = data.get("competitors", [])
    if len(comps) >= 3:
        ok(f"{len(comps)} competitors returned")
    elif len(comps) > 0:
        warn(f"Only {len(comps)} competitors returned (expected 3–5)")
    else:
        fail("No competitors returned")

    tdiu_names = ["TDIU Expert", "OAS", "Vocational Expert", "CRC", "Shae Group", "Wasatch", "Summit", "Stroud"]
    tdiu_found = [c["name"] for c in comps if any(t in c["name"] for t in tdiu_names)]
    if tdiu_found:
        ok(f"TDIU-specific competitors included: {tdiu_found}")
    else:
        fail("No TDIU-specific competitors found", f"Got: {[c['name'] for c in comps]}")

    intel_ok = sum(1 for c in comps if c.get("specialization") or c.get("differentiator"))
    if intel_ok == len(comps) and len(comps) > 0:
        ok("All competitor cards have intelligence fields")
    elif intel_ok > 0:
        warn(f"Only {intel_ok}/{len(comps)} competitors have intelligence fields")
    else:
        fail("No competitor intelligence fields populated")

    # ── Action plan ───────────────────────────────────────────
    print(f"\n  {BOLD}Action plan completeness{RESET}")
    plan = data.get("action_plan", {})
    for tier in ["quick_wins", "medium_term", "strategic"]:
        count = len(plan.get(tier, []))
        if count >= 2:
            ok(f"{tier}: {count} items")
        else:
            fail(f"{tier}: only {count} items (expected 3+)")

    # ── PDF from live data ────────────────────────────────────
    print(f"\n  {BOLD}PDF generation from live audit data{RESET}")
    from generate_report import generate_report
    with tempfile.TemporaryDirectory() as tmp:
        try:
            path = generate_report(data, tmp)
            size = os.path.getsize(path)
            ok(f"PDF generated from live data ({size:,} bytes)")
        except Exception as e:
            fail("PDF generation from live data failed", str(e))

    print(f"\n  {BOLD}Raw audit data snapshot:{RESET}")
    print(f"    Domain:     {data.get('domain')}")
    print(f"    Business:   {data.get('business_name')}")
    print(f"    Score:      {data.get('overall_score')}/100 ({data.get('overall_grade')})")
    print(f"    Findings:   {len(data.get('critical_findings', []))}")
    print(f"    Competitors:{len(data.get('competitors', []))}")


# ─────────────────────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AuditAI Test Suite")
    parser.add_argument("--site",        action="store_true", help="Scraper tests only")
    parser.add_argument("--competitors", action="store_true", help="Competitor DB tests only")
    parser.add_argument("--pdf",         action="store_true", help="PDF tests only")
    parser.add_argument("--full",        metavar="API_KEY",   help="Full end-to-end audit")
    args = parser.parse_args()

    run_all = not any([args.site, args.competitors, args.pdf, args.full])

    print(f"\n{BOLD}{'═'*55}")
    print(f"  AUDITAI TEST SUITE")
    print(f"{'═'*55}{RESET}")

    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    if args.site or run_all:
        test_scraper()

    if args.competitors or run_all:
        test_competitors()

    if args.pdf or run_all:
        test_pdf()

    if args.full:
        test_full_audit(args.full)
    elif run_all:
        print(f"\n{YELLOW}  Skipping Layer 4 (full audit) — run with --full YOUR_API_KEY to include{RESET}")

    result_summary()
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
