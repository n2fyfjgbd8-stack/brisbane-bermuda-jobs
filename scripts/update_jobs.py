#!/usr/bin/env python3
"""Fetch publicly indexed, currently active IT jobs for Brisbane and Bermuda.

No paid dependencies, no scraping, no authentication required. Source attribution
and verification metadata are retained. The site explicitly distinguishes
historical leads and live-feed records.
"""
import datetime
import hashlib
import html
import json
import os
import pathlib
import re
import urllib.parse
import urllib.request

OUT = pathlib.Path(__file__).resolve().parents[1] / "docs" / "jobs.json"
NOW = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
TITLE_TERMS = (
    "infrastructure", "systems engineer", "system engineer",
    "systems administrator", "system administrator", "network engineer",
    "network administrator", "cloud engineer", "azure engineer",
    "it engineer", "it support engineer", "platform engineer",
    "desktop engineer", "technical support engineer", "it administrator",
    "it infrastructure", "it operations engineer", "site reliability engineer",
)
EXCLUDE_TITLES = ("intern", "internship", "graduate", "apprentice", "director", "head of", "chief ")
jobs = {}
errors = []
sources = []

def fetch_json(url):
    request = urllib.request.Request(url, headers={
        "User-Agent": "BrisbaneBermudaPersonalJobSearch/1.1",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(request, timeout=22) as response:
        return json.load(response)

def plain(value):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", str(value or "")))).strip()

def matching_region(location, country=""):
    text = (str(location or "") + " " + str(country or "")).lower()
    if "bermuda" in text or re.search(r"\bhamilton,?\s*(bm|bermuda)\b", text):
        return "Bermuda"
    if "brisbane" in text or "greater brisbane" in text:
        return "Brisbane"
    return None

def add(title, company, location, url, source, salary="", posted="",
        description="", country="", employment="", verified="", attribution="", status="active"):
    region = matching_region(location, country)
    lower = plain(title).lower()
    if not region or not any(term in lower for term in TITLE_TERMS):
        return
    if any(term in lower for term in EXCLUDE_TITLES):
        return
    jobtype = str(employment or "").lower()
    if any(x in jobtype for x in ("contract", "temporary", "freelance", "internship")):
        return
    if not isinstance(url, str) or not url.startswith("https://"):
        return
    if str(status).lower() not in ("active", "open", "published"):
        return
    uid = hashlib.sha256(url.encode()).hexdigest()[:16]
    jobs[uid] = {
        "id": uid,
        "title": plain(title),
        "company": plain(company) or "Employer not specified",
        "location": plain(location),
        "country": region,
        "url": url,
        "source": source,
        "salary": plain(salary) or "Not disclosed",
        "posted": str(posted or ""),
        "employment": plain(employment) or "Permanent status unconfirmed",
        "verified": str(verified or ""),
        "visa": "Not confirmed",
        "attribution": plain(attribution) or source,
        "description": plain(description)[:350],
    }

# PeopleSeek provides active job verification, location filtering and direct
# application links. It is a public, no-key API (see developers/api).
for region in ("Brisbane", "Bermuda"):
    for term in ("infrastructure engineer", "systems engineer", "network engineer", "cloud engineer", "system administrator", "IT support engineer"):
        params = {"q": term, "city": region if region == "Brisbane" else "",
                  "country": "BM" if region == "Bermuda" else "AU",
                  "limit": 50}
        if not params["city"]:
            del params["city"]
        url = "https://jobs.peopleseek.ai/api/v1/jobs?" + urllib.parse.urlencode(params)
        try:
            payload = fetch_json(url)
            if not payload.get("ok"):
                raise ValueError(str(payload.get("error", "API declined query"))[:120])
            for x in payload.get("data", {}).get("jobs", []):
                if not isinstance(x, dict):
                    continue
                loc = x.get("location", {})
                if isinstance(loc, dict):
                    location = ", ".join(str(loc[k]) for k in ("city", "region", "country") if loc.get(k))
                else:
                    location = str(loc or "")
                if not location:
                    locations = x.get("locations", [])
                    if isinstance(locations, list):
                        location = ", ".join(str(i.get("city") or i.get("displayName") or "") for i in locations if isinstance(i, dict))
                comp = x.get("company") or {}
                src = x.get("source") or {}
                ver = x.get("verification") or {}
                pay = x.get("compensation") or {}
                if not isinstance(comp, dict): comp = {"name": str(comp)}
                if not isinstance(src, dict): src = {"name": str(src)}
                if not isinstance(ver, dict): ver = {}
                if not isinstance(pay, dict): pay = {}
                money = x.get("salary") or pay.get("displayText") or pay.get("formatted")
                add(x.get("title", ""), comp.get("name", ""),
                    location, x.get("applyUrl") or x.get("canonicalUrl") or "",
                    src.get("name") or "PeopleSeek",
                    salary=money or "", posted=x.get("postedAt") or x.get("datePosted") or "",
                    description=x.get("description") or x.get("summary") or "",
                    country=region if region == "Bermuda" else "",
                    employment=x.get("employmentType") or "",
                    verified=ver.get("lastVerifiedAt") or "",
                    attribution=src.get("attributionText") or src.get("name") or "PeopleSeek",
                    status=ver.get("status") or "active")
            sources.append("PeopleSeek")
        except Exception as exc:
            errors.append("PeopleSeek (" + region + ", " + term + "): " + str(exc)[:100])

# Optional Adzuna Australian listings (free API credentials supplied by owner).
app = os.environ.get("ADZUNA_APP_ID")
key = os.environ.get("ADZUNA_APP_KEY")
if app and key:
    for term in ("infrastructure engineer", "systems engineer", "network engineer", "cloud engineer"):
        try:
            params = {"app_id": app, "app_key": key, "results_per_page": 50,
                      "what": term, "where": "Brisbane", "content-type": "application/json",
                      "sort_by": "date"}
            url = "https://api.adzuna.com/v1/api/jobs/au/search/1?" + urllib.parse.urlencode(params)
            response = fetch_json(url)
            for x in response.get("results", []):
                loc = (x.get("location") or {}).get("display_name", "")
                sal = ("AUD " + str(round(x["salary_min"])) if x.get("salary_min") else "")
                add(x.get("title", ""), (x.get("company") or {}).get("display_name", ""),
                    loc, x.get("redirect_url", ""), "Adzuna", salary=sal,
                    posted=x.get("created", ""), description=x.get("description", ""))
            sources.append("Adzuna")
        except Exception as exc:
            errors.append("Adzuna (" + term + "): " + str(exc)[:120])
else:
    errors.append("Optional Adzuna API credentials are not configured")

previous = {}
if OUT.exists():
    try:
        previous = json.loads(OUT.read_text(encoding="utf-8"))
    except Exception:
        pass
if not jobs and previous.get("jobs"):
    # Never silently replace a populated feed with empty results following an outage.
    payload = {**previous, "lastAttempt": NOW, "fetchErrors": errors, "stale": True}
else:
    payload = {"lastUpdated": NOW, "lastAttempt": NOW, "stale": False,
               "sources": sorted(set(sources)), "fetchErrors": errors,
               "jobs": sorted(jobs.values(), key=lambda x: x.get("posted", ""), reverse=True)}
OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print("Job records:", len(payload["jobs"]), "Sources:", payload.get("sources"), "Errors:", len(errors))
