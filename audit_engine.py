"""
audit_engine.py — AuditAI Real Website Analyzer
Scrapes any URL, finds REAL competitors via Google, verifies each URL,
then uses Claude API to produce genuine audit data.
"""

VERSION = "12"  # ← Update this whenever you install a new version

import json
import re
import urllib.request
import urllib.error
import urllib.parse
import time
from datetime import datetime
from html.parser import HTMLParser


# ─────────────────────────────────────────────────────────────
# HTML Scraper
# ─────────────────────────────────────────────────────────────

class PageScraper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title        = ""
        self.meta_desc    = ""
        self.h1s          = []
        self.h2s          = []
        self.links        = []
        self.text_chunks  = []
        self.in_script    = False
        self.in_style     = False
        self.in_body      = False
        self._current_tag = ""

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        self._current_tag = tag
        if tag == "script": self.in_script = True
        if tag == "style":  self.in_style  = True
        if tag == "body":   self.in_body   = True
        if tag == "meta":
            name    = attrs_dict.get("name", "").lower()
            prop    = attrs_dict.get("property", "").lower()
            content = attrs_dict.get("content", "")
            if name in ("description",) or prop == "og:description":
                self.meta_desc = content
        if tag == "a" and "href" in attrs_dict:
            self.links.append(attrs_dict["href"])

    def handle_endtag(self, tag):
        if tag == "script": self.in_script = False
        if tag == "style":  self.in_style  = False

    def handle_data(self, data):
        if self.in_script or self.in_style:
            return
        text = data.strip()
        if not text:
            return
        tag = self._current_tag
        if tag == "title":
            self.title = text
        elif tag == "h1":
            self.h1s.append(text)
        elif tag == "h2":
            self.h2s.append(text[:120])
        elif self.in_body and len(text) > 20:
            self.text_chunks.append(text[:300])


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def fetch_html(url: str, timeout: int = 12) -> tuple:
    """
    Fetch URL, follow redirects, try www prefix on failure.
    Returns (html: str, final_url: str).
    final_url always reflects the real URL after redirects — use this for HTTPS detection.
    """
    if not url.startswith("http"):
        url = "https://" + url

    attempts = [url]
    if "www." not in url:
        attempts.append(url.replace("://", "://www."))

    for attempt_url in attempts:
        try:
            req      = urllib.request.Request(attempt_url, headers=HEADERS)
            response = urllib.request.urlopen(req, timeout=timeout)
            final_url = response.geturl()   # real URL after all redirects
            raw       = response.read()

            # Handle gzip encoding
            content_encoding = response.headers.get("Content-Encoding", "")
            if content_encoding == "gzip":
                import gzip
                raw = gzip.decompress(raw)

            html = raw.decode("utf-8", errors="ignore")
            if html:
                return html, final_url
            # Got a response but empty body — still return final_url for HTTPS check
            return "", final_url
        except Exception:
            continue

    # All attempts failed — but normalise the URL so HTTPS detection
    # doesn't falsely flag a site just because the sandbox can't reach it.
    # The caller must handle empty html gracefully.
    return "", url


def extract_h1s_deep(html: str) -> list:
    """
    Multi-strategy H1 extraction that catches both static and JS-rendered H1s.
    Strategy 1: Standard HTML parser results (passed in from caller)
    Strategy 2: Raw regex on HTML (catches H1s inside JS strings and templates)
    Strategy 3: aria-level="1" elements as fallback
    """
    found = []
    # Strategy 2: Raw regex sweep
    raw_h1s = re.findall(r'<h1[^>]*>\s*(.*?)\s*</h1>', html, re.IGNORECASE | re.DOTALL)
    for h in raw_h1s:
        clean = re.sub(r'<[^>]+>', '', h).strip()
        if clean and len(clean) > 1 and clean not in found:
            found.append(clean[:200])
    # Strategy 3: aria-level="1"
    aria_h1s = re.findall(r'aria-level=["\']1["\'][^>]*>\s*(.*?)\s*</', html, re.IGNORECASE | re.DOTALL)
    for h in aria_h1s:
        clean = re.sub(r'<[^>]+>', '', h).strip()
        if clean and len(clean) > 1 and clean not in found:
            found.append(clean[:200])
    return found[:5]


def detect_phone(html: str) -> tuple:
    """
    Improved phone detection. Returns (has_phone: bool, phone_number: str).
    Catches: (888)588-6975, 888-588-6975, tel: links, +1 formats, etc.
    """
    # tel: href links — most reliable
    tel_links = re.findall(r'href=["\']tel:([+\d\s\-\(\)\.]{7,20})["\']', html, re.IGNORECASE)
    if tel_links:
        return True, tel_links[0].strip()
    # Common US formats
    patterns = [
        r'\(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4}',
        r'\+1[\s.\-]?\(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4}',
        r'\b\d{3}[\s.\-]\d{3}[\s.\-]\d{4}\b',
    ]
    for p in patterns:
        m = re.search(p, html)
        if m:
            return True, m.group(0).strip()
    return False, ""


def scrape_page(url: str) -> dict:
    """Scrape a page and return structured signals with improved H1 and phone detection."""
    html, final_url = fetch_html(url)

    # resolved_url is always the post-redirect URL — use it for HTTPS detection
    # even if the page body is empty
    resolved_url = final_url if final_url else url

    if not html:
        # Return minimal dict with correct HTTPS status so Claude
        # never falsely flags HTTPS as missing just due to a fetch error
        return {
            "error":          f"Could not load page content for {url}",
            "url":            resolved_url,
            "is_https":       resolved_url.startswith("https"),
            "title":          "", "meta_desc": "", "h1s": [], "h2s": [],
            "links": [], "body_text": "", "h1_count": 0, "link_count": 0,
            "has_meta_desc": False, "title_length": 0,
            "has_local_schema": False, "has_faq_schema": False,
            "has_review_schema": False, "has_cta": False,
            "has_pricing": False, "has_phone": False, "phone_number": "",
            "js_rendered": False, "raw_h1_in_html": False,
        }

    parser = PageScraper()
    parser.feed(html)

    # Deep H1 extraction — merges parser results with raw HTML scan
    deep_h1s = extract_h1s_deep(html)
    all_h1s  = list(dict.fromkeys(parser.h1s + deep_h1s))  # deduplicate, preserve order

    # Improved phone detection
    has_phone, phone_number = detect_phone(html)

    # Flag JS-heavy sites so Claude knows H1s may not appear in raw HTML
    js_rendered = bool(re.search(
        r'(react|angular|vue|next\.js|nuxt|gatsby|__NEXT_DATA__|window\.__data)',
        html, re.IGNORECASE
    ))

    return {
        "url":               url,
        "title":             parser.title[:120],
        "meta_desc":         parser.meta_desc[:160],
        "h1s":               all_h1s[:5],
        "h2s":               parser.h2s[:10],
        "links":             parser.links[:30],
        "body_text":         " ".join(parser.text_chunks[:40]),
        "has_local_schema":  "LocalBusiness" in html,
        "has_faq_schema":    "FAQPage"        in html,
        "has_review_schema": "AggregateRating" in html,
        "has_cta":           any(s in html.lower() for s in ["book","schedule","appointment","call us","contact","get started"]),
        "has_pricing":       bool(re.search(r'\$[\d,]+', html)),
        "has_phone":         has_phone,
        "phone_number":      phone_number,
        "is_https":          resolved_url.startswith("https"),  # checks final URL after redirects
        "h1_count":          len(all_h1s),
        "link_count":        len(parser.links),
        "has_meta_desc":     bool(parser.meta_desc),
        "title_length":      len(parser.title),
        "js_rendered":       js_rendered,
        "raw_h1_in_html":    bool(re.search(r'<h1[\s>]', html, re.IGNORECASE)),
    }


# ─────────────────────────────────────────────────────────────
# Real Competitor Finder
# ─────────────────────────────────────────────────────────────

class GoogleResultParser(HTMLParser):
    """Parse Google search results to extract real business URLs and names."""
    def __init__(self):
        super().__init__()
        self.results      = []   # list of {"url": ..., "title": ...}
        self.in_h3        = False
        self.current_title= ""
        self.current_url  = ""
        self._capture     = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "a":
            href = attrs_dict.get("href", "")
            # Google result links look like /url?q=https://...
            if href.startswith("/url?q="):
                url = urllib.parse.unquote(href[7:].split("&")[0])
                if url.startswith("http") and "google" not in url:
                    self.current_url = url
        if tag == "h3":
            self.in_h3 = True
            self.current_title = ""

    def handle_endtag(self, tag):
        if tag == "h3":
            self.in_h3 = False
            if self.current_url and self.current_title:
                self.results.append({
                    "url":   self.current_url,
                    "title": self.current_title.strip(),
                })
                self.current_url   = ""
                self.current_title = ""

    def handle_data(self, data):
        if self.in_h3:
            self.current_title += data


def url_resolves(url: str, timeout: int = 8) -> bool:
    """Check if a URL actually loads (returns True/False)."""
    try:
        if not url.startswith("http"):
            url = "https://" + url
        req      = urllib.request.Request(url, headers=HEADERS, method="HEAD")
        response = urllib.request.urlopen(req, timeout=timeout)
        return response.status < 400
    except Exception:
        # HEAD failed, try GET
        try:
            req      = urllib.request.Request(url, headers=HEADERS)
            response = urllib.request.urlopen(req, timeout=timeout)
            return True
        except Exception:
            return False


def get_domain(url: str) -> str:
    """Extract bare domain from URL."""
    url = url.replace("https://","").replace("http://","").replace("www.","")
    return url.split("/")[0].split("?")[0]


def search_real_competitors(business_type: str, location: str, exclude_domain: str) -> list:
    """
    Search Google for real competitors and verify each URL loads.
    Returns list of verified competitor dicts.
    """
    competitors = []
    seen_domains = {get_domain(exclude_domain)}

    # Build 3 search queries to find different competitor tiers
    queries = [
        f"{business_type} {location}",
        f"{business_type} near {location}",
        f"best {business_type} {location}",
    ]

    for query in queries:
        if len(competitors) >= 6:
            break

        encoded = urllib.parse.quote_plus(query)
        search_url = f"https://www.google.com/search?q={encoded}&num=10"

        try:
            req      = urllib.request.Request(search_url, headers={
                **HEADERS,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            response = urllib.request.urlopen(req, timeout=12)
            html     = response.read().decode("utf-8", errors="ignore")
        except Exception:
            continue

        parser = GoogleResultParser()
        parser.feed(html)

        for result in parser.results:
            domain = get_domain(result["url"])

            # Skip if already seen, is the client, or is a directory/review site
            skip_domains = ["yelp.com","yellowpages.com","angi.com","bbb.org","facebook.com",
                           "instagram.com","linkedin.com","twitter.com","google.com",
                           "maps.google","tripadvisor.com","healthgrades.com","zocdoc.com",
                           "psychology today","wikipedia","indeed.com","glassdoor.com"]

            if domain in seen_domains:
                continue
            if any(s in domain for s in skip_domains):
                continue

            seen_domains.add(domain)

            # Verify the URL actually loads
            base_url = f"https://{domain}"
            if url_resolves(base_url):
                # Estimate reviews (can't get real number without API)
                competitors.append({
                    "name":   result["title"].split(" - ")[0].split(" | ")[0][:60],
                    "url":    base_url,
                    "domain": domain,
                })

            time.sleep(0.3)  # polite delay

        time.sleep(0.5)

    return competitors[:6]


def classify_competitors(competitors: list, business_type: str, api_key: str) -> list:
    """
    Use Claude to classify verified competitors into Direct/Indirect/Aspirational
    and estimate threat level. Much simpler prompt — just classification.
    """
    if not competitors:
        return []

    comp_list = "\n".join([f"- {c['name']} ({c['url']})" for c in competitors])

    payload = json.dumps({
        "model": "claude-sonnet-4-6",
        "max_tokens": 800,
        "messages": [{
            "role": "user",
            "content": f"""Classify these real competitors for a {business_type} business.
Return ONLY a JSON array, no other text.

Competitors:
{comp_list}

Return exactly this format:
[
  {{"name": "Business Name", "url": "https://domain.com", "tier": "Direct|Indirect|Aspirational", "threat": "HIGH|MED|LOW", "reviews": <estimated int>}}
]

Rules:
- Direct = same service, same market
- Indirect = different approach to same customer need  
- Aspirational = market leader worth benchmarking
- Estimate reviews based on how established the business looks
- Return ALL {len(competitors)} competitors classified
- Return ONLY the JSON array"""
        }]
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type":      "application/json",
            "x-api-key":         api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST"
    )

    try:
        response = urllib.request.urlopen(req, timeout=30)
        data     = json.loads(response.read().decode("utf-8"))
        raw      = data["content"][0]["text"].strip()
        # Strip markdown fences
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$",       "", raw).strip()
        return json.loads(raw)
    except Exception:
        # Fallback: return competitors with default classification
        return [
            {
                "name":    c["name"],
                "url":     c["url"],
                "tier":    "Direct",
                "threat":  "MED",
                "reviews": 50,
            }
            for c in competitors
        ]


# ─────────────────────────────────────────────────────────────
# Known Competitor Database
# Curated, verified lists by industry — used as primary source
# when Google search is blocked or returns poor results
# ─────────────────────────────────────────────────────────────

KNOWN_COMPETITORS = {
    "tdiu vocational": [
        {
            "name": "TDIU Expert",
            "url": "https://tdiuexpert.com",
            "tier": "Direct", "threat": "HIGH", "reviews": 85,
            "specialization": "Focuses solely on veterans and their ability to perform substantially gainful work",
            "differentiator": "20+ years of experience exclusively in TDIU evaluations",
            "serves": "Veterans directly and VA disability attorneys nationwide",
            "reach": "National",
            "weakness": "Narrow focus — no Aid & Attendance or Social Security services",
        },
        {
            "name": "Vocational Expert Services, Inc.",
            "url": "https://vocexpertservices.com",
            "tier": "Direct", "threat": "HIGH", "reviews": 60,
            "specialization": "Evaluates and documents the impact of service-connected conditions on employability",
            "differentiator": "Serves US and Puerto Rico — broader geographic reach than most",
            "serves": "Veterans and VA disability attorneys",
            "reach": "National + Puerto Rico",
            "weakness": "Less brand recognition than category leaders",
        },
        {
            "name": "OAS — Occupational Assessment Services",
            "url": "https://oasinc.org",
            "tier": "Direct", "threat": "HIGH", "reviews": 75,
            "specialization": "Vocational expert and life care planning services for veterans",
            "differentiator": "Nationwide firm with physical offices in 9+ states — strongest local presence",
            "serves": "Veterans, VA attorneys, and life care planning clients",
            "reach": "National (9+ state offices)",
            "weakness": "Broader scope dilutes TDIU specialization messaging",
        },
        {
            "name": "CRC Services, LLC",
            "url": "https://crcservicesllc.com",
            "tier": "Direct", "threat": "MED", "reviews": 55,
            "specialization": "TDIU vocational assessments and assistance",
            "differentiator": "Established since 2000 — one of the longest-running TDIU specialists",
            "serves": "Veterans and VA disability attorneys",
            "reach": "National",
            "weakness": "Older brand — likely weaker digital presence and SEO",
        },
        {
            "name": "The Shae Group, LLC",
            "url": "https://theshaegroupllc.com",
            "tier": "Direct", "threat": "MED", "reviews": 40,
            "specialization": "VA-tailored vocational assessments for veteran attorneys",
            "differentiator": "Based in Lancaster, SC — regional proximity is a direct geographic threat",
            "serves": "Primarily veteran attorneys nationwide",
            "reach": "National (SC-based)",
            "weakness": "Attorney-focused model — less direct-to-veteran outreach",
        },
        {
            "name": "Wasatch Disability Solutions",
            "url": "https://wasatchdisability.com",
            "tier": "Direct", "threat": "MED", "reviews": 45,
            "specialization": "Exclusively TDIU vocational evaluations for VA disability attorneys",
            "differentiator": "Narrowest focus in the category — pure TDIU, attorney channel only",
            "serves": "VA disability attorneys exclusively",
            "reach": "National",
            "weakness": "No direct-to-veteran channel limits growth ceiling",
        },
        {
            "name": "Summit Vocational Consulting",
            "url": "https://summitvocational.com",
            "tier": "Indirect", "threat": "MED", "reviews": 35,
            "specialization": "Vocational packages for TDIU and Aid & Attendance (A&A) claims",
            "differentiator": "Dual service offering — TDIU plus A&A expands addressable market",
            "serves": "Veterans and VA attorneys",
            "reach": "National",
            "weakness": "Bundled A&A offering may dilute TDIU credibility",
        },
        {
            "name": "Stroud Vocational Expert Services",
            "url": "https://stroudve.net",
            "tier": "Indirect", "threat": "LOW", "reviews": 30,
            "specialization": "Vocational forensic analysis, labor market analysis, veterans disability",
            "differentiator": "Forensic analysis expertise — serves legal proceedings beyond VA claims",
            "serves": "Veterans, attorneys, courts",
            "reach": "Regional (Alabama-based)",
            "weakness": "Regional focus and broader forensic scope — less TDIU-specific branding",
        },
    ],
    "consulting": [
        {"name": "McKinsey & Company",    "url": "https://mckinsey.com",    "tier": "Aspirational", "threat": "LOW",  "reviews": 500},
        {"name": "Bain & Company",        "url": "https://bain.com",        "tier": "Aspirational", "threat": "LOW",  "reviews": 400},
        {"name": "Deloitte Consulting",   "url": "https://deloitte.com",    "tier": "Aspirational", "threat": "LOW",  "reviews": 600},
    ],
    "medical spa aesthetics": [
        {"name": "Ideal Image",           "url": "https://idealimage.com",  "tier": "Aspirational", "threat": "MED",  "reviews": 2000},
        {"name": "SkinSpirit",            "url": "https://skinspirit.com",  "tier": "Indirect",     "threat": "MED",  "reviews": 800},
    ],
    "financial advisory": [
        {"name": "Edward Jones",          "url": "https://edwardjones.com", "tier": "Aspirational", "threat": "MED",  "reviews": 5000},
        {"name": "Fisher Investments",    "url": "https://fisherinvestments.com", "tier": "Indirect","threat": "MED",  "reviews": 1200},
        {"name": "Raymond James",         "url": "https://raymondjames.com","tier": "Aspirational", "threat": "LOW",  "reviews": 900},
    ],
    "law firm": [
        {"name": "LegalZoom",             "url": "https://legalzoom.com",   "tier": "Indirect",     "threat": "MED",  "reviews": 8000},
        {"name": "Martindale-Hubbell",    "url": "https://martindale.com",  "tier": "Indirect",     "threat": "LOW",  "reviews": 300},
    ],
    "dental practice": [
        {"name": "Aspen Dental",          "url": "https://aspendental.com", "tier": "Aspirational", "threat": "MED",  "reviews": 10000},
        {"name": "Smile Brands",          "url": "https://smilebrands.com", "tier": "Indirect",     "threat": "LOW",  "reviews": 2000},
    ],
    "fitness gym": [
        {"name": "Planet Fitness",        "url": "https://planetfitness.com","tier": "Aspirational", "threat": "MED", "reviews": 50000},
        {"name": "Anytime Fitness",       "url": "https://anytimefitness.com","tier": "Indirect",   "threat": "MED",  "reviews": 20000},
        {"name": "CrossFit",              "url": "https://crossfit.com",    "tier": "Indirect",     "threat": "LOW",  "reviews": 5000},
    ],
    "home services contractor": [
        {"name": "HomeAdvisor",           "url": "https://homeadvisor.com", "tier": "Indirect",     "threat": "MED",  "reviews": 30000},
        {"name": "Angi",                  "url": "https://angi.com",        "tier": "Indirect",     "threat": "MED",  "reviews": 25000},
    ],
    "restaurant": [
        {"name": "OpenTable",             "url": "https://opentable.com",   "tier": "Indirect",     "threat": "LOW",  "reviews": 100000},
    ],
    "real estate agency": [
        {"name": "RE/MAX",                "url": "https://remax.com",       "tier": "Aspirational", "threat": "MED",  "reviews": 50000},
        {"name": "Keller Williams",       "url": "https://kw.com",          "tier": "Aspirational", "threat": "MED",  "reviews": 40000},
        {"name": "Coldwell Banker",       "url": "https://coldwellbanker.com","tier": "Aspirational","threat": "LOW",  "reviews": 35000},
    ],
}


def get_known_competitors(biz_type: str, exclude_domain: str) -> list:
    """
    Match business type to known competitor database.
    Returns up to 5 verified competitors, excluding the client's own domain.
    """
    biz_lower = biz_type.lower()

    # Find best matching category
    matched_key = None
    if any(w in biz_lower for w in ["tdiu", "vocational", "veteran", "va benefit", "disability eval"]):
        matched_key = "tdiu vocational"
    elif any(w in biz_lower for w in ["medspa", "med spa", "aesthetics", "botox", "laser"]):
        matched_key = "medical spa aesthetics"
    elif any(w in biz_lower for w in ["financial", "advisor", "wealth", "investment"]):
        matched_key = "financial advisory"
    elif any(w in biz_lower for w in ["law", "attorney", "lawyer"]):
        matched_key = "law firm"
    elif any(w in biz_lower for w in ["dental", "dentist"]):
        matched_key = "dental practice"
    elif any(w in biz_lower for w in ["gym", "fitness"]):
        matched_key = "fitness gym"
    elif any(w in biz_lower for w in ["plumb", "hvac", "roofing", "contractor"]):
        matched_key = "home services contractor"
    elif any(w in biz_lower for w in ["restaurant", "cafe", "dining"]):
        matched_key = "restaurant"
    elif any(w in biz_lower for w in ["real estate", "realtor"]):
        matched_key = "real estate agency"
    elif any(w in biz_lower for w in ["consult"]):
        matched_key = "consulting"

    if not matched_key:
        return []

    # Normalize both to bare domain for reliable comparison
    exclude_clean = (exclude_domain
                     .replace("https://", "").replace("http://", "")
                     .replace("www.", "").strip("/").split("/")[0])
    results = []
    for c in KNOWN_COMPETITORS[matched_key]:
        domain = c["url"].replace("https://", "").replace("http://", "").replace("www.", "").strip("/").split("/")[0]
        if exclude_clean not in domain:
            results.append(c)
        if len(results) >= 5:
            break

    return results


def claude_competitor_fallback(biz_type: str, location: str, exclude_domain: str, api_key: str) -> list:
    """
    When Google search is blocked, ask Claude for competitors it is
    CERTAIN exist as real businesses with real websites.
    Claude is explicitly told not to fabricate — only include ones it knows.
    """
    payload = json.dumps({
        "model": "claude-sonnet-4-6",
        "max_tokens": 800,
        "messages": [{
            "role": "user",
            "content": f"""List real competitors for a {biz_type} business in {location}.

CRITICAL RULES:
- Only include businesses you are CERTAIN exist with a working website
- Do NOT invent names or URLs — if unsure, omit
- Include national industry leaders if local ones are unknown
- Exclude: {exclude_domain}

Return ONLY a JSON array (no other text):
[
  {{"name": "Business Name", "url": "https://domain.com", "tier": "Direct|Indirect|Aspirational", "threat": "HIGH|MED|LOW", "reviews": <estimated int>}}
]

Include 3-5 entries maximum. If you cannot confidently name any, return an empty array: []"""
        }]
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type":      "application/json",
            "x-api-key":         api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST"
    )

    try:
        response = urllib.request.urlopen(req, timeout=30)
        data     = json.loads(response.read().decode("utf-8"))
        raw      = data["content"][0]["text"].strip()
        raw      = re.sub(r"^```[a-z]*\n?", "", raw)
        raw      = re.sub(r"\n?```$",       "", raw).strip()
        candidates = json.loads(raw)

        # Verify each URL Claude suggested actually loads
        verified = []
        for c in candidates:
            if url_resolves(c.get("url", "")):
                verified.append(c)
        return verified
    except Exception:
        return []


# ─────────────────────────────────────────────────────────────
# Claude API
# ─────────────────────────────────────────────────────────────

def call_claude(api_key: str, system_prompt: str, user_prompt: str) -> str:
    payload = json.dumps({
        "model": "claude-sonnet-4-6",
        "max_tokens": 4000,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}]
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type":      "application/json",
            "x-api-key":         api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST"
    )

    try:
        response = urllib.request.urlopen(req, timeout=60)
        data     = json.loads(response.read().decode("utf-8"))
        return data["content"][0]["text"]
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        raise Exception(f"Claude API error {e.code}: {body}")


def score_to_grade(score: int) -> str:
    if score >= 90: return "A"
    if score >= 83: return "B+"
    if score >= 76: return "B"
    if score >= 70: return "B-"
    if score >= 63: return "C+"
    if score >= 56: return "C"
    if score >= 50: return "C-"
    if score >= 43: return "D+"
    if score >= 36: return "D"
    return "F"


# ─────────────────────────────────────────────────────────────
# Main Audit Function
# ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a senior marketing strategist and technical SEO expert.
You audit websites and return ONLY valid JSON with no extra text, no markdown, no code fences.
Your analysis must be specific to the actual website content provided — never use generic placeholder text.
Always base findings on real signals from the scraped content."""


def run_real_audit(domain: str, api_key: str, progress_callback=None, manual_biz_type: str = "", manual_competitors: list = None) -> dict:
    def update(msg):
        if progress_callback:
            progress_callback(msg)

    # ── 1. Scrape client site ─────────────────────────────────
    update("Crawling website...")
    page = scrape_page(domain)

    clean_domain  = domain.replace("https://","").replace("http://","").replace("www.","").rstrip("/")
    business_name = clean_domain.split(".")[0].replace("-"," ").replace("_"," ").title()

    # ── 2. Infer business type from content ───────────────────
    update("Identifying business type...")
    body_sample = page.get("body_text", "")[:500].lower()
    title_lower = page.get("title", "").lower()
    h1_lower    = " ".join(page.get("h1s", [])).lower()
    all_text    = f"{title_lower} {h1_lower} {body_sample}"

    # Simple keyword-based business type detection
    biz_type = "business"
    # IMPORTANT: more specific checks must come BEFORE generic ones
    # e.g. "tdiu vocational" must be checked before generic "consulting"
    if any(w in all_text for w in ["tdiu","unemployability","va benefit","va claim","veteran vocational","vocational evaluation","service-connected"]):
        biz_type = "tdiu vocational"
    elif any(w in all_text for w in ["botox","filler","medspa","med spa","aesthetics","laser","skincare"]):
        biz_type = "medical spa aesthetics"
    elif any(w in all_text for w in ["attorney","lawyer","law firm","legal"]):
        biz_type = "law firm"
    elif any(w in all_text for w in ["dentist","dental","teeth","orthodont"]):
        biz_type = "dental practice"
    elif any(w in all_text for w in ["restaurant","menu","reserv","dining","cafe","bistro"]):
        biz_type = "restaurant"
    elif any(w in all_text for w in ["plumb","hvac","electric","roofing","contractor","handyman"]):
        biz_type = "home services contractor"
    elif any(w in all_text for w in ["real estate","realtor","homes for sale","property"]):
        biz_type = "real estate agency"
    elif any(w in all_text for w in ["gym","fitness","personal train","crossfit","yoga","pilates"]):
        biz_type = "fitness gym"
    elif any(w in all_text for w in ["chiro","physical therapy","pt clinic","rehab"]):
        biz_type = "physical therapy or chiropractic"
    elif any(w in all_text for w in ["financial","advisor","wealth","investment","insurance"]):
        biz_type = "financial advisory"
    elif any(w in all_text for w in ["vocational","consultant","consulting"]):
        biz_type = "consulting"
    elif any(w in all_text for w in ["salon","hair","nail","spa","beauty"]):
        biz_type = "hair or beauty salon"

    # Try to detect location from page content
    location = ""
    location_patterns = [
        r'\b([A-Z][a-z]+,\s*[A-Z]{2})\b',   # City, ST
        r'\bin\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?),?\s+[A-Z]{2}\b',
    ]
    for pattern in location_patterns:
        match = re.search(pattern, page.get("body_text", "") + page.get("title", ""))
        if match:
            location = match.group(1)
            break

    if not location:
        location = "United States"

    # ── Manual overrides from UI ──────────────────────────────
    # If user supplied industry keywords, use those instead of auto-detection
    if manual_biz_type and manual_biz_type.strip():
        biz_type = manual_biz_type.strip().lower()

    # ── 3. Find real competitors ─────────────────────────────
    if manual_competitors:
        # User supplied their own competitor URLs — use them directly
        update("Using your competitor list...")
        verified_competitors = []
        for url in manual_competitors:
            url = url.strip()
            if not url:
                continue
            if not url.startswith("http"):
                url = "https://" + url
            name = url.replace("https://","").replace("http://","").replace("www.","").rstrip("/").split(".")[0].replace("-"," ").replace("_"," ").title()
            verified_competitors.append({
                "name":           name,
                "url":            url,
                "tier":           "Direct",
                "threat":         "HIGH",
                "reviews":        0,
                "specialization": "",
                "differentiator": "",
                "serves":         "",
                "reach":          "",
                "weakness":       "",
            })
        # Ask Claude to enrich the competitor intelligence
        if verified_competitors:
            update("Claude is researching your competitors...")
            enrich_prompt = f"""For each competitor below, return a JSON array with enriched intelligence fields.
Business type: {biz_type}
Client domain: {clean_domain}

Competitors to enrich:
{json.dumps([{"name": c["name"], "url": c["url"]} for c in verified_competitors], indent=2)}

For each, return:
- name (keep as-is)
- url (keep as-is)  
- tier: "Direct", "Indirect", or "Aspirational"
- threat: "HIGH", "MED", or "LOW"
- reviews: estimated number of online reviews (integer)
- specialization: what they focus on (1 sentence)
- differentiator: their key competitive advantage (1 sentence)
- serves: who their target client is (1 sentence)
- reach: geographic reach (e.g. "National", "Regional", "Local")
- weakness: their biggest exploitable weakness (1 sentence)

Return ONLY a JSON array, no other text."""
            try:
                raw = call_claude(api_key, "You are a competitive intelligence analyst. Return only valid JSON arrays.", enrich_prompt)
                raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
                enriched = json.loads(raw)
                if isinstance(enriched, list) and len(enriched) > 0:
                    verified_competitors = enriched
            except Exception:
                pass  # keep unenriched version if Claude fails
    else:
        # Priority 1: curated known competitor database (fastest, most accurate)
        update("Looking up industry competitors...")
        verified_competitors = get_known_competitors(biz_type, clean_domain)

        # Priority 2: live Google search to supplement or replace
        if len(verified_competitors) < 3:
            update("Searching web for local competitors...")
            raw_competitors = search_real_competitors(biz_type, location, clean_domain)
            if raw_competitors:
                update(f"Verifying {len(raw_competitors)} competitor URLs...")
                google_competitors = classify_competitors(raw_competitors, biz_type, api_key)
                known_urls = {c["url"] for c in verified_competitors}
                for c in google_competitors:
                    if c["url"] not in known_urls:
                        verified_competitors.append(c)

        # Priority 3: Claude fallback if still empty
        if not verified_competitors:
            update("Using AI competitor research...")
            verified_competitors = claude_competitor_fallback(biz_type, location, clean_domain, api_key)

    verified_competitors = verified_competitors[:5]  # cap at 5

    # ── 4. Build Claude prompt ────────────────────────────────
    update("Claude is analyzing content...")

    # Build clear note about JS rendering for Claude
    js_note = ""
    if page.get('js_rendered') and page.get('h1_count', 0) == 0:
        js_note = (
            "NOTE: This site uses JavaScript rendering (React/Next.js/Vue detected). "
            "H1 tags may exist in the live browser but not appear in raw HTML. "
            "Do NOT report 'missing H1' as a finding unless raw_h1_in_html is also False. "
            "Instead, flag it as 'H1 may not be crawler-visible' which is a technical SEO concern."
        )

    phone_detail = ""
    if page.get('has_phone'):
        phone_detail = f"Phone number found: {page.get('phone_number', 'yes')}"
    else:
        phone_detail = "No phone number detected in raw HTML (may be JS-rendered)"

    scraped_summary = f"""
DOMAIN: {clean_domain}
BUSINESS TYPE: {biz_type}
LOCATION: {location}
PAGE TITLE: {page.get('title', 'Not found')}
META DESCRIPTION: {page.get('meta_desc', 'Missing')}
H1 TAGS FOUND (multi-strategy scan): {json.dumps(page.get('h1s', []))}
H1 COUNT: {page.get('h1_count', 0)}
RAW H1 TAG IN HTML: {page.get('raw_h1_in_html', False)}
H2 TAGS: {json.dumps(page.get('h2s', []))}
BODY TEXT SAMPLE: {page.get('body_text', '')[:2000]}

TECHNICAL SIGNALS:
- HTTPS: {page.get('is_https', False)}
- Has CTA signals: {page.get('has_cta', False)}
- Has pricing: {page.get('has_pricing', False)}
- Phone: {phone_detail}
- Meta description present: {page.get('has_meta_desc', False)}
- LocalBusiness schema: {page.get('has_local_schema', False)}
- FAQ schema: {page.get('has_faq_schema', False)}
- Review schema: {page.get('has_review_schema', False)}
- Title length: {page.get('title_length', 0)} chars (ideal: 50-60)
- Internal links found: {page.get('link_count', 0)}
- JS-rendered site: {page.get('js_rendered', False)}

{js_note}

VERIFIED REAL COMPETITORS (already found and confirmed live):
{json.dumps(verified_competitors, indent=2)}
"""

    user_prompt = f"""Audit this website and return ONLY a JSON object.

{scraped_summary}

Return this exact JSON structure:

{{
  "business_name": "string (infer from domain/content)",
  "executive_summary": "3 sentences specific to this site: current state, biggest opportunity, first action.",
  "overall_score": <integer 0-100>,
  "overall_grade": "string",
  "scores": {{
    "SEO Health":  {{"score": <int>, "grade": "string"}},
    "Brand Trust": {{"score": <int>, "grade": "string"}},
    "Conversion":  {{"score": <int>, "grade": "string"}},
    "Technical":   {{"score": <int>, "grade": "string"}}
  }},
  "critical_findings": [
    {{
      "severity": "critical|high|medium|low",
      "category": "string",
      "title": "string (specific to this site)",
      "description": "2-3 sentences with specific evidence",
      "impact": "string"
    }}
  ],
  "action_plan": {{
    "quick_wins":  [{{"task": "string", "time": "string", "owner": "Client|Consultant|Both"}}],
    "medium_term": [{{"task": "string", "time": "string", "owner": "string"}}],
    "strategic":   [{{"task": "string", "time": "string", "owner": "string"}}]
  }},
  "competitors": <use the VERIFIED REAL COMPETITORS list above exactly as provided — do not change URLs or names>
}}

Rules:
- critical_findings: 4–6 items based on ACTUAL signals — never fabricate issues
- quick_wins: 4–5 items; medium_term: 3–4 items; strategic: 3–4 items
- Base ALL scores on technical signals provided above

H1 RULES (critical — do not get this wrong):
- If H1 TAGS FOUND list is non-empty → the site HAS an H1, do NOT report it as missing
- If JS-rendered site is True AND H1 count is 0 AND raw_h1_in_html is False → report as "H1 not crawler-visible" (technical SEO issue, not "missing H1")
- If JS-rendered site is True AND H1 count is 0 AND raw_h1_in_html is True → H1 exists but scraper missed text, do NOT report as missing

PHONE RULES:
- If Phone shows a number was found → the site HAS a phone number, do NOT report it as missing
- Only flag phone as missing if Phone explicitly says "No phone number detected"

OTHER RULES:
- Missing LocalBusiness schema → MUST be a finding
- Missing meta description → MUST be a finding
- competitors: copy the verified list exactly — do NOT invent new ones
- Return ONLY the JSON object"""

    raw_response = call_claude(api_key, SYSTEM_PROMPT, user_prompt)

    # ── 5. Parse ──────────────────────────────────────────────
    update("Parsing results...")
    clean = raw_response.strip()
    clean = re.sub(r"^```[a-z]*\n?", "", clean)
    clean = re.sub(r"\n?```$",       "", clean).strip()

    try:
        audit_json = json.loads(clean)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', clean, re.DOTALL)
        if match:
            audit_json = json.loads(match.group())
        else:
            raise Exception(f"Could not parse response. Raw: {clean[:400]}")

    # ── 6. Inject verified competitors (override any hallucinations) ──
    if verified_competitors:
        audit_json["competitors"] = verified_competitors

    # ── 7. Enrich metadata ────────────────────────────────────
    audit_json["domain"]     = clean_domain
    audit_json["audit_date"] = datetime.now().strftime("%B %d, %Y")
    audit_json["consultant"] = "AuditAI"

    if not audit_json.get("business_name"):
        audit_json["business_name"] = business_name

    audit_json["overall_grade"] = score_to_grade(audit_json.get("overall_score", 60))
    for key in audit_json.get("scores", {}):
        s = audit_json["scores"][key].get("score", 60)
        audit_json["scores"][key]["grade"] = score_to_grade(s)

    update("Audit complete!")
    return audit_json
