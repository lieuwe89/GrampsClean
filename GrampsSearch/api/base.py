"""Base connector — normalizes API results to a common shape."""

import json
import os
import ssl
import urllib.request
import urllib.parse
import urllib.error
from dataclasses import dataclass, field, asdict
from typing import Optional, List


def _build_ssl_context():
    """SSL context for urllib.

    GRAMPS's bundled macOS Python sometimes ships without trusted CA
    roots, causing CERTIFICATE_VERIFY_FAILED. Try in order:
      1. certifi (if installed)
      2. Common macOS / homebrew CA bundle paths
      3. Unverified (logged, last resort so the plugin still works)
    """
    try:
        import certifi  # type: ignore
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        pass

    for path in (
        "/etc/ssl/cert.pem",
        "/private/etc/ssl/cert.pem",
        "/usr/local/etc/openssl/cert.pem",
        "/usr/local/etc/openssl@3/cert.pem",
        "/opt/homebrew/etc/ca-certificates/cert.pem",
        "/opt/homebrew/etc/openssl@3/cert.pem",
    ):
        if os.path.isfile(path):
            try:
                return ssl.create_default_context(cafile=path)
            except Exception:
                continue

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    print("[GrampsSearch] WARNING: no CA bundle found, TLS verification disabled")
    return ctx


_SSL_CTX = _build_ssl_context()


@dataclass
class ExternalPerson:
    """Normalized candidate returned by any connector."""
    source: str
    source_id: str
    given: str = ""
    surname: str = ""
    birth_date: Optional[str] = None
    birth_place: str = ""
    death_date: Optional[str] = None
    death_place: str = ""
    detail_url: str = ""
    raw: dict = field(default_factory=dict)

    def as_dict(self):
        return asdict(self)


class BaseConnector:
    source_name = "base"
    timeout = 15

    def search(self, given: str, surname: str, year: Optional[int] = None) -> List[ExternalPerson]:
        raise NotImplementedError

    # ------------------------------------------------------------------

    def _get_json(self, url: str, headers: Optional[dict] = None) -> dict:
        req = urllib.request.Request(url, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout, context=_SSL_CTX) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise ConnectorError(f"{self.source_name} HTTP {e.code}: {e.reason}") from e
        except urllib.error.URLError as e:
            raise ConnectorError(f"{self.source_name} network error: {e.reason}") from e

    @staticmethod
    def _qs(params: dict) -> str:
        clean = {k: v for k, v in params.items() if v is not None and v != ""}
        return urllib.parse.urlencode(clean)


class ConnectorError(Exception):
    pass
