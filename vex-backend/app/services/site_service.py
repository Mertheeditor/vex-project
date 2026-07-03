from __future__ import annotations

from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

def analyze_site(url: str, prompt: str = "") -> dict:
    if not url:
        return {"success": False, "message": "URL boş."}
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        response = requests.get(url, timeout=15, headers={"User-Agent": "VexBot/0.2"})
        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.title.get_text(strip=True) if soup.title else ""
        description_tag = soup.find("meta", attrs={"name": "description"})
        description = description_tag.get("content", "") if description_tag else ""
        h1s = [h.get_text(strip=True) for h in soup.find_all("h1")[:5]]
        return {"success": True, "analysis": f"Başlık: {title}\nMeta açıklama: {description}\nH1: {', '.join(h1s) or 'Bulunamadı'}\nHTTP: {response.status_code}"}
    except Exception as exc:
        return {"success": False, "message": f"Site analiz edilemedi: {exc}"}

def find_products(url: str, query: str = "", language: str = "Turkish", max_pages: int = 40) -> dict:
    if not url:
        return {"success": False, "message": "URL boş."}
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        response = requests.get(url, timeout=15, headers={"User-Agent": "VexBot/0.2"})
        soup = BeautifulSoup(response.text, "html.parser")
        links = []
        for a in soup.find_all("a", href=True):
            text = a.get_text(" ", strip=True)
            href = urljoin(url, a["href"])
            if text and any(word in href.lower() for word in ["product", "urun", "produkt", "collections", "shop"]):
                links.append({"title": text[:120], "url": href})
            if len(links) >= 20:
                break
        formatted = "\n".join(f"- {item['title']}: {item['url']}" for item in links) or "Ürün linki bulunamadı."
        return {"success": True, "products": links, "formatted_output": formatted}
    except Exception as exc:
        return {"success": False, "message": f"Ürün araması başarısız: {exc}"}
