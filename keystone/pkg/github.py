"""Windows downloads from a project's latest GitHub release."""
from __future__ import annotations

import html
import json
import re
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.github.com/repos/{repo}/releases/latest"
SKIP = re.compile(r"sha\d*|checksum|\.sig$|\.asc$|\.blockmap$|symbols|debug|source|\bsrc\b"
                  r"|linux|ubuntu|mac|darwin|osx|freebsd|netbsd|openbsd|plan9|solaris|aix|\.appimage$|\.deb$|\.rpm$", re.I)
ARM = re.compile(r"arm64|aarch64", re.I)
X86 = re.compile(r"\b(x86|386|i[36]86|win32|32-?bit)\b", re.I)
SUFFIX_RANK = {".msi": 2, ".exe": 2, ".zip": 1}

ICON_CANDIDATE_PATHS = [
    "app_icon.png", "app_icon.svg", "app_icon.ico",
    "icon.png", "icon.svg", "icon.ico",
    "logo.png", "logo.svg", "logo.ico",
    "app-icon.png", "app.png", "app.ico",
    "assets/app_icon.png", "assets/icon.png", "assets/logo.png", "assets/icon.ico", "assets/logo.svg",
    "assets/logo-256.png", "assets/logo-128.png", "assets/logo.ico", "assets/app.png",
    "resources/icon.png", "resources/app_icon.png", "resources/logo.png", "resources/icon.ico",
    "resources/assets/icon.png", "resources/assets/icon.ico", "resources/assets/logo.svg",
    "resources/icons/app/app.png", "resources/app.ico",
    "res/icon.png", "res/icon.ico", "res/logo.png", "res/app.ico",
    ".github/icon.png", ".github/logo.png", ".github/app.png",
    ".chocolatey/logo.png",
    "src/images/icon_128x128.png", "src/images/icon.png", "src/images/logo.png",
    "images/icon.png", "images/logo.png", "images/app.png", "images/simplewall.png",
    "img/icon.png", "img/logo.png", "img/icon.svg", "img/logo.svg",
    "Artworks/app.png", "Artwork/app.png", "Artworks/icon.png",
    "QuickLook.Common/app.png",
    "Img/icon.png", "Img/logo.png",
    "devscripts/logo.ico",
    "Assets/icon.ico", "Assets/icon.png", "Assets/logo.png", "Assets/NewLogoTemplate.ico",
    "Installer/logo.png", "Helpers/extps1/PE_Helper/logo.png",
    "src/Common/VeraCrypt.ico",
    "src/SyncTrayzor/Icons/default.ico",
    "PackagingProject/Images/Square150x150Logo.scale-200.png",
    "doc/images/icons/PowerToys%20icon/PNG/PowerToysAppList.targetsize-144.png",
    "res/terminal/images-Can/Square150x150Logo.scale-150.png",
    "icons/timeshift.png",
]


def pick_asset(assets: list[dict], arch: str = "x86_64", pattern: str = "") -> dict | None:
    """The best Windows asset for ``arch``; ``pattern`` overrides the name heuristics."""
    if pattern:
        return next((a for a in assets if re.search(pattern, a["name"], re.I)), None)
    want_arm = bool(ARM.search(arch))

    def score(a: dict) -> int:
        name = a["name"]
        rank = next((r for s, r in SUFFIX_RANK.items() if name.lower().endswith(s)), 0)
        if name.lower().endswith(".zip") and "win" not in name.lower():
            return 0
        if not rank or SKIP.search(name) or X86.search(name) or bool(ARM.search(name)) != want_arm:
            return 0
        return rank * 2 + bool(re.search(r"setup|install", name, re.I))

    best = max(assets, key=score, default=None)
    return best if best and score(best) else None


def _scrape_assets(repo: str) -> list[dict]:
    """Release assets from the public pages; used when the API's anonymous rate limit is hit."""
    ua = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) KeyStone"}
    with urllib.request.urlopen(urllib.request.Request(f"https://github.com/{repo}/releases/latest", headers=ua), timeout=30) as r:
        m = re.search(r"/releases/tag/([^/?#]+)", r.geturl())
    if not m:
        return []
    tag = m.group(1)
    page = f"https://github.com/{repo}/releases/expanded_assets/{tag}"
    with urllib.request.urlopen(urllib.request.Request(page, headers=ua), timeout=30) as r:
        html_src = r.read().decode("utf-8", "replace")
    names = dict.fromkeys(re.findall(r'href="(/%s/releases/download/%s/[^"]+)"' % (re.escape(repo), re.escape(tag)), html_src))
    return [{"name": urllib.parse.unquote(path.rsplit("/", 1)[-1]), "browser_download_url": "https://github.com" + path}
            for path in names]


def detect_lang(text: str) -> str:
    """Detect whether text is predominantly Turkish ('tr'), English ('en'), or other."""
    if not text:
        return "other"
    s = text.lower()
    # Distinctive Turkish characters
    if any(c in "çğıöşü" for c in s):
        return "tr"
    # Distinctive Turkish stop words
    tr_words = {"bir", "ve", "ile", "icin", "için", "bu", "da", "de", "olan", "olarak",
                "uygulama", "arac", "araç", "saglar", "sağlar", "yonetimi", "yönetimi", "acik", "açık"}
    words = set(re.findall(r"\b\w+\b", s))
    if len(words & tr_words) >= 2:
        return "tr"
    en_words = {"the", "and", "is", "for", "with", "this", "that", "from", "which",
                "an", "in", "on", "at", "to", "tool", "app", "application", "supports", "allows"}
    if len(words & en_words) >= 2:
        return "en"
    return "other"


def extract_readme_desc(readme_text: str) -> str:
    """Extract the first meaningful descriptive paragraph from a project's README."""
    if not readme_text:
        return ""
    for raw_line in readme_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("[!") or line.startswith("![") or line.startswith("<") or line.startswith("---") or line.startswith("==="):
            continue
        line = re.sub(r"^[>\s*_-]+", "", line)  # blockquote or list markers
        line = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", line)  # markdown links to text
        line = re.sub(r"[*_`]", "", line).strip()  # markdown formatting characters
        if len(line) >= 20:
            return line[:300].strip()
    return ""


def extract_section_desc(markdown_text: str, lang: str) -> str:
    """Extract description from a language-specific heading in README if present."""
    if not markdown_text:
        return ""
    if lang == "tr":
        pattern = r"(?:^|\n)#{1,4}\s*(?:🇹🇷|Türkçe|Turkish)[^\n]*\n(.*?)(?=\n#{1,4}\s|\Z)"
    elif lang == "en":
        pattern = r"(?:^|\n)#{1,4}\s*(?:🇺🇸|🇬🇧|English|EN)[^\n]*\n(.*?)(?=\n#{1,4}\s|\Z)"
    else:
        return ""
    m = re.search(pattern, markdown_text, re.DOTALL | re.I)
    if m:
        return extract_readme_desc(m.group(1))
    return ""


def resolve_localized_desc(desc_tr: str, desc_en: str, desc_other: str, preferred_lang: str = "tr") -> tuple[str, dict[str, str]]:
    """Resolve primary and dictionary descriptions according to KeyStone language rules.
    
    Rule:
    - If preferred language is English:
        If English description exists, use English.
        If only one language exists (e.g. Spanish or Turkish), use it anyway.
    - If preferred language is Turkish:
        If both Turkish and English exist, prioritize Turkish according to app language.
        If only English exists, use English.
        If only another single language exists (e.g. Spanish), use it anyway.
    """
    desc_tr = desc_tr.strip()
    desc_en = desc_en.strip()
    desc_other = desc_other.strip()

    if desc_tr and desc_en:
        # Both exist
        primary = desc_en if preferred_lang == "en" else desc_tr
        d = {"tr": desc_tr, "en": desc_en}
    elif desc_tr:
        # Only Turkish exists -> use it regardless of app language
        primary = desc_tr
        d = {"tr": desc_tr, "en": desc_tr}
    elif desc_en:
        # Only English exists -> use it regardless of app language
        primary = desc_en
        d = {"tr": desc_en, "en": desc_en}
    elif desc_other:
        # Only one other language exists (e.g. Spanish) -> use it regardless of app language
        primary = desc_other
        d = {"tr": desc_other, "en": desc_other}
    else:
        primary = ""
        d = {"tr": "", "en": ""}
    return primary, d


def find_repo_app_icon(repo: str, owner: str, name: str, owner_type: str = "User", items: list[dict] | None = None) -> str:
    """Find the authentic application icon URL.
    
    Never defaults to an individual developer's personal avatar photo.
    """
    ua = {"User-Agent": "KeyStone", "Accept": "application/vnd.github+json"}

    # 1. Check repo contents (from provided items or API)
    contents = items
    if contents is None:
        try:
            req = urllib.request.Request(f"https://api.github.com/repos/{repo}/contents", headers=ua)
            with urllib.request.urlopen(req, timeout=5) as r:
                contents = json.load(r)
        except Exception:
            contents = []

    if isinstance(contents, list):
        for ext in ("png", "svg", "ico"):
            for item in contents:
                fn = item.get("name", "").lower()
                if fn in [f"app_icon.{ext}", f"app-icon.{ext}", f"icon.{ext}", f"logo.{ext}", f"app.{ext}"]:
                    item_name = item.get("name", "")
                    return item.get("download_url") or f"https://raw.githubusercontent.com/{repo}/HEAD/{item_name}"

    # 2. Check candidate raw URLs directly
    for rel_path in ICON_CANDIDATE_PATHS:
        url = f"https://raw.githubusercontent.com/{repo}/HEAD/{rel_path}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "KeyStone"}, method="HEAD")
            with urllib.request.urlopen(req, timeout=2) as r:
                if r.status == 200:
                    return url
        except Exception:
            continue

    # 2.5 If candidate paths didn't match, check repo tree for authentic icon files
    try:
        req = urllib.request.Request(f"https://api.github.com/repos/{repo}/git/trees/HEAD?recursive=1", headers=ua)
        with urllib.request.urlopen(req, timeout=3) as r:
            tree = json.load(r).get("tree", [])
            for item in tree:
                p = item.get("path", "")
                pl = p.lower()
                if any(skip in pl for skip in ("test", "vendor", "node_modules", "badge", "travis", "workflow", "screenshot")):
                    continue
                fn = pl.split("/")[-1]
                if fn in ("icon.png", "app_icon.png", "app-icon.png", "logo.png", "app.png", "icon.ico", "app.ico", "logo.ico", "icon.svg", "logo.svg"):
                    quoted_path = urllib.parse.quote(p)
                    return f"https://raw.githubusercontent.com/{repo}/HEAD/{quoted_path}"
    except Exception:
        pass

    # 3. If no authentic app icon file is found, do not add any fallback avatar or image.
    # User requirement: "eklenen github repolarında uygulama ikonu yoksa hiçbir görsel eklemek zorunda değilsin"
    return ""


def _scrape_repo_meta(repo: str) -> dict:
    """Scrape description and icon from public github.com/{repo} page when API is unavailable."""
    ua = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) KeyStone"}
    owner, name = repo.split("/", 1)
    desc = ""
    icon_url = ""
    owner_type = "User"
    try:
        req = urllib.request.Request(f"https://github.com/{repo}", headers=ua)
        with urllib.request.urlopen(req, timeout=10) as r:
            html_text = r.read().decode("utf-8", "replace")

        # Detect organization vs user
        if 'organization:' in html_text or 'itemtype="http://schema.org/Organization"' in html_text:
            owner_type = "Organization"

        m = re.search(r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']+)["\']', html_text, re.I)
        if not m:
            m = re.search(r'<meta\s+property=["\']og:description["\']\s+content=["\']([^"\']+)["\']', html_text, re.I)
        if m:
            raw_desc = html.unescape(m.group(1)).strip()
            raw_desc = re.sub(r"\.?\s*Contribute to .+ on GitHub\.?", "", raw_desc, flags=re.I).strip()
            raw_desc = re.sub(r"\s*-\s*[a-zA-Z0-9_\-\.]+/[a-zA-Z0-9_\-\.]+$", "", raw_desc).strip()
            if raw_desc:
                desc = raw_desc

        # If meta description was empty, scrape embedded README from HTML
        if not desc:
            m_art = re.search(r'<article[^>]*markdown-body[^>]*>(.*?)</article>', html_text, re.DOTALL | re.I)
            if m_art:
                clean_article = re.sub(r"<[^>]+>", "\n", m_art.group(1))
                desc = extract_readme_desc(clean_article)
    except Exception:
        pass

    icon_url = find_repo_app_icon(repo, owner, name, owner_type)
    return {"desc": desc, "icon_url": icon_url, "owner_type": owner_type}


def latest_asset(repo: str, arch: str = "x86_64", pattern: str = "") -> dict | None:
    req = urllib.request.Request(API.format(repo=repo), headers={
        "User-Agent": "KeyStone", "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            assets = json.load(r).get("assets", [])
    except urllib.error.HTTPError as exc:
        if exc.code not in (403, 429):
            raise
        assets = _scrape_assets(repo)
    return pick_asset(assets, arch, pattern)


def clean_repo_name(raw: str) -> str:
    """Normalize input (e.g. URL, git link, or 'owner/repo') to 'owner/repo'."""
    s = raw.strip()
    m = re.search(r"github\.com[:/]([a-zA-Z0-9_\-\.]+)/([a-zA-Z0-9_\-\.]+)", s, re.I)
    if m:
        owner, repo = m.group(1), m.group(2)
    else:
        parts = s.strip("/").split("/")
        if len(parts) >= 2:
            owner, repo = parts[0], parts[1]
        else:
            owner, repo = "", parts[0]
    repo = re.sub(r"\.git$", "", repo, flags=re.I)
    return f"{owner}/{repo}".strip("/")


def repo_info(repo_raw: str, arch: str = "x86_64", preferred_lang: str = "tr") -> dict:
    """Fetch repo details, description, icon URL, and available release assets."""
    repo = clean_repo_name(repo_raw)
    if not repo or "/" not in repo:
        raise ValueError(f"Invalid GitHub repository: {repo_raw}")
    owner, name = repo.split("/", 1)
    title = name.replace("-", " ").replace("_", " ").title()
    desc = ""
    website = f"https://github.com/{repo}"
    icon_url = ""
    tag = ""
    assets: list[dict] = []
    owner_type = "User"
    contents: list[dict] = []

    ua = {"User-Agent": "KeyStone", "Accept": "application/vnd.github+json"}

    # 1. Fetch repo details from GitHub API
    api_desc = ""
    try:
        req = urllib.request.Request(f"https://api.github.com/repos/{repo}", headers=ua)
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.load(r)
            api_desc = (data.get("description") or "").strip()
            website = data.get("html_url") or website
            owner_type = data.get("owner", {}).get("type", "User")
            if data.get("name"):
                title = data["name"].replace("-", " ").replace("_", " ").title()
    except Exception:
        pass

    # 2. Fetch repo contents list to check for icons and localized READMEs
    try:
        req = urllib.request.Request(f"https://api.github.com/repos/{repo}/contents", headers=ua)
        with urllib.request.urlopen(req, timeout=6) as r:
            contents = json.load(r)
    except Exception:
        contents = []

    # 3. Find authentic application icon
    icon_url = find_repo_app_icon(repo, owner, name, owner_type, contents)

    # 4. Multilingual description discovery (TR, EN, and others)
    desc_tr = ""
    desc_en = ""
    desc_other = ""

    # Check API description language
    if api_desc:
        alang = detect_lang(api_desc)
        if alang == "tr":
            desc_tr = api_desc
        elif alang == "en":
            desc_en = api_desc
        else:
            desc_other = api_desc

    # Check for localized README files in repo
    tr_readme_names = ["readme_tr.md", "readme.tr.md", "readme-tr.md", "readme_tr.txt"]
    en_readme_names = ["readme_en.md", "readme.en.md", "readme-en.md", "readme_en.txt"]

    for item in contents:
        fn = item.get("name", "").lower()
        if not desc_tr and fn in tr_readme_names:
            try:
                url = item.get("download_url") or f"https://raw.githubusercontent.com/{repo}/HEAD/{item.get('name')}"
                with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "KeyStone"}), timeout=5) as r:
                    desc_tr = extract_readme_desc(r.read().decode("utf-8", "replace"))
            except Exception:
                pass
        if not desc_en and fn in en_readme_names:
            try:
                url = item.get("download_url") or f"https://raw.githubusercontent.com/{repo}/HEAD/{item.get('name')}"
                with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "KeyStone"}), timeout=5) as r:
                    desc_en = extract_readme_desc(r.read().decode("utf-8", "replace"))
            except Exception:
                pass

    # Check main README
    main_readme_text = ""
    try:
        req = urllib.request.Request(f"https://raw.githubusercontent.com/{repo}/HEAD/README.md", headers={"User-Agent": "KeyStone"})
        with urllib.request.urlopen(req, timeout=5) as r:
            main_readme_text = r.read().decode("utf-8", "replace")
    except Exception:
        pass

    if main_readme_text:
        # Check if sections exist
        sec_tr = extract_section_desc(main_readme_text, "tr")
        if sec_tr and not desc_tr:
            desc_tr = sec_tr
        sec_en = extract_section_desc(main_readme_text, "en")
        if sec_en and not desc_en:
            desc_en = sec_en

        if not desc_tr and not desc_en and not desc_other:
            rd = extract_readme_desc(main_readme_text)
            if rd:
                rlang = detect_lang(rd)
                if rlang == "tr":
                    desc_tr = rd
                elif rlang == "en":
                    desc_en = rd
                else:
                    desc_other = rd

    # 5. Fallback scraping if nothing was found
    if not desc_tr and not desc_en and not desc_other:
        scraped = _scrape_repo_meta(repo)
        if scraped.get("desc"):
            sd = scraped["desc"]
            slang = detect_lang(sd)
            if slang == "tr":
                desc_tr = sd
            elif slang == "en":
                desc_en = sd
            else:
                desc_other = sd
        if not icon_url and scraped.get("icon_url"):
            icon_url = scraped["icon_url"]

    # 6. Fetch release assets and use release body if needed
    try:
        req = urllib.request.Request(API.format(repo=repo), headers=ua)
        with urllib.request.urlopen(req, timeout=8) as r:
            rel = json.load(r)
            tag = rel.get("tag_name") or ""
            assets = rel.get("assets", [])
            if not desc_tr and not desc_en and not desc_other and rel.get("body"):
                rb = extract_readme_desc(rel["body"])
                if rb:
                    rlang = detect_lang(rb)
                    if rlang == "tr":
                        desc_tr = rb
                    elif rlang == "en":
                        desc_en = rb
                    else:
                        desc_other = rb
    except urllib.error.HTTPError as exc:
        if exc.code in (403, 429):
            assets = _scrape_assets(repo)
    except Exception:
        pass

    best_asset = pick_asset(assets, arch) if assets else None

    # Resolve descriptions according to KeyStone language rule
    primary_desc, desc_dict = resolve_localized_desc(desc_tr, desc_en, desc_other, preferred_lang=preferred_lang)

    return {
        "ok": True,
        "repo": repo,
        "name": title,
        "desc": primary_desc,
        "desc_dict": desc_dict,
        "desc_tr": desc_dict.get("tr", ""),
        "desc_en": desc_dict.get("en", ""),
        "website": website,
        "icon_url": icon_url,
        "tag": tag,
        "asset_name": best_asset["name"] if best_asset else "",
        "assets": [a["name"] for a in assets],
    }
