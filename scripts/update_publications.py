#!/usr/bin/env python3
"""Refresh QuantAct publications for members with an explicitly stored ORCID.

Only works present on the member's public ORCID record or explicitly tagged
with that exact ORCID in Crossref are accepted. The script never expands an
ORCID into a third-party author cluster and never searches for people by name.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MEMBERS_PATH = ROOT / "data" / "members.json"
PUBLICATIONS_PATH = ROOT / "data" / "publications.json"
SITE_DATA_PATH = ROOT / "assets" / "site-data.js"
SITE_PUBLICATION_CHUNK_COUNT = 8
MIN_PUBLICATION_YEAR = 2000
ORCID_RE = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$")
USER_AGENT = "quantact-publications-site/1.0"


class IdentityMismatchError(ValueError):
    """The stored ORCID record does not belong to the named member."""


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: dict[str, Any]) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    path.write_text(text, encoding="utf-8")


def browser_publications(publication_doc: dict[str, Any]) -> list[dict[str, Any]]:
    publication_fields = ("title", "journal", "year", "type", "doi", "url", "quantact_members")
    return [
        {field: publication[field] for field in publication_fields if field in publication}
        for publication in filter_publications(publication_doc.get("publications", []))
    ]


def publication_in_scope(publication: dict[str, Any]) -> bool:
    """Return whether a publication belongs in the 2000-present site index."""
    try:
        return int(publication.get("year")) >= MIN_PUBLICATION_YEAR
    except (TypeError, ValueError):
        return False


def filter_publications(publications: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [publication for publication in publications if publication_in_scope(publication)]


def scope_publication_doc(publication_doc: dict[str, Any]) -> dict[str, Any]:
    scoped = publication_doc.copy()
    scoped["minimum_publication_year"] = MIN_PUBLICATION_YEAR
    scoped["publications"] = filter_publications(publication_doc.get("publications", []) or [])
    return scoped


def encode_javascript_json(data: Any) -> str:
    encoded = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return encoded.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def site_data_text(member_doc: dict[str, Any], publication_doc: dict[str, Any]) -> str:
    """Return the small bootstrap bundle used by direct file:// opening."""
    payload = {
        "members": member_doc.get("members", []),
        "publications": [],
        "generated_at": publication_doc.get("generated_at"),
        "minimum_publication_year": MIN_PUBLICATION_YEAR,
    }
    return f"var QUANTACT_SITE_DATA={encode_javascript_json(payload)};\n"


def site_publication_chunk_text(publications: list[dict[str, Any]]) -> str:
    encoded = encode_javascript_json(publications)
    return f"QUANTACT_SITE_DATA.publications.push(...{encoded});\n"


def write_site_data(member_doc: dict[str, Any], publication_doc: dict[str, Any]) -> None:
    SITE_DATA_PATH.write_text(site_data_text(member_doc, publication_doc), encoding="utf-8")
    publications = browser_publications(publication_doc)
    chunk_size = max(1, (len(publications) + SITE_PUBLICATION_CHUNK_COUNT - 1) // SITE_PUBLICATION_CHUNK_COUNT)
    for index in range(SITE_PUBLICATION_CHUNK_COUNT):
        start = index * chunk_size
        chunk = publications[start:start + chunk_size]
        path = ROOT / "assets" / f"site-publications-{index + 1}.js"
        path.write_text(site_publication_chunk_text(chunk), encoding="utf-8")


def valid_orcid(orcid: str) -> bool:
    """Validate ORCID format and ISO 7064 MOD 11-2 check digit."""
    if not ORCID_RE.fullmatch(orcid):
        return False
    digits = orcid.replace("-", "")
    total = 0
    for ch in digits[:15]:
        total = (total + int(ch)) * 2
    remainder = total % 11
    result = (12 - remainder) % 11
    check = "X" if result == 10 else str(result)
    return check == digits[-1]


def normalize_title(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-zA-Z0-9]+", " ", value.lower()).strip()
    return re.sub(r"\s+", " ", value)


def get_json(url: str, retries: int = 3, accept: str = "application/json") -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={"Accept": accept, "User-Agent": USER_AGENT},
        method="GET",
    )
    delay = 2
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            if attempt == retries - 1:
                raise RuntimeError(f"GET failed after {retries} attempts: {url}: {exc}") from exc
            time.sleep(delay)
            delay *= 2
    raise RuntimeError("unreachable")


def normalize_doi(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value.strip(), flags=re.I).lower()
    return normalized or None


def normalize_orcid(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = re.sub(r"^https?://orcid\.org/", "", value.strip(), flags=re.I)
    return normalized or None


def person_names_match(expected: str, observed: str) -> bool:
    """Compare names while tolerating accents, middle initials, and first initials."""
    expected_tokens = normalize_title(expected).split()
    observed_tokens = normalize_title(observed).split()
    if not expected_tokens or not observed_tokens:
        return False
    if expected_tokens == observed_tokens:
        return True
    if expected_tokens[-1] != observed_tokens[-1]:
        return False
    expected_first = expected_tokens[0]
    observed_first = observed_tokens[0]
    return (
        expected_first == observed_first
        or (len(expected_first) == 1 and observed_first.startswith(expected_first))
        or (len(observed_first) == 1 and expected_first.startswith(observed_first))
    )


def orcid_record_names(record: dict[str, Any]) -> list[str]:
    person = record.get("person") or {}
    name = person.get("name") or {}
    candidates: list[str] = []
    given = ((name.get("given-names") or {}).get("value"))
    family = ((name.get("family-name") or {}).get("value"))
    if given and family:
        candidates.append(f"{given} {family}")
    credit_name = ((name.get("credit-name") or {}).get("value"))
    if credit_name:
        candidates.append(credit_name)
    for other_name in ((person.get("other-names") or {}).get("other-name") or []):
        content = other_name.get("content")
        if content:
            candidates.append(content)
    return candidates


def validate_orcid_record_identity(record: dict[str, Any], member_name: str, orcid: str) -> None:
    observed_names = orcid_record_names(record)
    if not any(person_names_match(member_name, observed) for observed in observed_names):
        observed = ", ".join(observed_names) if observed_names else "no public name"
        raise IdentityMismatchError(
            f"stored ORCID {orcid} does not match {member_name}; ORCID record name: {observed}"
        )


def external_id_value(group: dict[str, Any], id_type: str) -> str | None:
    external_ids = (group.get("external-ids") or {}).get("external-id") or []
    for external_id in external_ids:
        if (external_id.get("external-id-type") or "").lower() == id_type.lower():
            value = external_id.get("external-id-value")
            if value:
                return str(value)
    return None


def parse_orcid_work_group(group: dict[str, Any], member_name: str, orcid: str) -> dict[str, Any] | None:
    """Parse a work that is explicitly present on the member's ORCID record."""
    summaries = group.get("work-summary") or []
    if not summaries:
        return None
    summary = summaries[0]
    title = (((summary.get("title") or {}).get("title") or {}).get("value") or "Untitled")
    journal = ((summary.get("journal-title") or {}).get("value"))
    year_value = ((((summary.get("publication-date") or {}).get("year") or {}).get("value")))
    try:
        year = int(year_value) if year_value is not None else None
    except (TypeError, ValueError):
        year = None
    doi = normalize_doi(external_id_value(group, "doi"))
    explicit_url = ((summary.get("url") or {}).get("value"))
    external_ids = (group.get("external-ids") or {}).get("external-id") or []
    external_url = next(
        (
            (external_id.get("external-id-url") or {}).get("value")
            for external_id in external_ids
            if (external_id.get("external-id-url") or {}).get("value")
        ),
        None,
    )
    return {
        "title": title,
        "journal": journal,
        "year": year,
        "type": summary.get("type"),
        "doi": doi,
        "url": f"https://doi.org/{doi}" if doi else (explicit_url or external_url),
        "quantact_members": [member_name],
        "orcid_ids": [orcid],
        "source": "ORCID public record",
    }


def fetch_orcid(orcid: str, member_name: str) -> list[dict[str, Any]]:
    payload = get_json(
        f"https://pub.orcid.org/v3.0/{orcid}/record",
        accept="application/vnd.orcid+json",
    )
    validate_orcid_record_identity(payload, member_name, orcid)
    results: list[dict[str, Any]] = []
    groups = (((payload.get("activities-summary") or {}).get("works") or {}).get("group") or [])
    for group in groups:
        publication = parse_orcid_work_group(group, member_name, orcid)
        if publication:
            results.append(publication)
    return results


def crossref_date(item: dict[str, Any]) -> int | None:
    for field in ("published-print", "published-online", "issued", "created"):
        parts = ((item.get(field) or {}).get("date-parts") or [])
        if parts and parts[0]:
            try:
                return int(parts[0][0])
            except (TypeError, ValueError, IndexError):
                pass
    return None


def crossref_item_has_member_orcid(item: dict[str, Any], member_name: str, orcid: str) -> bool:
    return any(
        normalize_orcid(author.get("ORCID") or author.get("orcid")) == orcid
        and person_names_match(
            member_name,
            " ".join(part for part in (author.get("given"), author.get("family")) if part),
        )
        for author in item.get("author", []) or []
    )


def parse_crossref_item(item: dict[str, Any], member_name: str, orcid: str) -> dict[str, Any] | None:
    """Accept a Crossref work only when an author carries the exact ORCID."""
    if not crossref_item_has_member_orcid(item, member_name, orcid):
        return None
    title_field = item.get("title") or []
    journal_field = item.get("container-title") or []
    doi = normalize_doi(item.get("DOI"))
    return {
        "title": title_field[0] if title_field else "Untitled",
        "journal": journal_field[0] if journal_field else None,
        "year": crossref_date(item),
        "type": item.get("type"),
        "doi": doi,
        "url": item.get("URL") or (f"https://doi.org/{doi}" if doi else None),
        "quantact_members": [member_name],
        "orcid_ids": [orcid],
        "source": "Crossref (exact ORCID)",
    }


def fetch_crossref(orcid: str, member_name: str) -> list[dict[str, Any]]:
    query = urllib.parse.urlencode({"filter": f"orcid:{orcid}", "rows": "1000"})
    payload = get_json(f"https://api.crossref.org/works?{query}")
    results: list[dict[str, Any]] = []
    for item in ((payload.get("message") or {}).get("items") or []):
        publication = parse_crossref_item(item, member_name, orcid)
        if publication:
            results.append(publication)
    return results


def fetch_publications(orcid: str, member_name: str) -> list[dict[str, Any]]:
    # Both calls must complete so a temporary outage cannot erase records that
    # are available from only one exact-ORCID source.
    orcid_works = fetch_orcid(orcid, member_name)
    crossref_works = fetch_crossref(orcid, member_name)
    return orcid_works + crossref_works


def publication_key(publication: dict[str, Any]) -> str:
    doi = (publication.get("doi") or "").strip().lower()
    if doi:
        return "doi:" + doi
    return "title:" + normalize_title(publication.get("title") or "") + f":{publication.get('year') or ''}"


def merge_publications(publications: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for publication in publications:
        key = publication_key(publication)
        if key not in merged:
            merged[key] = publication.copy()
            merged[key]["quantact_members"] = list(publication.get("quantact_members", []))
            merged[key]["orcid_ids"] = list(publication.get("orcid_ids", []))
            continue
        existing = merged[key]
        for field in ("journal", "year", "type", "doi", "url"):
            if not existing.get(field) and publication.get(field):
                existing[field] = publication[field]
        existing["quantact_members"] = sorted(set(existing.get("quantact_members", [])) | set(publication.get("quantact_members", [])))
        existing["orcid_ids"] = sorted(set(existing.get("orcid_ids", [])) | set(publication.get("orcid_ids", [])))

    values = list(merged.values())
    values.sort(key=lambda p: (p.get("year") or 0, normalize_title(p.get("title") or "")), reverse=True)
    return values


def validate_members(members: list[dict[str, Any]]) -> None:
    seen_names: set[str] = set()
    seen_orcids: dict[str, str] = {}
    errors: list[str] = []
    for member in members:
        name = (member.get("name") or "").strip()
        institution = (member.get("institution") or "").strip()
        orcid = member.get("orcid")
        if not name or not institution:
            errors.append(f"Member missing name/institution: {member!r}")
            continue
        if name in seen_names:
            errors.append(f"Duplicate member name: {name}")
        seen_names.add(name)
        if orcid:
            if not valid_orcid(orcid):
                errors.append(f"Invalid ORCID for {name}: {orcid}")
            if orcid in seen_orcids and seen_orcids[orcid] != name:
                errors.append(f"ORCID {orcid} assigned to both {seen_orcids[orcid]} and {name}")
            seen_orcids[orcid] = name
    if errors:
        raise ValueError("\n".join(errors))


def refresh() -> int:
    member_doc = load_json(MEMBERS_PATH)
    members = member_doc.get("members", [])
    validate_members(members)

    previous_doc = load_json(PUBLICATIONS_PATH) if PUBLICATIONS_PATH.exists() else {"generated_at": None, "publications": []}
    previous = previous_doc.get("publications", []) or []
    previous_by_member: dict[str, list[dict[str, Any]]] = {}
    for publication in previous:
        for name in publication.get("quantact_members", []) or []:
            previous_by_member.setdefault(name, []).append(publication)

    all_publications: list[dict[str, Any]] = []
    successes = 0
    failures = 0
    linked = [m for m in members if m.get("orcid")]

    for index, member in enumerate(linked, start=1):
        name = member["name"]
        orcid = member["orcid"]
        print(f"[{index}/{len(linked)}] {name} — {orcid}")
        try:
            works = fetch_publications(orcid, name)
            all_publications.extend(works)
            successes += 1
            print(f"  fetched {len(works)} exact-ORCID works")
        except IdentityMismatchError as exc:
            failures += 1
            print(f"  identity error: {exc}", file=sys.stderr)
        except Exception as exc:  # preserve last known good data on transient/API failures
            failures += 1
            print(f"  warning: {exc}", file=sys.stderr)
            if previous_by_member.get(name):
                all_publications.extend(previous_by_member[name])
                print(f"  preserved {len(previous_by_member[name])} previous records")

    merged = merge_publications(filter_publications(all_publications))
    if successes:
        generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    else:
        generated_at = previous_doc.get("generated_at")

    output = {
        "generated_at": generated_at,
        "member_count": len(members),
        "orcid_linked_count": len(linked),
        "minimum_publication_year": MIN_PUBLICATION_YEAR,
        "refresh": {"successful_orcid_records": successes, "failed_orcid_records": failures},
        "publications": merged,
    }
    write_json(PUBLICATIONS_PATH, output)
    write_site_data(member_doc, output)
    print(f"Wrote {len(merged)} deduplicated publications to {PUBLICATIONS_PATH}")
    print(f"Wrote browser data bundle to {SITE_DATA_PATH}")
    return 0


def build_site_data() -> int:
    member_doc = load_json(MEMBERS_PATH)
    publication_doc = scope_publication_doc(load_json(PUBLICATIONS_PATH))
    validate_members(member_doc.get("members", []))
    write_json(PUBLICATIONS_PATH, publication_doc)
    write_site_data(member_doc, publication_doc)
    print(f"Wrote browser data bundle to {SITE_DATA_PATH}")
    return 0


def check() -> int:
    member_doc = load_json(MEMBERS_PATH)
    members = member_doc.get("members", [])
    validate_members(members)
    print(f"OK: {len(members)} members; {sum(bool(m.get('orcid')) for m in members)} ORCID-linked")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--check", action="store_true", help="validate local member data without network requests")
    action.add_argument("--build-site-data", action="store_true", help="rebuild browser data files without network requests")
    args = parser.parse_args()
    try:
        if args.check:
            return check()
        if args.build_site_data:
            return build_site_data()
        return refresh()
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
