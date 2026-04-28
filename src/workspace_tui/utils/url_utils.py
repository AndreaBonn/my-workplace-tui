import webbrowser
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


def open_google_url(url: str, google_account_email: str = "") -> None:
    """Open a Google URL in the browser, forcing the specified account via authuser."""
    if google_account_email and _is_google_url(url):
        url = _add_authuser(url, google_account_email)
    webbrowser.open(url)


def _is_google_url(url: str) -> bool:
    host = urlparse(url).hostname or ""
    return host.endswith(".google.com") or host == "meet.google.com"


def _add_authuser(url: str, email: str) -> str:
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    params["authuser"] = [email]
    new_query = urlencode(params, doseq=True)
    return urlunparse(parsed._replace(query=new_query))
