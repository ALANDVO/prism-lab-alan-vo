"""OIDC Keycloak client for authentication."""
import httpx
from typing import Optional
from app.core.config import settings
from app.core.security import generate_state, generate_nonce, generate_pkce_verifier, generate_pkce_challenge


class OIDCClient:
    def __init__(self):
        self.issuer_url = settings.oidc_issuer_url.rstrip("/")
        self.client_id = settings.oidc_client_id
        self.client_secret = settings.oidc_client_secret
        self.redirect_uri = settings.oidc_redirect_uri
        self.scopes = settings.oidc_scopes
        self._discovery: Optional[dict] = None
        self._jwks: Optional[dict] = None

    async def get_discovery(self) -> dict:
        if self._discovery is None:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.issuer_url}/.well-known/openid-configuration")
                resp.raise_for_status()
                self._discovery = resp.json()
        return self._discovery

    async def get_jwks(self) -> dict:
        if self._jwks is None:
            discovery = await self.get_discovery()
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(discovery["jwks_uri"])
                resp.raise_for_status()
                self._jwks = resp.json()
        return self._jwks

    def build_authorization_url(self) -> tuple[str, str, str, str]:
        """Returns (auth_url, state, nonce, pkce_verifier)"""
        discovery = self._discovery or {}
        auth_endpoint = discovery.get("authorization_endpoint", f"{self.issuer_url}/protocol/openid-connect/auth")

        state = generate_state()
        nonce = generate_nonce()
        pkce_verifier = generate_pkce_verifier()
        pkce_challenge = generate_pkce_challenge(pkce_verifier)

        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": self.scopes,
            "state": state,
            "nonce": nonce,
            "code_challenge": pkce_challenge,
            "code_challenge_method": "S256",
        }

        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{auth_endpoint}?{query}", state, nonce, pkce_verifier

    async def exchange_code_for_tokens(self, code: str, pkce_verifier: str) -> dict:
        discovery = await self.get_discovery()
        token_endpoint = discovery["token_endpoint"]

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "code_verifier": pkce_verifier,
        }

        if self.client_secret:
            data["client_secret"] = self.client_secret

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(token_endpoint, data=data)
            resp.raise_for_status()
            return resp.json()

    async def validate_id_token(self, id_token: str, nonce: str) -> Optional[dict]:
        """Validate ID token signature, issuer, audience, and nonce."""
        from jose import jwt, JWTError
        try:
            jwks = await self.get_jwks()
            # Extract kid from token header
            header = jwt.get_unverified_header(id_token)
            kid = header.get("kid")
            if not kid:
                return None

            # Find matching key
            key = None
            for k in jwks.get("keys", []):
                if k.get("kid") == kid:
                    key = k
                    break
            if not key:
                return None

            # Convert JWK to PEM format for jose
            from jose.utils import base64url_decode
            import json

            n = base64url_decode(key["n"].encode() + b"==")
            e = base64url_decode(key["e"].encode() + b"==")
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.hazmat.primitives import serialization

            public_key = rsa.RSAPublicNumbers(
                int.from_bytes(e, "big"),
                int.from_bytes(n, "big")
            ).public_key()

            pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )

            payload = jwt.decode(
                id_token,
                pem,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=self.issuer_url,
                options={"verify_nonce": False}  # We verify nonce manually
            )

            if payload.get("nonce") != nonce:
                return None

            return payload
        except (JWTError, KeyError, ValueError):
            return None

    async def logout_url(self, id_token_hint: Optional[str] = None) -> str:
        discovery = await self.get_discovery()
        end_session_endpoint = discovery.get("end_session_endpoint", f"{self.issuer_url}/protocol/openid-connect/logout")
        params = {"client_id": self.client_id, "post_logout_redirect_uri": settings.frontend_url}
        if id_token_hint:
            params["id_token_hint"] = id_token_hint
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{end_session_endpoint}?{query}"


oidc_client = OIDCClient()