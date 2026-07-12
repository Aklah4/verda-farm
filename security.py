"""Redirect-target validation.

`next` params and the Referer header are attacker-controllable, so anything we
feed to `redirect()` has to be proven same-origin first — otherwise a page that
auto-submits a form to /cart/add can bounce the customer to a lookalike site.
"""

from urllib.parse import urljoin, urlparse

from flask import request, url_for


def is_same_origin(target):
    """True only for targets that resolve back to this host over http(s).

    Rejects absolute URLs to other hosts and scheme-relative "//evil.com",
    which urljoin resolves to a foreign netloc.
    """
    if not target:
        return False

    here = urlparse(request.host_url)
    there = urlparse(urljoin(request.host_url, target))

    return there.scheme in ("http", "https") and there.netloc == here.netloc


def safe_redirect_target(*candidates, fallback="shop.index"):
    """First same-origin candidate, else the fallback endpoint."""
    for candidate in candidates:
        if is_same_origin(candidate):
            return candidate
    return url_for(fallback)
