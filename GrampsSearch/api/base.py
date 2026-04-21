"""Base connector — normalizes API results to a common shape."""

import json
import urllib.request
import urllib.parse
import urllib.error
from dataclasses import dataclass, field, asdict
from typing import Optional, List


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
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
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
