from __future__ import annotations

import http.client
import ipaddress
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.schemas.seo import SeoAuditRequest, SeoSiteSignals
from app.services.seo_service import (
    FetchResult,
    SeoAuditError,
    SeoAuditService,
    SeoCrawler,
    analyze_fetches,
    build_recommendations,
    build_site_signals,
    collect_issues,
    normalize_url,
    parse_sitemap_urls,
    score_audit,
)
from app.storage.seo_store import SeoAuditStore


class FakeCrawler(SeoCrawler):
    def __init__(self, pages: dict[str, str], redirects: dict[str, str] | None = None) -> None:
        super().__init__()
        self.pages = pages
        self.redirects = redirects or {}
        self.fetched: list[str] = []

    def validate_public_url(self, url: str) -> None:
        if "127.0.0.1" in url or "localhost" in url or "169.254.169.254" in url:
            raise SeoAuditError("Unsafe IP address blocked for host test")

    async def discover_sitemaps(self, start_url: str, root_host: str, errors: list[str]) -> list[str]:
        return []

    async def fetch(self, url: str) -> FetchResult:
        self.fetched.append(url)
        if url in self.redirects:
            final_url = self.redirects[url]
            self.validate_public_url(final_url)
            url = final_url
        html = self.pages.get(url, "<html><head><title>Missing</title></head><body></body></html>")
        return FetchResult(
            url=url,
            status_code=200,
            content_type="text/html; charset=utf-8",
            body=html.encode("utf-8"),
            final_url=url,
        )


class SeoSecurityTests(unittest.TestCase):
    def test_url_validation_accepts_only_http_https(self) -> None:
        valid = SeoAuditRequest(url="https://example.com", max_pages=25)
        self.assertEqual(str(valid.url), "https://example.com/")
        with self.assertRaises(Exception):
            SeoAuditRequest(url="ftp://example.com")

    def test_normalize_url_removes_tracking_and_fragment(self) -> None:
        normalized = normalize_url(
            "HTTPS://Example.COM:443/a//b/?utm_source=x&b=2&a=1&fbclid=z#frag"
        )
        self.assertEqual(normalized, "https://example.com/a/b?a=1&b=2")

    def test_ssrf_blocks_private_localhost_link_local_and_metadata(self) -> None:
        crawler = SeoCrawler()
        cases = [
            "http://localhost/",
            "http://127.0.0.1/",
            "http://10.0.0.1/",
            "http://169.254.1.1/",
            "http://169.254.169.254/",
        ]
        with patch("app.services.seo_service.resolve_host") as resolver:
            for url in cases:
                host = url.split("//", 1)[1].strip("/")
                if host == "localhost":
                    with self.assertRaises(SeoAuditError):
                        crawler.validate_public_url(url)
                    continue
                resolver.return_value = {ipaddress.ip_address(host)}
                with self.assertRaises(SeoAuditError):
                    crawler.validate_public_url(url)

    def test_redirect_validation_blocks_unsafe_final_url(self) -> None:
        crawler = FakeCrawler(
            {"https://example.com/": "<html></html>"},
            redirects={"https://example.com/": "http://127.0.0.1/admin"},
        )
        with self.assertRaises(SeoAuditError):
            self.run_async(crawler.fetch("https://example.com/"))

    def test_fetch_pins_connection_to_validated_ip(self) -> None:
        crawler = SeoCrawler()
        used_ips: list[str] = []

        class FakeConnection:
            def __init__(self, host: str, pinned_ip: str, port: int, timeout: int) -> None:
                used_ips.append(pinned_ip)
                self.sock = None

            def request(self, method: str, path: str, headers: dict[str, str]) -> None:
                return None

            def getresponse(self):
                class FakeResponse:
                    status = 200

                    def getheader(self, name: str) -> str:
                        return "text/html" if name == "Content-Type" else ""

                    def read(self, size: int) -> bytes:
                        return b"<html></html>"

                return FakeResponse()

            def close(self) -> None:
                return None

        with patch("app.services.seo_service.resolve_host") as resolver:
            resolver.return_value = {ipaddress.ip_address("93.184.216.34")}
            with patch("app.services.seo_service.PinnedHTTPConnection", FakeConnection):
                result = crawler._fetch_once("http://example.com/")
        self.assertEqual(result.status_code, http.client.OK)
        self.assertEqual(used_ips, ["93.184.216.34"])

    def run_async(self, coro):
        import asyncio

        return asyncio.run(coro)


class SeoCrawlerTests(unittest.IsolatedAsyncioTestCase):
    async def test_crawl_limits_and_duplicate_urls(self) -> None:
        page = """
        <html><head><title>Good Example Title Length</title><meta name="description" content="Good description."><link rel="canonical" href="/"><meta name="viewport" content="width=device-width"></head>
        <body><h1>Main</h1><a href="/a?utm_source=x">A</a><a href="/a">A duplicate</a><a href="/b">B</a></body></html>
        """
        pages = {
            "https://example.com/": page,
            "https://example.com/a": page,
            "https://example.com/b": page,
        }
        crawler = FakeCrawler(pages)
        results, errors, _signals = await crawler.crawl("https://example.com/", max_pages=2)
        self.assertEqual(len(results), 2)
        self.assertEqual(len(set(crawler.fetched)), 2)
        self.assertEqual(errors, [])

    async def test_same_domain_blocks_external_urls(self) -> None:
        page = "<html><head><title>Good Example Title Length</title></head><body><a href='https://other.com/x'>X</a></body></html>"
        crawler = FakeCrawler({"https://example.com/": page, "https://other.com/x": page})
        await crawler.crawl("https://example.com/", max_pages=10)
        self.assertNotIn("https://other.com/x", crawler.fetched)

    def test_robots_sitemap_parsing(self) -> None:
        xml = """
        <urlset>
          <url><loc>https://example.com/a</loc></url>
          <url><loc>https://other.com/b</loc></url>
          <url><loc>https://example.com/a?utm_source=x</loc></url>
        </urlset>
        """
        urls = parse_sitemap_urls(xml, "example.com")
        self.assertEqual(urls, ["https://example.com/a", "https://example.com/a"])


class SeoAnalysisTests(unittest.TestCase):
    def test_title_meta_h1_analysis_and_exports(self) -> None:
        html = """
        <html lang="en"><head>
          <title>Excellent SEO Title Example</title>
          <meta name="description" content="A useful page description for search results.">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <link rel="canonical" href="https://example.com/">
          <meta property="og:title" content="OG title">
          <meta name="twitter:card" content="summary">
          <script type="application/ld+json">{"@context":"https://schema.org"}</script>
        </head><body>
          <h1>Main Heading</h1><h2>Sub Heading</h2><h3>Detail Heading</h3>
          <p>One two three four five six seven eight nine ten.</p>
          <a href="/inside">Inside</a><a href="https://outside.com/">Outside</a>
          <img src="a.jpg"><img src="b.jpg" alt="Alt text">
        </body></html>
        """
        pages = analyze_fetches([
            FetchResult(
                url="https://example.com/",
                status_code=200,
                content_type="text/html",
                body=html.encode("utf-8"),
                final_url="https://example.com/",
            )
        ])
        page = pages[0]
        self.assertEqual(page.title, "Excellent SEO Title Example")
        self.assertEqual(page.meta_description, "A useful page description for search results.")
        self.assertEqual(page.h1, ["Main Heading"])
        self.assertEqual(page.h2, ["Sub Heading"])
        self.assertEqual(page.h3, ["Detail Heading"])
        self.assertEqual(page.lang, "en")
        self.assertEqual(page.images_total, 2)
        self.assertEqual(page.images_missing_alt, 1)
        self.assertEqual(page.json_ld_count, 1)
        self.assertEqual(page.open_graph["og:title"], "OG title")
        self.assertEqual(page.twitter["twitter:card"], "summary")
        self.assertTrue(page.indexable)
        self.assertIn("https://example.com/inside", page.internal_links)
        self.assertIn("https://outside.com/", page.external_links)

    def test_scoring_and_recommendations_are_deterministic(self) -> None:
        bad_html = "<html><head><meta name='robots' content='noindex'></head><body><img src='x'><p>Thin</p></body></html>"
        pages = analyze_fetches([
            FetchResult(
                url="https://example.com/bad",
                status_code=200,
                content_type="text/html",
                body=bad_html.encode("utf-8"),
                final_url="https://example.com/bad",
            )
        ])
        signals = build_site_signals(pages, SeoSiteSignals())
        issues = collect_issues(pages, signals, [])
        self.assertLess(score_audit(issues, pages), 100)
        codes = [issue.code for issue in issues]
        self.assertIn("missing_title", codes)
        self.assertIn("missing_h1", codes)
        recs = build_recommendations(issues)
        self.assertTrue(all(rec.platform_hint == "generic" for rec in recs))

    def test_mspovleceni_shopify_homepage_fixture(self) -> None:
        html = """
        <html lang="cs"><head>
          <title>mSpovleceni | Nakupujte kvalitní povlečení a bytový textil online</title>
          <meta name="description" content="Kvalitní povlečení, prostěradla a bytový textil online.">
          <meta name="robots" content="index,follow">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <link rel="canonical" href="https://mspovleceni.cz/">
          <script>var Shopify = {shop: "mspovleceni.myshopify.com"}; var productJson = {"body_html":"should not count"};</script>
          <script type="application/ld+json">{"@type":"Organization","description":"should not count"}</script>
        </head><body>
          <nav>Menu Povlečení Košík Účet</nav>
          <main><h1>Kvalitní povlečení a bytový textil</h1>
          <p>Nakupujte bavlněné povlečení prostěradla ručníky deky polštáře a další bytový textil pro pohodlný spánek.</p></main>
          <footer>Kontakt Obchodní podmínky</footer>
          <a href="/collections/povleceni?utm_source=x">Povlečení</a>
          <a href="/products/bavlnene-povleceni">Produkt</a>
        </body></html>
        """
        pages = analyze_fetches([FetchResult("https://mspovleceni.cz/", 200, "text/html", html.encode(), "https://mspovleceni.cz/")])
        page = pages[0]
        self.assertEqual(page.title, "mSpovleceni | Nakupujte kvalitní povlečení a bytový textil online")
        self.assertEqual(page.h1, ["Kvalitní povlečení a bytový textil"])
        self.assertEqual(page.canonical, "https://mspovleceni.cz/")
        self.assertEqual(page.robots, "index,follow")
        self.assertEqual(page.page_type, "homepage")
        self.assertEqual(page.platform, "Shopify")
        self.assertGreater(page.word_count, 10)
        self.assertLess(page.word_count, 30)
        self.assertNotIn("missing_title", [issue.code for issue in page.issues])
        self.assertIsNotNone(page.page_score)

    def test_mspovleceni_collection_product_and_utility_fixtures(self) -> None:
        collection_html = """
        <html><head><title>Bavlněné povlečení | mSpovleceni</title><meta name="description" content="Vyberte si kvalitní bavlněné povlečení."><link rel="canonical" href="https://mspovleceni.cz/collections/bavlnene-povleceni"><meta name="viewport" content="width=device-width"></head>
        <body><main><h1>Bavlněné povlečení</h1><p>Kolekce obsahuje moderní vzory a kvalitní materiály pro každou ložnici.</p></main><script src="https://cdn.shopify.com/shopifycloud.js"></script></body></html>
        """
        product_html = """
        <html><head><title>Luxusní bavlněné povlečení modré | mSpovleceni</title><meta property="og:type" content="product"><meta name="description" content="Luxusní modré bavlněné povlečení pro pohodlný spánek."><link rel="canonical" href="https://mspovleceni.cz/products/luxusni-povleceni"><meta name="viewport" content="width=device-width"></head>
        <body><main><h1>Luxusní bavlněné povlečení modré</h1><p>Produktový popis vysvětluje materiál rozměry údržbu a výhody povlečení.</p><img src="x.jpg"></main></body></html>
        """
        cart_html = "<html><head><title>Košík</title><meta name='robots' content='noindex'></head><body><main><h1>Košík</h1></main></body></html>"
        pages = analyze_fetches([
            FetchResult("https://mspovleceni.cz/collections/bavlnene-povleceni", 200, "text/html", collection_html.encode(), "https://mspovleceni.cz/collections/bavlnene-povleceni"),
            FetchResult("https://mspovleceni.cz/products/luxusni-povleceni", 200, "text/html", product_html.encode(), "https://mspovleceni.cz/products/luxusni-povleceni"),
            FetchResult("https://mspovleceni.cz/cart", 200, "text/html", cart_html.encode(), "https://mspovleceni.cz/cart"),
        ])
        self.assertEqual(pages[0].page_type, "collection")
        self.assertEqual(pages[1].page_type, "product")
        self.assertEqual(pages[2].page_type, "cart")
        self.assertGreater(pages[2].page_score or 0, 70)
        signals = build_site_signals(pages, SeoSiteSignals(discovered_urls=500, skipped_urls=3, blocked_urls=1, errored_urls=2))
        issues = collect_issues(pages, signals, [])
        self.assertEqual(signals.platform, "Shopify")
        self.assertEqual(signals.page_type_counts["collection"], 1)
        self.assertGreater(score_audit(issues, pages), 50)

    def test_500_page_limit_and_duplicate_normalization(self) -> None:
        valid = SeoAuditRequest(url="https://example.com", max_pages=500)
        self.assertEqual(valid.max_pages, 500)
        with self.assertRaises(Exception):
            SeoAuditRequest(url="https://example.com", max_pages=501)
        self.assertEqual(normalize_url("https://example.com/a?utm_source=x&b=2#frag"), "https://example.com/a?b=2")
        self.assertEqual(normalize_url("https://example.com/a?b=2"), "https://example.com/a?b=2")

    def test_mspovleceni_shopify_homepage_fixture(self) -> None:
        html = """
        <html lang="cs"><head>
          <title>mSpovleceni | Nakupujte kvalitní povlečení a bytový textil online</title>
          <meta name="description" content="Kvalitní povlečení, prostěradla a bytový textil online.">
          <meta name="robots" content="index,follow">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <link rel="canonical" href="https://mspovleceni.cz/">
          <script>var Shopify = {shop: "mspovleceni.myshopify.com"}; var productJson = {"body_html":"should not count"};</script>
          <script type="application/ld+json">{"@type":"Organization","description":"should not count"}</script>
        </head><body>
          <nav>Menu Povlečení Košík Účet</nav>
          <main><h1>Kvalitní povlečení a bytový textil</h1>
          <p>Nakupujte bavlněné povlečení prostěradla ručníky deky polštáře a další bytový textil pro pohodlný spánek.</p></main>
          <footer>Kontakt Obchodní podmínky</footer>
          <a href="/collections/povleceni?utm_source=x">Povlečení</a>
          <a href="/products/bavlnene-povleceni">Produkt</a>
        </body></html>
        """
        pages = analyze_fetches([FetchResult("https://mspovleceni.cz/", 200, "text/html", html.encode(), "https://mspovleceni.cz/")])
        page = pages[0]
        self.assertEqual(page.title, "mSpovleceni | Nakupujte kvalitní povlečení a bytový textil online")
        self.assertEqual(page.h1, ["Kvalitní povlečení a bytový textil"])
        self.assertEqual(page.canonical, "https://mspovleceni.cz/")
        self.assertEqual(page.robots, "index,follow")
        self.assertEqual(page.page_type, "homepage")
        self.assertEqual(page.platform, "Shopify")
        self.assertGreater(page.word_count, 10)
        self.assertLess(page.word_count, 30)
        self.assertNotIn("missing_title", [issue.code for issue in page.issues])
        self.assertIsNotNone(page.page_score)

    def test_mspovleceni_collection_product_and_utility_fixtures(self) -> None:
        collection_html = """
        <html><head><title>Bavlněné povlečení | mSpovleceni</title><meta name="description" content="Vyberte si kvalitní bavlněné povlečení."><link rel="canonical" href="https://mspovleceni.cz/collections/bavlnene-povleceni"><meta name="viewport" content="width=device-width"></head>
        <body><main><h1>Bavlněné povlečení</h1><p>Kolekce obsahuje moderní vzory a kvalitní materiály pro každou ložnici.</p></main><script src="https://cdn.shopify.com/shopifycloud.js"></script></body></html>
        """
        product_html = """
        <html><head><title>Luxusní bavlněné povlečení modré | mSpovleceni</title><meta property="og:type" content="product"><meta name="description" content="Luxusní modré bavlněné povlečení pro pohodlný spánek."><link rel="canonical" href="https://mspovleceni.cz/products/luxusni-povleceni"><meta name="viewport" content="width=device-width"></head>
        <body><main><h1>Luxusní bavlněné povlečení modré</h1><p>Produktový popis vysvětluje materiál rozměry údržbu a výhody povlečení.</p><img src="x.jpg"></main></body></html>
        """
        cart_html = "<html><head><title>Košík</title><meta name='robots' content='noindex'></head><body><main><h1>Košík</h1></main></body></html>"
        pages = analyze_fetches([
            FetchResult("https://mspovleceni.cz/collections/bavlnene-povleceni", 200, "text/html", collection_html.encode(), "https://mspovleceni.cz/collections/bavlnene-povleceni"),
            FetchResult("https://mspovleceni.cz/products/luxusni-povleceni", 200, "text/html", product_html.encode(), "https://mspovleceni.cz/products/luxusni-povleceni"),
            FetchResult("https://mspovleceni.cz/cart", 200, "text/html", cart_html.encode(), "https://mspovleceni.cz/cart"),
        ])
        self.assertEqual(pages[0].page_type, "collection")
        self.assertEqual(pages[1].page_type, "product")
        self.assertEqual(pages[2].page_type, "cart")
        self.assertGreater(pages[2].page_score or 0, 70)
        signals = build_site_signals(pages, SeoSiteSignals(discovered_urls=500, skipped_urls=3, blocked_urls=1, errored_urls=2))
        issues = collect_issues(pages, signals, [])
        self.assertEqual(signals.platform, "Shopify")
        self.assertEqual(signals.page_type_counts["collection"], 1)
        self.assertGreater(score_audit(issues, pages), 50)

    def test_500_page_limit_and_duplicate_normalization(self) -> None:
        valid = SeoAuditRequest(url="https://example.com", max_pages=500)
        self.assertEqual(valid.max_pages, 500)
        with self.assertRaises(Exception):
            SeoAuditRequest(url="https://example.com", max_pages=501)
        self.assertEqual(normalize_url("https://example.com/a?utm_source=x&b=2#frag"), "https://example.com/a?b=2")
        self.assertEqual(normalize_url("https://example.com/a?b=2"), "https://example.com/a?b=2")


class SeoStorageExportTests(unittest.IsolatedAsyncioTestCase):
    async def test_isolated_storage_and_exports(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SeoAuditStore(Path(temp_dir) / "seo_audits.json")
            html = """
            <html><head><title>Good Example Title Length</title><meta name="description" content="Good description."><meta name="viewport" content="width=device-width"><link rel="canonical" href="https://example.com/"></head>
            <body><h1>Main</h1><p>Enough content for a deterministic technical audit.</p></body></html>
            """
            service = SeoAuditService(store=store, crawler=FakeCrawler({"https://example.com/": html}))
            audit = await service.create_audit("https://example.com/", max_pages=1)
            stored = store.get_audit(audit.id)
            self.assertIsNotNone(stored)
            self.assertEqual(stored["id"], audit.id)
            exported = service.export_json(audit.id)
            self.assertEqual(exported["id"], audit.id)
            markdown = service.export_markdown(audit.id)
            self.assertIn("# SEO Audit Report", markdown)
            self.assertIn(audit.id, markdown)
            self.assertFalse((Path(temp_dir).parent / "data" / "seo_audits.json").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
