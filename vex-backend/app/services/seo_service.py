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
from html import unescape
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
    PageType,
)
from app.storage.seo_store import SeoAuditStore

USER_AGENT = "VexSeoBot/1.0"
DEFAULT_MAX_PAGES = 100
HARD_MAX_PAGES = 500
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

    EXCLUDED_TEXT_TAGS = {"script", "style", "noscript", "template", "svg", "head"}
    LOW_VALUE_TEXT_TAGS = {"nav", "footer", "header", "aside"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.meta: list[dict[str, str]] = []
        self.links: list[dict[str, str]] = []
        self.images: list[dict[str, str]] = []
        self.scripts: list[dict[str, str]] = []
        self.html_attrs: dict[str, str] = {}
        self.headings: dict[str, list[str]] = {"h1": [], "h2": [], "h3": []}
        self._tag_stack: list[str] = []
        self._capture_tag = ""
        self._capture_parts: list[str] = []
        self._main_text_parts: list[str] = []
        self._fallback_text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value or "" for key, value in attrs}
        tag = tag.lower()
        self._tag_stack.append(tag)
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
        if tag in self._tag_stack:
            while self._tag_stack:
                popped = self._tag_stack.pop()
                if popped == tag:
                    break

    def handle_data(self, data: str) -> None:
        if self._capture_tag:
            self._capture_parts.append(data)
        if self._is_text_excluded():
            return
        cleaned = _clean_text(data)
        if not cleaned:
            return
        if self._is_low_value_text():
            self._fallback_text_parts.append(cleaned)
        else:
            self._main_text_parts.append(cleaned)

    def visible_text(self) -> str:
        parts = self._main_text_parts or self._fallback_text_parts
        return _clean_text(" ".join(parts))

    def _is_text_excluded(self) -> bool:
        return any(tag in self.EXCLUDED_TEXT_TAGS for tag in self._tag_stack)

    def _is_low_value_text(self) -> bool:
        return any(tag in self.LOW_VALUE_TEXT_TAGS for tag in self._tag_stack)


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
        queue: deque[tuple[str, int, str]] = deque()
        seen: set[str] = set()
        queued: set[str] = set()
        results: list[FetchResult] = []
        errors: list[str] = []
        skipped_urls = 0
        blocked_urls = 0
        signals = SeoSiteSignals(
            robots_url=urljoin(normalized_start, "/robots.txt"),
            sitemap_urls=[],
        )

        sitemap_urls = await self.discover_sitemaps(normalized_start, root_host, errors)
        signals.sitemap_urls = sitemap_urls[:100]
        for sitemap_url in sitemap_urls:
            if len(queued) >= capped_max_pages * 3:
                break
            if sitemap_url not in queued:
                queue.append((sitemap_url, 1, normalized_start))
                queued.add(sitemap_url)
        if normalized_start not in queued:
            queue.appendleft((normalized_start, 0, ""))
            queued.add(normalized_start)

        while queue and len(results) < capped_max_pages:
            current_url, depth, source_url = queue.popleft()
            normalized_current = normalize_url(current_url)
            if normalized_current in seen:
                skipped_urls += 1
                continue
            seen.add(normalized_current)
            try:
                self.validate_public_url(normalized_current)
                if not same_registered_host(root_host, urlparse(normalized_current).hostname or ""):
                    skipped_urls += 1
                    continue
                fetched = await self.fetch(normalized_current)
                final_normalized = normalize_url(fetched.final_url)
                self.validate_public_url(final_normalized)
                if not same_registered_host(root_host, urlparse(final_normalized).hostname or ""):
                    blocked_urls += 1
                    errors.append(f"Redirect left domain: {normalized_current} -> {final_normalized}")
                    continue
                content_type = fetched.content_type.lower()
                if "text/html" not in content_type:
                    skipped_urls += 1
                    continue
                results.append(fetched)
                if len(results) >= capped_max_pages:
                    break
                parser = SeoHtmlParser()
                parser.feed(_decode_body(fetched.body))
                for link in extract_anchor_links(parser, final_normalized, root_host):
                    normalized_link = normalize_url(link)
                    if normalized_link not in seen and normalized_link not in queued and len(queued) < capped_max_pages * 3:
                        queue.append((normalized_link, depth + 1, final_normalized))
                        queued.add(normalized_link)
                    elif normalized_link in seen or normalized_link in queued:
                        skipped_urls += 1
            except SeoAuditError as exc:
                if "Unsafe IP" in str(exc) or "Localhost" in str(exc) or "Redirect left domain" in str(exc):
                    blocked_urls += 1
                else:
                    errors.append(str(exc))
            except Exception as exc:
                errors.append(f"Fetch failed for {normalized_current}: {exc}")
        signals.discovered_urls = len(queued)
        signals.crawled_urls = len(results)
        signals.skipped_urls = skipped_urls
        signals.blocked_urls = blocked_urls
        signals.errored_urls = len(errors)
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
                sitemap_pages.extend(parse_sitemap_urls(text, root_host)[:HARD_MAX_PAGES])
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
        country: str = "",
        language: str = "",
        business_description: str = "",
        include_ai_recommendations: bool = False,
    ) -> SeoAudit:
        capped_max_pages = min(max_pages, HARD_MAX_PAGES)
        normalized = normalize_url(url)
        fetches, crawl_errors, signals = await self.crawler.crawl(normalized, capped_max_pages)
        pages = analyze_fetches(fetches)
        site_signals = build_site_signals(pages, signals)
        issues = collect_issues(pages, site_signals, crawl_errors)
        score = score_audit(issues, pages)
        site_signals.score_reasons = score_reasons(issues, pages)
        recommendations = build_recommendations(issues, language, business_description)
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
            metadata={
                "traffic_note": "No traffic or volume estimates are generated.",
                "targeting": {
                    "country": country,
                    "language": language,
                    "business_description": business_description,
                },
                "mspovleceni_reference": {
                    "previous_title": "missing_title/boş veya hatalı",
                    "new_title_expected": "mSpovleceni | Nakupujte kvalitní povlečení a bytový textil online",
                    "page_limit_previous": 50,
                    "page_limit_new": HARD_MAX_PAGES,
                },
            },
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
    html_text = _decode_body(fetch.body)
    meta_description = first_meta(parser, "description")
    robots = first_meta(parser, "robots")
    canonical = first_link(parser, "canonical", base_url)
    viewport = first_meta(parser, "viewport")
    open_graph = prefixed_meta(parser, "property", "og:")
    twitter = prefixed_meta(parser, "name", "twitter:")
    page_type = classify_page_type(base_url, parser)
    platform, _confidence = detect_platform(html_text, parser)
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
    visible_words = visible_word_count(parser.visible_text())
    issues = analyze_page_issues(
        base_url,
        page_type,
        parser.title,
        meta_description,
        parser.headings["h1"],
        canonical,
        viewport,
        missing_alt,
        len(parser.images),
        noindex,
        visible_words,
        platform,
    )
    page_score, score_reasons = score_page(issues, page_type)
    return SeoPageAnalysis(
        url=base_url,
        source_url=fetch.url,
        status_code=fetch.status_code,
        depth=0,
        page_type=page_type,
        page_score=page_score,
        platform=platform,
        score_reasons=score_reasons,
        title=parser.title,
        meta_description=meta_description,
        h1=parser.headings["h1"][:10],
        h2=parser.headings["h2"][:20],
        h3=parser.headings["h3"][:30],
        canonical=canonical,
        robots=robots,
        lang=parser.html_attrs.get("lang", ""),
        word_count=visible_words,
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
    page_type: str,
    title: str,
    description: str,
    h1: list[str],
    canonical: str,
    viewport: str,
    missing_alt: int,
    total_images: int,
    noindex: bool,
    word_count: int,
    platform: str,
) -> list[SeoIssue]:
    issues: list[SeoIssue] = []
    utility = is_utility_page(page_type)
    platform_hint = platform if platform != "unknown" else "generic"
    if not title:
        issues.append(issue("P1", "missing_title", "Missing title tag", url, "Add a unique title tag.", platform_hint, "Bulunamadı", page_type))
    elif not utility and (len(title) < 20 or len(title) > 70):
        issues.append(issue("P3", "title_length", "Title length is outside the recommended range", url, "Use a descriptive 20-70 character title.", platform_hint, title, page_type))
    if not description and not utility:
        issues.append(issue("P2", "missing_meta_description", "Missing meta description", url, "Add a concise meta description.", platform_hint, "Bulunamadı", page_type))
    elif description and len(description) > 170:
        issues.append(issue("P3", "meta_description_length", "Meta description is long", url, "Keep meta descriptions under 170 characters.", platform_hint, description, page_type))
    if not h1 and not utility:
        issues.append(issue("P2", "missing_h1", "Missing H1", url, "Add one clear H1 heading.", platform_hint, "Bulunamadı", page_type))
    elif len(h1) > 1:
        issues.append(issue("P3", "multiple_h1", "Multiple H1 headings", url, "Use one primary H1 where possible.", platform_hint, " / ".join(h1[:3]), page_type))
    if not canonical:
        issues.append(issue("P3", "missing_canonical", "Missing canonical link", url, "Add a self-referencing canonical URL.", platform_hint, "Bulunamadı", page_type))
    if not viewport:
        issues.append(issue("P2", "missing_viewport", "Missing viewport meta tag", url, "Add a responsive viewport meta tag.", platform_hint, "Bulunamadı", page_type))
    if not utility and page_type in {"homepage", "collection", "product", "blog/article", "content page"} and word_count < 80:
        issues.append(issue("P3", "thin_visible_content", "Visible content is thin", url, "Add useful visible copy for users and search engines.", platform_hint, str(word_count), page_type))
    if total_images and missing_alt:
        issues.append(issue("P3", "images_missing_alt", "Some images are missing alt text", url, "Add descriptive alt text to meaningful images.", platform_hint, f"{missing_alt}/{total_images} missing", page_type))
    if noindex and not utility:
        issues.append(issue("P1", "noindex", "Page is marked noindex", url, "Confirm noindex is intentional.", platform_hint, "noindex", page_type))
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
    platform, confidence = aggregate_platform(pages)
    page_type_counts: dict[str, int] = {}
    for page in pages:
        page_type_counts[page.page_type] = page_type_counts.get(page.page_type, 0) + 1
    return SeoSiteSignals(
        duplicate_titles={key: urls for key, urls in title_map.items() if len(urls) > 1},
        duplicate_meta_descriptions={key: urls for key, urls in meta_map.items() if len(urls) > 1},
        missing_titles=missing_titles,
        missing_meta_descriptions=missing_meta,
        canonical_mismatches=canonical_mismatches,
        broken_links=list(dict.fromkeys(broken_links))[:50],
        robots_url=base.robots_url,
        sitemap_urls=base.sitemap_urls,
        discovered_urls=base.discovered_urls,
        crawled_urls=len(pages),
        skipped_urls=base.skipped_urls,
        blocked_urls=base.blocked_urls,
        errored_urls=base.errored_urls,
        platform=platform,
        platform_confidence=confidence,
        page_type_counts=page_type_counts,
    )


def collect_issues(
    pages: list[SeoPageAnalysis], signals: SeoSiteSignals, crawl_errors: list[str]
) -> list[SeoIssue]:
    issues: list[SeoIssue] = []
    for page in pages:
        if page.status_code >= 500:
            issues.append(issue("P0", "server_error", "Server error response", page.url, "Fix 5xx responses.", page.platform, str(page.status_code), page.page_type))
        elif page.status_code >= 400:
            issues.append(issue("P1", "client_error", "Client error response", page.url, "Fix broken page responses.", page.platform, str(page.status_code), page.page_type))
        issues.extend(page.issues)
    if signals.duplicate_titles:
        issues.append(issue("P2", "duplicate_titles", "Duplicate page titles found", "", "Write unique titles for each indexable page.", signals.platform, str(len(signals.duplicate_titles)), "site", "site"))
    if signals.duplicate_meta_descriptions:
        issues.append(issue("P2", "duplicate_meta_descriptions", "Duplicate meta descriptions found", "", "Write unique meta descriptions.", signals.platform, str(len(signals.duplicate_meta_descriptions)), "site", "site"))
    if signals.canonical_mismatches:
        issues.append(issue("P2", "canonical_mismatch", "Canonical URLs do not match page URLs", "", "Review canonical targets.", signals.platform, str(len(signals.canonical_mismatches)), "site", "site"))
    for error in crawl_errors:
        if "Unsafe IP" in error or "Localhost" in error or "Redirect left domain" in error:
            issues.append(issue("P0", "crawl_security_block", error, "", "Use only public same-domain http/https URLs.", "generic", error, "unknown", "crawl"))
            break
    return issues


def score_audit(issues: list[SeoIssue], pages: list[SeoPageAnalysis]) -> int:
    if not pages:
        return 0
    commercial_pages = [page for page in pages if not is_utility_page(page.page_type)] or pages
    average_page_score = sum(page.page_score or 0 for page in commercial_pages) / len(commercial_pages)
    site_issues = [current for current in issues if current.scope in {"site", "crawl"}]
    score = average_page_score
    seen_codes: set[str] = set()
    weights = {"P0": 18, "P1": 9, "P2": 4, "P3": 1}
    for current in site_issues:
        if current.code in seen_codes and current.severity != "P0":
            continue
        seen_codes.add(current.code)
        score -= weights[current.severity]
    return max(0, min(100, round(score)))


def score_page(issues: list[SeoIssue], page_type: str) -> tuple[int, list[str]]:
    score = 100
    reasons: list[str] = []
    weights = {"P0": 30, "P1": 15, "P2": 8, "P3": 3}
    multiplier = 0.35 if is_utility_page(page_type) else 1.0
    for current in issues:
        loss = max(1, round(weights[current.severity] * multiplier))
        score -= loss
        reasons.append(f"-{loss}: {current.code} ({current.severity})")
    return max(0, min(100, score)), reasons


def score_reasons(issues: list[SeoIssue], pages: list[SeoPageAnalysis]) -> list[str]:
    reasons: list[str] = []
    commercial_pages = [page for page in pages if not is_utility_page(page.page_type)] or pages
    if commercial_pages:
        average = sum(page.page_score or 0 for page in commercial_pages) / len(commercial_pages)
        reasons.append(f"Commercial page average: {round(average)} across {len(commercial_pages)} pages")
    weights = {"P0": 18, "P1": 9, "P2": 4, "P3": 1}
    seen_codes: set[str] = set()
    for current in issues:
        if current.scope not in {"site", "crawl"}:
            continue
        if current.code in seen_codes and current.severity != "P0":
            continue
        seen_codes.add(current.code)
        reasons.append(f"-{weights[current.severity]}: {current.code} ({current.severity}, {current.scope})")
    return reasons


def build_recommendations(
    issues: list[SeoIssue], language: str = "", business_description: str = ""
) -> list[SeoRecommendation]:
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
                detail=localized_recommendation(current, language, business_description),
                platform_hint=current.platform_hint,
            )
        )
    return recs


def localized_recommendation(
    current: SeoIssue, language: str = "", business_description: str = ""
) -> str:
    target_language = language.strip() or "seçilen dil"
    context = business_description.strip()
    context_sentence = f" İş bağlamı: {context}." if context else ""
    detail = current.recommendation
    if target_language.casefold() in {"czech", "čeština", "česky", "cz", "cs"}:
        return (
            f"Heuristic öneri: Bu sayfa için başlık/meta/H1 ve içerik başlıklarını Çekçe "
            f"hazırla; gerçek mevcut değeri temel al: {current.current_value}. {detail}"
            f"{context_sentence} Arama hacmi, trafik veya sıralama verisi üretilmedi."
        )
    return (
        f"Heuristic öneri: İçeriği {target_language} hedef dilinde, sayfaya özel mevcut "
        f"değere göre güncelle: {current.current_value}. {detail}{context_sentence} "
        "Arama hacmi, trafik veya sıralama verisi üretilmedi."
    )


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
    current_value: str = "",
    page_type: str = "unknown",
    scope: str = "page",
) -> SeoIssue:
    return SeoIssue(
        severity=severity,
        code=code,
        message=message,
        url=url,
        recommendation=shopify_recommendation(recommendation, platform_hint) if "Shopify" in platform_hint else recommendation,
        platform_hint=platform_hint,
        current_value=current_value or "Bulunamadı",
        page_type=page_type,
        scope=scope,
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


def classify_page_type(url: str, parser: SeoHtmlParser) -> PageType:
    parsed = urlparse(url)
    path = parsed.path.lower().rstrip("/") or "/"
    query = parsed.query.lower()
    og_type = next((meta.get("content", "").lower() for meta in parser.meta if meta.get("property", "").lower() == "og:type"), "")
    if path == "/":
        return "homepage"
    if any(part in path for part in ["/cart", "/checkout"]):
        return "cart"
    if any(part in path for part in ["/account", "/login", "/register"]):
        return "account"
    if "search" in path or "q=" in query:
        return "search"
    if any(part in path for part in ["policy", "privacy", "terms", "obchodni-podminky", "gdpr"]):
        return "policy"
    if "/products/" in path or og_type == "product":
        return "product"
    if "/collections/" in path or "/category/" in path or "/collections" == path:
        return "collection"
    if "/blogs/" in path or "/blog/" in path or og_type == "article":
        return "blog/article"
    if path != "/":
        return "content page"
    return "unknown"


def is_utility_page(page_type: str) -> bool:
    return page_type in {"cart", "account", "policy", "search"}


def detect_platform(html_text: str, parser: SeoHtmlParser) -> tuple[str, str]:
    lower = html_text.lower()
    signals = [
        "cdn.shopify.com" in lower,
        "shopify" in lower,
        "shopify-features" in lower,
        any("shopify" in script.get("src", "").lower() for script in parser.scripts),
        any("/products/" in link.get("href", "").lower() for link in parser.links),
        any("/collections/" in link.get("href", "").lower() for link in parser.links),
    ]
    count = sum(1 for signal in signals if signal)
    if count >= 2:
        return "Shopify", "confirmed"
    if count == 1:
        return "Muhtemelen Shopify", "probable"
    return "unknown", "unknown"


def aggregate_platform(pages: list[SeoPageAnalysis]) -> tuple[str, str]:
    if any(page.platform == "Shopify" for page in pages):
        return "Shopify", "confirmed"
    if any(page.platform == "Muhtemelen Shopify" for page in pages):
        return "Muhtemelen Shopify", "probable"
    return "unknown", "unknown"


def visible_word_count(text: str) -> int:
    return len(re.findall(r"[\wÀ-ž]+", text, flags=re.UNICODE))


def shopify_recommendation(recommendation: str, platform_hint: str) -> str:
    if "Shopify" not in platform_hint:
        return recommendation
    return f"Shopify Admin > Products/Collections/Pages > Search engine listing alanında uygula. {recommendation}"


def _decode_body(body: bytes) -> str:
    return body.decode("utf-8", errors="replace")


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(value)).strip()
