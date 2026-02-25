"""
Image scraper: given a webpage URL, find and download all images.
Supports both static HTML (requests) and JavaScript-rendered pages (Selenium).
Used for collecting scam prevention image dataset.
"""
import base64
import os
import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# Optional: Selenium for JS-rendered pages (e.g. BNM financial-fraud-alerts)
_SELENIUM_AVAILABLE = False
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.by import By
    try:
        from webdriver_manager.chrome import ChromeDriverManager
    except Exception:
        ChromeDriverManager = None
    _SELENIUM_AVAILABLE = True
except ImportError:
    pass

# Default headers to reduce blocking
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

# Common image extensions
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg", ".ico"}

# Magic bytes for image formats (so we don't save HTML as .png)
_IMAGE_SIGNATURES = [
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"\xff\xd8\xff", ".jpg"),
    (b"GIF87a", ".gif"),
    (b"GIF89a", ".gif"),
    (b"RIFF", ".webp"),  # WebP: RIFF....WEBP
    (b"BM", ".bmp"),
]
# HTML/error pages often start with these
_NON_IMAGE_STARTS = (b"<!", b"<?", b"%PDF", b"<html", b"<!DOCTYPE", b"<?xml")


def _detect_image_format(data: bytes) -> tuple[str | None, bool]:
    """
    Check first bytes of response. Returns (extension, is_valid_image).
    If server returned HTML/error, is_valid_image is False and we should not save as image.
    """
    if not data or len(data) < 4:
        return None, False
    data_lower = data[:20].lower()
    for start in _NON_IMAGE_STARTS:
        if data.startswith(start) or data_lower.startswith(start):
            return None, False
    for sig, ext in _IMAGE_SIGNATURES:
        if data.startswith(sig):
            if ext == ".webp":
                if len(data) >= 12 and data[8:12] == b"WEBP":
                    return ext, True
                continue
            return ext, True
    return None, False


def url_to_folder_name(url: str) -> str:
    """
    Generate a safe folder name from URL so each website gets its own folder.
    e.g. https://www.pbebank.com/online-security/?popup=Y -> pbebank.com_online-security
    """
    parsed = urlparse(url.strip())
    netloc = (parsed.netloc or "").strip().lower()
    path = (parsed.path or "/").strip()
    # Remove www.
    if netloc.startswith("www."):
        netloc = netloc[4:]
    # First path segment or "page"
    path_part = path.strip("/").split("/")[0] if path.strip("/") else "page"
    # Sanitize: only alphanumeric, dash, underscore
    netloc_safe = re.sub(r"[^\w\-.]", "_", netloc)[:64]
    path_safe = re.sub(r"[^\w\-]", "_", path_part)[:48]
    if not netloc_safe:
        netloc_safe = "site"
    name = f"{netloc_safe}_{path_safe}" if path_safe and path_safe != "page" else netloc_safe
    return name or "site"


def is_image_url(url: str) -> bool:
    """Check if URL looks like an image (by path or common patterns)."""
    if not url or url.strip().startswith("data:"):
        return False
    path = urlparse(url.strip()).path.lower()
    if any(path.endswith(ext) for ext in (".js", ".css", ".html", ".htm", ".php", ".json", ".xml")):
        return False
    if any(path.endswith(ext) for ext in IMAGE_EXTENSIONS):
        return True
    # CMS / government sites often use paths like /sites/default/files/ or /media/
    if "/img/" in path or "/image/" in path or "/images/" in path or "/files/" in path or "/sites/" in path or "/media/" in path or "/assets/" in path:
        return True
    return False


def _is_clearly_not_image(url: str) -> bool:
    """Exclude only obvious non-image URLs (e.g. scripts). Used for <img> src so we don't miss odd URLs."""
    if not url or url.strip().startswith("data:"):
        return True
    path = urlparse(url.strip()).path.lower()
    return any(path.endswith(ext) for ext in (".js", ".css", ".html", ".htm", ".php", ".json", ".xml"))


def _fetch_html_with_selenium(page_url: str) -> tuple[str | None, str | None, list[str]]:
    """
    Load page with Chrome/Chromium so JavaScript runs; return (html, base_url, errors).
    """
    if not _SELENIUM_AVAILABLE:
        return None, None, ["Selenium not installed. pip install selenium webdriver-manager"]
    driver = None
    errors = []
    try:
        options = ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        if ChromeDriverManager:
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
        else:
            driver = webdriver.Chrome(options=options)
        driver.get(page_url)
        # Wait for body and some content to load
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
        # Optional: scroll to trigger lazy-loaded images
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        import time
        time.sleep(1.5)
        html = driver.page_source
        base_url = driver.current_url
        return html, base_url, []
    except Exception as e:
        errors.append(f"Selenium: {e}")
        return None, None, errors
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


def _download_images_with_selenium(
    page_url: str,
    image_urls: list[str],
    output_folder: str,
    progress_callback=None,
) -> tuple[int, int, list[str]]:
    """
    Download images using the same browser session as the page (so cookies/Referer
    are sent). BNM and similar sites return HTML when requested without session.
    """
    if not _SELENIUM_AVAILABLE or not image_urls:
        return 0, len(image_urls or []), ["Selenium not available or no URLs"]
    driver = None
    downloaded = 0
    failed = 0
    errors = []
    os.makedirs(output_folder, exist_ok=True)

    _fetch_script = """
    const url = arguments[0];
    const callback = arguments[arguments.length - 1];
    fetch(url, { credentials: 'include', mode: 'cors' })
      .then(r => r.blob())
      .then(blob => {
        const reader = new FileReader();
        reader.onloadend = () => callback(reader.result);
        reader.readAsDataURL(blob);
      })
      .catch(e => callback('error:' + e.message));
    """
    try:
        options = ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        if ChromeDriverManager:
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
        else:
            driver = webdriver.Chrome(options=options)
        driver.get(page_url)
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
        driver.set_script_timeout(30)
        import time
        time.sleep(1)

        for i, img_url in enumerate(image_urls):
            if progress_callback:
                progress_callback(i, len(image_urls), f"Downloading {i + 1}/{len(image_urls)} (browser)")
            try:
                data_url = driver.execute_async_script(_fetch_script, img_url)
                if isinstance(data_url, str) and data_url.startswith("error:"):
                    failed += 1
                    errors.append(f"{img_url}: {data_url}")
                    continue
                if not isinstance(data_url, str) or "base64," not in data_url:
                    failed += 1
                    errors.append(f"{img_url}: Invalid response")
                    continue
                b64 = data_url.split("base64,", 1)[1]
                data = base64.b64decode(b64)
                if not data:
                    failed += 1
                    errors.append(f"{img_url}: Empty decode")
                    continue
                detected_ext, is_image = _detect_image_format(data)
                if not is_image or not detected_ext:
                    failed += 1
                    errors.append(f"{img_url}: Not image data")
                    continue
                filepath = os.path.join(
                    output_folder,
                    safe_filename_from_url(img_url, i, f"image/{detected_ext[1:]}")
                )
                base_no_ext = os.path.splitext(filepath)[0]
                filepath = base_no_ext + detected_ext
                with open(filepath, "wb") as f:
                    f.write(data)
                downloaded += 1
            except Exception as e:
                failed += 1
                errors.append(f"{img_url}: {e}")
        if progress_callback:
            progress_callback(len(image_urls), len(image_urls), f"Done. Downloaded {downloaded}, failed {failed}.")
    except Exception as e:
        errors.append(f"Selenium download: {e}")
        failed = len(image_urls)
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
    return downloaded, failed, errors


# Regex to find url(...) in CSS (e.g. background-image: url(...))
_CSS_URL_PATTERN = re.compile(r"url\s*\(\s*['\"]?([^'\")\s]+)['\"]?\s*\)", re.I)


def _extract_urls_from_soup(soup: BeautifulSoup, base_url: str) -> set:
    """Extract all image URLs from parsed HTML (img, a, and style background-image)."""
    image_urls = set()
    # 1. All <img src="..."> and data-src (lazy loading). Include any URL from img that isn't clearly script/css.
    for img in soup.find_all("img"):
        for attr in ("src", "data-src", "data-lazy-src"):
            src = img.get(attr)
            if not src or str(src).strip().startswith("data:"):
                continue
            full_url = urljoin(base_url, str(src).strip())
            if not _is_clearly_not_image(full_url):
                image_urls.add(full_url)
        for attr in ("data-srcset", "srcset"):
            src = img.get(attr)
            if not src:
                continue
            for part in str(src).split(","):
                part = part.strip().split()[0] if part.strip() else ""
                if part and not part.startswith("data:") and not _is_clearly_not_image(part):
                    full_url = urljoin(base_url, part.strip())
                    image_urls.add(full_url)
    # 2. Links that point to image files
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith("data:"):
            continue
        full_url = urljoin(base_url, href)
        if is_image_url(full_url):
            image_urls.add(full_url)
    # 3. background-image: url(...) in style attributes
    for tag in soup.find_all(style=True):
        style = tag.get("style", "")
        for m in _CSS_URL_PATTERN.finditer(style):
            u = m.group(1).strip()
            if u.startswith("data:"):
                continue
            full_url = urljoin(base_url, u)
            if is_image_url(full_url):
                image_urls.add(full_url)
    return image_urls


def get_image_urls_from_page(page_url: str, session: requests.Session | None = None, use_selenium: bool = False) -> tuple[list[str], list[str]]:
    """
    Fetch a webpage and extract all image URLs (img, links, background-image).
    If use_selenium=True and Selenium is available, uses browser to get JS-rendered content.
    Returns (list of image URLs, list of error messages).
    """
    errors = []
    image_urls = set()
    soup = None
    base_url = page_url

    if use_selenium and _SELENIUM_AVAILABLE:
        html, base_url, sel_errors = _fetch_html_with_selenium(page_url)
        errors.extend(sel_errors)
        if html and base_url:
            soup = BeautifulSoup(html, "html.parser")
            image_urls = _extract_urls_from_soup(soup, base_url)

    if soup is None:
        session = session or requests.Session()
        session.headers.update(HEADERS)
        try:
            resp = session.get(page_url, timeout=15)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or "utf-8"
            soup = BeautifulSoup(resp.text, "html.parser")
            base_url = resp.url
            image_urls = _extract_urls_from_soup(soup, base_url)
        except requests.RequestException as e:
            errors.append(f"Failed to fetch {page_url}: {e}")
            return [], errors

    return list(image_urls), errors


def safe_filename_from_url(url: str, index: int, content_type: str | None = None) -> str:
    """Generate a safe filename for the image (avoid overwrites)."""
    parsed = urlparse(url)
    path = parsed.path or "/unknown"
    name = os.path.basename(path).split("?")[0]
    if not name or name == "unknown":
        name = "image"
    # Ensure we have an extension
    ext = os.path.splitext(name)[1].lower()
    if not ext and content_type:
        ctype = content_type.lower()
        if "jpeg" in ctype or "jpg" in ctype:
            ext = ".jpg"
        elif "png" in ctype:
            ext = ".png"
        elif "gif" in ctype:
            ext = ".gif"
        elif "webp" in ctype:
            ext = ".webp"
    if not ext:
        ext = ".jpg"
    if ext not in IMAGE_EXTENSIONS:
        ext = ".jpg"
    # Unique suffix to avoid overwrites
    slug = re.sub(r"[^\w\-.]", "_", name)[:80]
    base = os.path.splitext(slug)[0] or "image"
    return f"{base}_{index:04d}{ext}"


def download_image(
    url: str,
    folder: str,
    index: int,
    session: requests.Session | None = None,
) -> tuple[str | None, str | None]:
    """
    Download a single image to folder. Validates content is real image data (magic bytes);
    skips if server returned HTML/error page so we don't save broken .png files.
    Returns (filepath, error).
    """
    session = session or requests.Session()
    session.headers.update(HEADERS)
    try:
        r = session.get(url, timeout=15)
        r.raise_for_status()
        data = r.content
        if not data:
            return None, "Empty response"
        detected_ext, is_image = _detect_image_format(data)
        if not is_image or not detected_ext:
            return None, "Skip (server returned HTML or non-image data)"
        content_type = r.headers.get("Content-Type", "")
        filepath = os.path.join(
            folder,
            safe_filename_from_url(url, index, content_type or f"image/{detected_ext[1:]}")
        )
        # Override extension with detected format so we never save HTML as .png
        base_no_ext = os.path.splitext(filepath)[0]
        filepath = base_no_ext + detected_ext
        with open(filepath, "wb") as f:
            f.write(data)
        return filepath, None
    except Exception as e:
        return None, str(e)


def scrape_images_from_url(
    page_url: str,
    output_folder: str,
    progress_callback=None,
    subfolder_name: str | None = None,
) -> tuple[int, int, list[str]]:
    """
    Scrape all images from one webpage URL.
    Images are saved to output_folder/subfolder_name (or output_folder/url_to_folder_name(page_url) if subfolder_name is None).
    progress_callback(current, total, message) optional.
    Returns (downloaded_count, failed_count, list of error messages).
    """
    raw_name = (subfolder_name or url_to_folder_name(page_url)).strip() or url_to_folder_name(page_url)
    folder_name = re.sub(r"[^\w\-.]", "_", raw_name)[:80] or "site"
    real_output = os.path.join(output_folder, folder_name)
    os.makedirs(real_output, exist_ok=True)
    session = requests.Session()
    session.headers.update(HEADERS)

    image_urls, fetch_errors = get_image_urls_from_page(page_url, session, use_selenium=False)
    all_errors = list(fetch_errors)
    used_selenium_for_fetch = False
    # If no images found (e.g. JS-rendered page like BNM), retry with Selenium
    if len(image_urls) == 0 and _SELENIUM_AVAILABLE:
        if progress_callback:
            progress_callback(0, 0, "No images in HTML. Trying browser (Selenium)...")
        image_urls, sel_errors = get_image_urls_from_page(page_url, session, use_selenium=True)
        all_errors.extend(sel_errors)
        used_selenium_for_fetch = True
        if progress_callback and image_urls:
            progress_callback(0, len(image_urls), f"Found {len(image_urls)} image(s) with browser.")

    if progress_callback:
        progress_callback(0, len(image_urls), f"Found {len(image_urls)} image(s) on page.")

    # Sites like BNM return HTML when we request image URLs directly (no session).
    # If we got URLs via Selenium, download them in the same browser session.
    if used_selenium_for_fetch and image_urls and _SELENIUM_AVAILABLE:
        downloaded, failed, dl_errors = _download_images_with_selenium(
            page_url, image_urls, real_output, progress_callback
        )
        all_errors.extend(dl_errors)
        return downloaded, failed, all_errors

    downloaded = 0
    failed = 0
    for i, img_url in enumerate(image_urls):
        if progress_callback:
            progress_callback(i, len(image_urls), f"Downloading {i + 1}/{len(image_urls)}")
        path, err = download_image(img_url, real_output, i, session)
        if path:
            downloaded += 1
        else:
            failed += 1
            if err:
                all_errors.append(f"{img_url}: {err}")

    if progress_callback:
        progress_callback(len(image_urls), len(image_urls), f"Done. Downloaded {downloaded}, failed {failed}.")
    return downloaded, failed, all_errors


def scrape_images_from_urls(
    urls: list[str],
    output_folder: str,
    progress_callback=None,
) -> tuple[int, int, list[str]]:
    """
    Scrape images from multiple page URLs (e.g. from a txt file).
    Each URL gets its own subfolder under output_folder (auto-named from URL).
    Returns (total_downloaded, total_failed, all_errors).
    """
    total_downloaded = 0
    total_failed = 0
    all_errors = []
    urls = [u.strip() for u in urls if u.strip()]

    for idx, page_url in enumerate(urls):
        if progress_callback:
            progress_callback(idx, len(urls), f"Processing URL {idx + 1}/{len(urls)}: {page_url[:50]}...")

        def sub_progress(current, total, msg):
            if progress_callback:
                progress_callback(idx, len(urls), msg)

        d, f, errs = scrape_images_from_url(page_url, output_folder, sub_progress, subfolder_name=None)
        total_downloaded += d
        total_failed += f
        all_errors.extend(errs)

    return total_downloaded, total_failed, all_errors
