from __future__ import annotations

import asyncio
import http.client
import ipaddress
import re
import socket
import ssl
import uuid
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from typing import Any
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

from app.schemas.seo import (
    IssueSeverity,
    SeoAudit,
    SeoIssue,
    SeoPageAnalysis,
    SeoRecommendation,
    SeoSiteSignals,
)
from app.storage.seo_store import SeoAuditStore

USER_AGENT = "VexSeoBot/1.0"
DEFAULT_MAX_PAGES = 25
HARD_MAX_PAGES = 50
DEFAULT_TIMEOUT_SECONDS = 8
MAX_RESPONSE_BYTES = 1_000_000
MAX_FACET_PARAMS = 6
MAX_QUERY_VALUE_LENGTH = 80
BLOCKED_HOSTS = {"localhost", "localhost.localdomain"}


class SeoAuditError(ValueError):
    """Raised for invalid or unsafe SEO audit requests."""


class PinnedHTTPSConnection(http.client.HTTPSConnection):
    """HTTPS connection that dials a vetted IP while preserving SNI."""

    def __init__(
        self,
        host: str,
        pinned_ip: str,
        port: int,
        timeout: int,
        context: ssl.SSLContext,
    ) -> None:
        super().__init__(host, port=port, timeout=timeout, context=context)
        self.pinned_ip = pinned_ip

    def connect(self) -> None:
        raw_socket = socket.create_connection((self.pinned_ip, self.port), self.timeout)
        self.sock = self._context.wrap_socket(raw_socket, server_hostname=self.host)


class PinnedHTTPConnection(http.client.HTTPConnection):
    """HTTP connection that dials a vetted IP while preserving Host."""

    def __init__(self, host: str, pinned_ip: str, port: int, timeout: int) -> None:
        super().__init__(host, port=port, timeout=timeout)
        self.pinned_ip = pinned_ip

    def connect(self) -> None:
        self.sock = socket.create_connection((self.pinned_ip, self.port), self.timeout)


@dataclass(frozen=True)
class FetchResult:
    """Safe HTTP fetch result."""

    url: str
    status_code: int
    content_type: str
    body: bytes
    final_url: str


class SeoHtmlParser(HTMLParser):
    """Small HTML extractor for deterministic SEO analysis."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.meta: list[dict[str, str]] = []
        self.links: list[dict[str, str]] = []
        self.images: list[dict[str, str]] = []
        self.scripts: list[dict[str, str]] = []
        self.html_attrs: dict[str, str] = {}
        self.headings: dict[str, list[str]] = {"h1": [], "h2": [], "h3": []}
        self._capture_tag = ""
        self._capture_parts: list[str] = []
        self._text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value or "" for key, value in attrs}
        tag = tag.lower()
        if tag == "html":
            self.html_attrs = values
        elif tag == "title":
            self._capture_tag = "title"
            self._capture_parts = []
        elif tag in self.headings:
            self._capture_tag = tag
            self._capture_parts = []
        elif tag == "meta":
            self.meta.append(values)
        elif tag == "link":
            self.links.append(values)
        elif tag == "a" and values.get("href"):
            self.links.append({"tag": "a", **values})
        elif tag == "img":
            self.images.append(values)
        elif tag == "script":
            self.scripts.append(values)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self._capture_tag == tag:
            text = _clean_text(" ".join(self._capture_parts))
            if tag == "title":
                self.title = text
            elif tag in self.headings and text:
                self.headings[tag].append(text)
            self._capture_tag = ""
            self._capture_parts = []

    def handle_data(self, data: str) -> None:
        if self._capture_tag:
            self._capture_parts.append(data)
        self._text_parts.append(data)

    def visible_text(self) -> str:
        return _clean_text(" ".join(self._text_parts))


class SeoCrawler:
    """Safe same-domain crawler with SSRF protections."""

    def __init__(
        self,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        max_response_bytes: int = MAX_RESPONSE_BYTES,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_response_bytes = max_response_bytes

    async def crawl(self, start_url: str, max_pages: int = DEFAULT_MAX_PAGES) -> tuple[list[FetchResult], list[str], SeoSiteSignals]:
        capped_max_pages = min(max_pages, HARD_MAX_PAGES)
        normalized_start = normalize_url(start_url)
        self.validate_public_url(normalized_start)
        root_host = urlparse(normalized_start).hostname or ""
        queue: deque[tuple[str, int, str]] = deque([(normalized_start, 0, "")])
        seen: set[str] = set()
        results: list[FetchResult] = []
        errors: list[str] = []
        signals = SeoSiteSignals(
            robots_url=urljoin(normalized_start, "/robots.txt"),
            sitemap_urls=[],
        )

        sitemap_urls = await self.discover_sitemaps(normalized_start, root_host, errors)
        signals.sitemap_urls = sitemap_urls[:20]
        for sitemap_url in sitemap_urls[:10]:
            if len(queue) >= capped_max_pages:
                break
            queue.append((sitemap_url, 1, normalized_start))

        while queue and len(results) < capped_max_pages:
            current_url, depth, source_url = queue.popleft()
            normalized_current = normalize_url(current_url)
            if normalized_current in seen:
                continue
            seen.add(normalized_current)
            try:
                self.validate_public_url(normalized_current)
                if not same_registered_host(root_host, urlparse(normalized_current).hostname or ""):
                    continue
                fetched = await self.fetch(normalized_current)
                final_normalized = normalize_url(fetched.final_url)
                self.validate_public_url(final_normalized)
                if not same_registered_host(root_host, urlparse(final_normalized).hostname or ""):
                    errors.append(f"Redirect left domain: {normalized_current} -> {final_normalized}")
                    continue
                content_type = fetched.content_type.lower()
                if "text/html" not in content_type:
                    continue
                results.append(fetched)
                if len(results) >= capped_max_pages:
                    break
                parser = SeoHtmlParser()
                parser.feed(_decode_body(fetched.body))
                for link in extract_anchor_links(parser, final_normalized, root_host):
                    normalized_link = normalize_url(link)
                    if normalized_link not in seen and len(seen) + len(queue) < capped_max_pages * 3:
                        queue.append((normalized_link, depth + 1, final_normalized))
            except SeoAuditError as exc:
                errors.append(str(exc))
            except Exception as exc:
                errors.append(f"Fetch failed for {normalized_current}: {exc}")
        return results, errors, signals

    async def fetch(self, url: str) -> FetchResult:
        return await asyncio.to_thread(self._fetch_sync, url)

    def _fetch_sync(self, url: str) -> FetchResult:
        current = url
        root_host = urlparse(url).hostname or ""
        for _ in range(6):
            result = self._fetch_once(current)
            final_url = normalize_url(result.final_url)
            self.validate_public_url(final_url)
            if not same_registered_host(root_host, urlparse(final_url).hostname or ""):
                raise SeoAuditError(f"Redirect left domain: {current} -> {final_url}")
            if result.status_code in {301, 302, 303, 307, 308}:
                location = result.content_type
                if not location:
                    raise SeoAuditError(f"Redirect missing location: {current}")
                next_url = normalize_url(urljoin(current, location))
                self.validate_public_url(next_url)
                if not same_registered_host(root_host, urlparse(next_url).hostname or ""):
                    raise SeoAuditError(f"Redirect left domain: {current} -> {next_url}")
                current = next_url
                continue
            return result
        raise SeoAuditError(f"Too many redirects: {url}")

    def _fetch_once(self, url: str) -> FetchResult:
        self.validate_public_url(url)
        parsed = urlparse(url)
        host = parsed.hostname or ""
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        address = choose_public_address(host)
        pinned_ip = str(address)
        path = urlunparse(("", "", parsed.path or "/", "", parsed.query, ""))
        connection: http.client.HTTPConnection
        if parsed.scheme == "https":
            connection = PinnedHTTPSConnection(
                host=host,
                pinned_ip=pinned_ip,
                port=port,
                timeout=self.timeout_seconds,
                context=ssl.create_default_context(),
            )
        else:
            connection = PinnedHTTPConnection(
                host=host,
                pinned_ip=pinned_ip,
                port=port,
                timeout=self.timeout_seconds,
            )
        try:
            connection.request("GET", path, headers={"Host": host, "User-Agent": USER_AGENT})
            response = connection.getresponse()
            peer = connection.sock.getpeername()[0] if connection.sock else str(address)
            peer_address = ipaddress.ip_address(peer)
            if peer_address != address or is_blocked_ip(peer_address):
                raise SeoAuditError(f"Unsafe peer IP blocked for host {host}")
            location = response.getheader("Location") or ""
            if response.status in {301, 302, 303, 307, 308}:
                return FetchResult(
                    url=url,
                    status_code=int(response.status),
                    content_type=location,
                    body=b"",
                    final_url=normalize_url(urljoin(url, location)) if location else url,
                )
            body = response.read(self.max_response_bytes + 1)
            if len(body) > self.max_response_bytes:
                raise SeoAuditError(f"Response too large: {url}")
            return FetchResult(
                url=url,
                status_code=int(response.status),
                content_type=response.getheader("Content-Type") or "",
                body=body,
                final_url=url,
            )
        except OSError as exc:
            raise SeoAuditError(f"Network error for {url}: {exc}") from exc
        finally:
            connection.close()

    async def discover_sitemaps(self, start_url: str, root_host: str, errors: list[str]) -> list[str]:
        robots_url = urljoin(start_url, "/robots.txt")
        found: list[str] = []
        try:
            robots = await self.fetch(robots_url)
            text = _decode_body(robots.body)
            for line in text.splitlines():
                if line.lower().startswith("sitemap:"):
                    sitemap = normalize_url(line.split(":", 1)[1].strip())
                    if same_registered_host(root_host, urlparse(sitemap).hostname or ""):
                        found.append(sitemap)
        except Exception as exc:
            errors.append(f"robots.txt discovery failed: {exc}")
        default_sitemap = urljoin(start_url, "/sitemap.xml")
        if default_sitemap not in found:
            found.append(default_sitemap)
        sitemap_pages: list[str] = []
        for sitemap_url in found[:3]:
            try:
                fetched = await self.fetch(sitemap_url)
                text = _decode_body(fetched.body)
                sitemap_pages.extend(parse_sitemap_urls(text, root_host)[:20])
            except Exception as exc:
                errors.append(f"sitemap discovery failed for {sitemap_url}: {exc}")
        return list(dict.fromkeys(sitemap_pages or found))

    def validate_public_url(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            raise SeoAuditError("Only http and https URLs are allowed")
        host = parsed.hostname
        if not host:
            raise SeoAuditError("URL host is required")
        if host.lower() in BLOCKED_HOSTS or host.lower().endswith(".localhost"):
            raise SeoAuditError("Localhost URLs are blocked")
        addresses = resolve_host(host)
        if not addresses:
            raise SeoAuditError(f"Host could not be resolved: {host}")
        for address in addresses:
            if is_blocked_ip(address):
                raise SeoAuditError(f"Unsafe IP address blocked for host {host}")


class SeoAuditService:
    """Coordinates crawling, analysis, scoring, storage, and exports."""

    def __init__(self, store: SeoAuditStore | None = None, crawler: SeoCrawler | None = None) -> None:
        self.store = store or SeoAuditStore()
        self.crawler = crawler or SeoCrawler()

    async def create_audit(
        self,
        url: str,
        max_pages: int = DEFAULT_MAX_PAGES,
        include_ai_recommendations: bool = False,
    ) -> SeoAudit:
        capped_max_pages = min(max_pages, HARD_MAX_PAGES)
        normalized = normalize_url(url)
        fetches, crawl_errors, signals = await self.crawler.crawl(normalized, capped_max_pages)
        pages = analyze_fetches(fetches)
        site_signals = build_site_signals(pages, signals)
        issues = collect_issues(pages, site_signals, crawl_errors)
        score = score_audit(issues, pages)
        recommendations = build_recommendations(issues)
        ai_recommendations = await self._optional_ai_recommendations(include_ai_recommendations)
        audit = SeoAudit(
            id=f"seo-{uuid.uuid4().hex[:12]}",
            requested_url=url,
            normalized_url=normalized,
            status="completed" if pages else "failed",
            created_at=datetime.now().isoformat(timespec="seconds"),
            max_pages=capped_max_pages,
            crawled_pages=len(pages),
            score=score,
            issues=issues,
            recommendations=recommendations,
            pages=pages,
            site_signals=site_signals,
            crawl_errors=crawl_errors,
            ai_recommendations=ai_recommendations,
            metadata={"traffic_note": "No traffic or volume estimates are generated."},
        )
        self.store.save_audit(audit.model_dump())
        return audit

    def get_audit(self, audit_id: str) -> SeoAudit:
        data = self.store.get_audit(audit_id)
        if not data:
            raise KeyError(audit_id)
        return SeoAudit.model_validate(data)

    def export_json(self, audit_id: str) -> dict[str, Any]:
        return self.get_audit(audit_id).model_dump()

    def export_markdown(self, audit_id: str) -> str:
        return render_markdown(self.get_audit(audit_id))

    def report(self, audit_id: str) -> str:
        return render_markdown(self.get_audit(audit_id))

    async def _optional_ai_recommendations(self, enabled: bool) -> list[SeoRecommendation]:
        if enabled:
            raise SeoAuditError("AI recommendations are not available in this MVP")
        return []


def normalize_url(url: str) -> str:
    parsed = urlparse(str(url).strip())
    if not parsed.scheme:
        raise SeoAuditError("URL scheme is required")
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host:
        raise SeoAuditError("URL host is required")
    port = parsed.port
    netloc = host
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        netloc = f"{host}:{port}"
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    safe_params = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=False):
        key_lower = key.lower()
        if key_lower.startswith("utm_") or key_lower in {"fbclid", "gclid"}:
            continue
        if len(safe_params) >= MAX_FACET_PARAMS or len(value) > MAX_QUERY_VALUE_LENGTH:
            continue
        safe_params.append((key_lower, value))
    query = urlencode(sorted(safe_params))
    return urlunparse((scheme, netloc, path.rstrip("/") or "/", "", query, ""))


def resolve_host(host: str) -> set[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    try:
        return {ipaddress.ip_address(info[4][0]) for info in socket.getaddrinfo(host, None)}
    except socket.gaierror as exc:
        raise SeoAuditError(f"DNS resolution failed for {host}") from exc


def choose_public_address(host: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    addresses = sorted(resolve_host(host), key=lambda address: (address.version, str(address)))
    for address in addresses:
        if not is_blocked_ip(address):
            return address
    raise SeoAuditError(f"Unsafe IP address blocked for host {host}")


def is_blocked_ip(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    metadata = ipaddress.ip_network("169.254.169.254/32")
    return any(
        [
            address.is_private,
            address.is_loopback,
            address.is_link_local,
            address.is_multicast,
            address.is_reserved,
            address.is_unspecified,
            address in metadata,
        ]
    )


def same_registered_host(root_host: str, candidate_host: str) -> bool:
    root = root_host.lower().removeprefix("www.")
    candidate = candidate_host.lower().removeprefix("www.")
    return candidate == root


def parse_sitemap_urls(xml: str, root_host: str) -> list[str]:
    urls = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml, flags=re.IGNORECASE)
    return [normalize_url(url) for url in urls if same_registered_host(root_host, urlparse(url).hostname or "")]


def extract_anchor_links(parser: SeoHtmlParser, base_url: str, root_host: str) -> list[str]:
    links: list[str] = []
    for link in parser.links:
        if link.get("tag") != "a":
            continue
        href = link.get("href", "").strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        try:
            absolute = normalize_url(urljoin(base_url, href))
        except SeoAuditError:
            continue
        if same_registered_host(root_host, urlparse(absolute).hostname or ""):
            links.append(absolute)
    return list(dict.fromkeys(links))


def analyze_fetches(fetches: list[FetchResult]) -> list[SeoPageAnalysis]:
    pages: list[SeoPageAnalysis] = []
    for fetch in fetches:
        parser = SeoHtmlParser()
        parser.feed(_decode_body(fetch.body))
        page = analyze_page(fetch, parser)
        pages.append(page)
    return pages


def analyze_page(fetch: FetchResult, parser: SeoHtmlParser) -> SeoPageAnalysis:
    base_url = normalize_url(fetch.final_url)
    root_host = urlparse(base_url).hostname or ""
    meta_description = first_meta(parser, "description")
    robots = first_meta(parser, "robots")
    canonical = first_link(parser, "canonical", base_url)
    viewport = first_meta(parser, "viewport")
    open_graph = prefixed_meta(parser, "property", "og:")
    twitter = prefixed_meta(parser, "name", "twitter:")
    internal_links: list[str] = []
    external_links: list[str] = []
    for link in parser.links:
        if link.get("tag") != "a" or not link.get("href"):
            continue
        href = link["href"]
        if href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        try:
            absolute = normalize_url(urljoin(base_url, href))
        except SeoAuditError:
            continue
        if same_registered_host(root_host, urlparse(absolute).hostname or ""):
            internal_links.append(absolute)
        else:
            external_links.append(absolute)
    missing_alt = sum(1 for image in parser.images if not image.get("alt", "").strip())
    json_ld_count = sum(1 for script in parser.scripts if script.get("type", "").lower() == "application/ld+json")
    noindex = "noindex" in robots.lower()
    issues = analyze_page_issues(
        base_url,
        parser.title,
        meta_description,
        parser.headings["h1"],
        canonical,
        viewport,
        missing_alt,
        len(parser.images),
        noindex,
    )
    return SeoPageAnalysis(
        url=base_url,
        source_url=fetch.url,
        status_code=fetch.status_code,
        depth=0,
        title=parser.title,
        meta_description=meta_description,
        h1=parser.headings["h1"][:10],
        h2=parser.headings["h2"][:20],
        h3=parser.headings["h3"][:30],
        canonical=canonical,
        robots=robots,
        lang=parser.html_attrs.get("lang", ""),
        word_count=len(re.findall(r"\w+", parser.visible_text())),
        internal_links=list(dict.fromkeys(internal_links))[:100],
        external_links=list(dict.fromkeys(external_links))[:100],
        images_total=len(parser.images),
        images_missing_alt=missing_alt,
        json_ld_count=json_ld_count,
        open_graph=open_graph,
        twitter=twitter,
        viewport=viewport,
        indexable=not noindex and fetch.status_code < 400,
        issues=issues,
    )


def analyze_page_issues(
    url: str,
    title: str,
    description: str,
    h1: list[str],
    canonical: str,
    viewport: str,
    missing_alt: int,
    total_images: int,
    noindex: bool,
) -> list[SeoIssue]:
    issues: list[SeoIssue] = []
    if not title:
        issues.append(issue("P1", "missing_title", "Missing title tag", url, "Add a unique title tag."))
    elif len(title) < 20 or len(title) > 65:
        issues.append(issue("P3", "title_length", "Title length is outside the recommended range", url, "Use a descriptive 20-65 character title."))
    if not description:
        issues.append(issue("P2", "missing_meta_description", "Missing meta description", url, "Add a concise meta description."))
    elif len(description) > 170:
        issues.append(issue("P3", "meta_description_length", "Meta description is long", url, "Keep meta descriptions under 170 characters."))
    if not h1:
        issues.append(issue("P2", "missing_h1", "Missing H1", url, "Add one clear H1 heading."))
    elif len(h1) > 1:
        issues.append(issue("P3", "multiple_h1", "Multiple H1 headings", url, "Use one primary H1 where possible."))
    if not canonical:
        issues.append(issue("P3", "missing_canonical", "Missing canonical link", url, "Add a self-referencing canonical URL."))
    if not viewport:
        issues.append(issue("P2", "missing_viewport", "Missing viewport meta tag", url, "Add a responsive viewport meta tag."))
    if total_images and missing_alt:
        issues.append(issue("P3", "images_missing_alt", "Some images are missing alt text", url, "Add descriptive alt text to meaningful images."))
    if noindex:
        issues.append(issue("P1", "noindex", "Page is marked noindex", url, "Confirm noindex is intentional."))
    return issues


def build_site_signals(pages: list[SeoPageAnalysis], base: SeoSiteSignals) -> SeoSiteSignals:
    title_map: dict[str, list[str]] = {}
    meta_map: dict[str, list[str]] = {}
    missing_titles: list[str] = []
    missing_meta: list[str] = []
    canonical_mismatches: list[str] = []
    broken_links: list[str] = []
    page_urls = {page.url for page in pages}
    for page in pages:
        if page.title:
            title_map.setdefault(page.title.lower(), []).append(page.url)
        else:
            missing_titles.append(page.url)
        if page.meta_description:
            meta_map.setdefault(page.meta_description.lower(), []).append(page.url)
        else:
            missing_meta.append(page.url)
        if page.canonical and normalize_url(page.canonical) != page.url:
            canonical_mismatches.append(page.url)
        for link in page.internal_links:
            if link not in page_urls and len(page_urls) > 1:
                broken_links.append(link)
    return SeoSiteSignals(
        duplicate_titles={key: urls for key, urls in title_map.items() if len(urls) > 1},
        duplicate_meta_descriptions={key: urls for key, urls in meta_map.items() if len(urls) > 1},
        missing_titles=missing_titles,
        missing_meta_descriptions=missing_meta,
        canonical_mismatches=canonical_mismatches,
        broken_links=list(dict.fromkeys(broken_links))[:50],
        robots_url=base.robots_url,
        sitemap_urls=base.sitemap_urls,
    )


def collect_issues(
    pages: list[SeoPageAnalysis], signals: SeoSiteSignals, crawl_errors: list[str]
) -> list[SeoIssue]:
    issues: list[SeoIssue] = []
    for page in pages:
        if page.status_code >= 500:
            issues.append(issue("P0", "server_error", "Server error response", page.url, "Fix 5xx responses."))
        elif page.status_code >= 400:
            issues.append(issue("P1", "client_error", "Client error response", page.url, "Fix broken page responses."))
        issues.extend(page.issues)
    if signals.duplicate_titles:
        issues.append(issue("P2", "duplicate_titles", "Duplicate page titles found", "", "Write unique titles for each indexable page."))
    if signals.duplicate_meta_descriptions:
        issues.append(issue("P2", "duplicate_meta_descriptions", "Duplicate meta descriptions found", "", "Write unique meta descriptions."))
    if signals.canonical_mismatches:
        issues.append(issue("P2", "canonical_mismatch", "Canonical URLs do not match page URLs", "", "Review canonical targets."))
    for error in crawl_errors:
        if "Unsafe IP" in error or "Localhost" in error or "Redirect left domain" in error:
            issues.append(issue("P0", "crawl_security_block", error, "", "Use only public same-domain http/https URLs."))
            break
    return issues


def score_audit(issues: list[SeoIssue], pages: list[SeoPageAnalysis]) -> int:
    score = 100
    weights = {"P0": 30, "P1": 15, "P2": 7, "P3": 3}
    for current in issues:
        score -= weights[current.severity]
    if not pages:
        score -= 40
    return max(0, min(100, score))


def build_recommendations(issues: list[SeoIssue]) -> list[SeoRecommendation]:
    seen: set[str] = set()
    recs: list[SeoRecommendation] = []
    for current in sorted(issues, key=lambda item: item.severity):
        if current.code in seen:
            continue
        seen.add(current.code)
        recs.append(
            SeoRecommendation(
                priority=current.severity,
                title=current.message,
                detail=current.recommendation,
                platform_hint=current.platform_hint,
            )
        )
    return recs


def render_markdown(audit: SeoAudit) -> str:
    lines = [
        f"# SEO Audit Report",
        "",
        f"- Audit ID: `{audit.id}`",
        f"- URL: {audit.normalized_url}",
        f"- Score: {audit.score}/100",
        f"- Crawled pages: {audit.crawled_pages}/{audit.max_pages}",
        "",
        "## Priority Issues",
    ]
    if not audit.issues:
        lines.append("No priority issues found.")
    for current in audit.issues:
        target = f" ({current.url})" if current.url else ""
        lines.append(f"- **{current.severity} {current.code}**: {current.message}{target}")
    lines.extend(["", "## Recommendations"])
    if not audit.recommendations:
        lines.append("No recommendations required.")
    for rec in audit.recommendations:
        lines.append(f"- **{rec.priority} {rec.title}**: {rec.detail} [{rec.platform_hint}]")
    lines.extend(["", "## Pages"])
    for page in audit.pages:
        lines.append(f"- {page.url}: title='{page.title}', h1={len(page.h1)}, words={page.word_count}")
    return "\n".join(lines) + "\n"


def issue(
    severity: IssueSeverity,
    code: str,
    message: str,
    url: str,
    recommendation: str,
    platform_hint: str = "generic",
) -> SeoIssue:
    return SeoIssue(
        severity=severity,
        code=code,
        message=message,
        url=url,
        recommendation=recommendation,
        platform_hint=platform_hint,
    )


def first_meta(parser: SeoHtmlParser, name: str) -> str:
    for meta in parser.meta:
        if meta.get("name", "").lower() == name.lower():
            return meta.get("content", "").strip()
    return ""


def first_link(parser: SeoHtmlParser, rel: str, base_url: str) -> str:
    for link in parser.links:
        if link.get("rel", "").lower() == rel.lower() and link.get("href"):
            try:
                return normalize_url(urljoin(base_url, link["href"]))
            except SeoAuditError:
                return ""
    return ""


def prefixed_meta(parser: SeoHtmlParser, attr: str, prefix: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for meta in parser.meta:
        key = meta.get(attr, "")
        if key.lower().startswith(prefix):
            values[key] = meta.get("content", "")
    return values


def _decode_body(body: bytes) -> str:
    return body.decode("utf-8", errors="replace")


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
