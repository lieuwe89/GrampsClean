"""GenealogieOnline.nl connector — OAuth2 (authorization code flow).

Register an app at https://www.genealogieonline.nl/en/api/ to obtain
client_id / client_secret. Token is cached in memory; persist it
via prefs.py if you want it to survive restarts.
"""

import json
import time
import urllib.parse
import urllib.request
from typing import List, Optional

from .base import BaseConnector, ExternalPerson, ConnectorError


class GenealogieOnlineClient(BaseConnector):
    source_name = "genealogieonline"
    authorize_url = "https://www.genealogieonline.nl/oauth/authorize"
    token_url = "https://www.genealogieonline.nl/oauth/token"
    api_base = "https://www.genealogieonline.nl/api/v1"

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self._token: Optional[str] = None
        self._token_expires_at: float = 0

    # ------------------------------------------------------------------
    # OAuth2 — authorization code flow
    # ------------------------------------------------------------------

    def build_authorize_url(self, state: str = "") -> str:
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "read",
            "state": state,
        }
        return f"{self.authorize_url}?{urllib.parse.urlencode(params)}"

    def exchange_code(self, code: str) -> None:
        body = urllib.parse.urlencode({
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }).encode("utf-8")
        req = urllib.request.Request(self.token_url, data=body, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                payload = json.loads(r.read().decode("utf-8"))
        except Exception as e:
            raise ConnectorError(f"OAuth token exchange failed: {e}") from e

        self._token = payload.get("access_token")
        ttl = int(payload.get("expires_in", 3600))
        self._token_expires_at = time.time() + ttl - 30
        if not self._token:
            raise ConnectorError("No access_token in OAuth response")

    def set_token(self, token: str, expires_at: float = 0) -> None:
        self._token = token
        self._token_expires_at = expires_at or (time.time() + 3600)

    def _auth_headers(self) -> dict:
        if not self._token or time.time() >= self._token_expires_at:
            raise ConnectorError("Not authorized — run OAuth flow first")
        return {"Authorization": f"Bearer {self._token}"}

    # ------------------------------------------------------------------

    def search(
        self,
        given: str,
        surname: str,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
    ) -> List[ExternalPerson]:
        params = {
            "firstname": given,
            "lastname": surname,
            "birth_year_from": year_from,
            "birth_year_to": year_to,
        }
        url = f"{self.api_base}/persons?{self._qs(params)}"
        data = self._get_json(url, headers=self._auth_headers())
        return [self._normalize(rec) for rec in data.get("results", [])]

    def _normalize(self, rec: dict) -> ExternalPerson:
        return ExternalPerson(
            source=self.source_name,
            source_id=str(rec.get("id", "")),
            given=rec.get("firstname", ""),
            surname=rec.get("lastname", ""),
            birth_date=rec.get("birth_date"),
            birth_place=rec.get("birth_place", ""),
            death_date=rec.get("death_date"),
            death_place=rec.get("death_place", ""),
            detail_url=rec.get("url", ""),
            raw=rec,
        )
