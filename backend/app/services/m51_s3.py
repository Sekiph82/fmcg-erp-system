"""M51.S01.T010 minimal S3-compatible object client (MinIO, Ceph, AWS S3) with AWS Signature Version 4 header signing.

Contract: Amazon S3 REST API + SigV4 "Authenticating requests: using the Authorization header"
  https://docs.aws.amazon.com/AmazonS3/latest/API/sigv4-auth-using-authorization-header.html (SigV4, service "s3")
Operations: PutObject, GetObject (Range), HeadObject, DeleteObject, CreateMultipartUpload, UploadPart,
CompleteMultipartUpload, AbortMultipartUpload, ListParts  https://docs.aws.amazon.com/AmazonS3/latest/API/API_Operations_Amazon_Simple_Storage_Service.html
Every request goes through provider_http.provider_client(), so PROVIDER_EGRESS=local only reaches loopback/.test hosts
(MinIO in a disposable container) and live mode pins DNS. Path-style addressing (endpoint/bucket/key) is used.
Errors: 4xx/5xx carry <Error><Code>; 5xx/429/SlowDown are retried with backoff, everything else raises S3Error.
Why not boto3: it is synchronous, bypasses the egress guard and adds a heavy dependency; tests cross-check this
signer byte-for-byte against botocore when botocore is installed.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import re
from datetime import datetime, timezone
from typing import AsyncIterator, Optional
from urllib.parse import parse_qsl, quote, urlsplit

from app.core.provider_http import provider_client


class S3Error(RuntimeError):
    def __init__(self, status: int, code: str, message: str = ""):
        super().__init__(f"S3 {status} {code}: {message}"[:300])
        self.status, self.code = status, code


def _enc(s: str, safe: str = "-_.~") -> str:
    return quote(s, safe=safe)


def sign_headers(method: str, url: str, headers: dict, payload_hash: str, access_key: str, secret_key: str,
                 region: str, now: Optional[datetime] = None) -> dict:
    """Return headers + x-amz-date, x-amz-content-sha256 and Authorization for this request."""
    now = now or datetime.now(timezone.utc)
    amz_date, day = now.strftime("%Y%m%dT%H%M%SZ"), now.strftime("%Y%m%d")
    parts = urlsplit(url)
    h = {k.lower(): str(v).strip() for k, v in headers.items()}
    h["host"] = parts.netloc
    h["x-amz-date"] = amz_date
    h["x-amz-content-sha256"] = payload_hash
    query = "&".join(f"{_enc(k)}={_enc(v)}" for k, v in sorted(parse_qsl(parts.query, keep_blank_values=True)))
    names = sorted(h)
    canonical = "\n".join([method, parts.path or "/", query,
                           "".join(f"{n}:{h[n]}\n" for n in names), ";".join(names), payload_hash])
    scope = f"{day}/{region}/s3/aws4_request"
    to_sign = "\n".join(["AWS4-HMAC-SHA256", amz_date, scope, hashlib.sha256(canonical.encode()).hexdigest()])
    k = ("AWS4" + secret_key).encode()
    for part in (day, region, "s3", "aws4_request"):
        k = hmac.new(k, part.encode(), hashlib.sha256).digest()
    sig = hmac.new(k, to_sign.encode(), hashlib.sha256).hexdigest()
    h["authorization"] = f"AWS4-HMAC-SHA256 Credential={access_key}/{scope}, SignedHeaders={';'.join(names)}, Signature={sig}"
    return h


class S3Client:
    def __init__(self, endpoint: str, bucket: str, access_key: str, secret_key: str, region: str = "us-east-1",
                 retries: int = 3, backoff: float = 0.5):
        if not (endpoint and bucket and access_key and secret_key):
            raise S3Error(0, "NotConfigured", "S3 endpoint, bucket and credentials are required")
        self.endpoint, self.bucket = endpoint.rstrip("/"), bucket
        self.ak, self.sk, self.region, self.retries, self.backoff = access_key, secret_key, region, retries, backoff

    def _url(self, key: str = "", query: str = "") -> str:
        path = f"/{self.bucket}" + (f"/{_enc(key, '/-_.~')}" if key else "")
        return f"{self.endpoint}{path}" + (f"?{query}" if query else "")

    async def _req(self, method: str, key: str = "", query: str = "", body: bytes = b"", headers: Optional[dict] = None,
                   ok: tuple = (200, 204), stream: bool = False):
        for attempt in range(self.retries + 1):
            url = self._url(key, query)
            h = sign_headers(method, url, headers or {}, hashlib.sha256(body).hexdigest(), self.ak, self.sk, self.region)
            h.pop("host")                      # httpx sets Host itself (same value)
            async with provider_client(timeout=60.0) as c:
                r = await c.request(method, url, headers=h, content=body)
            if r.status_code in ok:
                return r
            code = (re.search(r"<Code>([^<]+)</Code>", r.text) or [None, f"HTTP{r.status_code}"])[1]
            if (r.status_code >= 500 or r.status_code == 429 or code == "SlowDown") and attempt < self.retries:
                await asyncio.sleep(min(float(r.headers.get("Retry-After", self.backoff * 2 ** attempt)), 5))
                continue
            raise S3Error(r.status_code, code, r.text[:200])

    async def create_bucket(self) -> None:
        """Setup helper (tests / first run): CreateBucket; an existing bucket of ours is fine."""
        await self._req("PUT", "", ok=(200, 409))

    async def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        r = await self._req("PUT", key, body=data, headers={"content-type": content_type})
        return r.headers.get("etag", "").strip('"')

    async def head(self, key: str) -> Optional[dict]:
        try:
            r = await self._req("HEAD", key)
        except S3Error as e:
            if e.status == 404:
                return None
            raise
        return {"size": int(r.headers.get("content-length", 0)), "etag": r.headers.get("etag", "").strip('"')}

    async def get_range(self, key: str, start: int, end: int) -> bytes:
        """Inclusive byte range [start, end]; 206 (or 200 when the whole object was returned)."""
        r = await self._req("GET", key, headers={"range": f"bytes={start}-{end}"}, ok=(200, 206))
        return r.content

    async def iter_range(self, key: str, start: int, end: int, chunk: int = 1 << 20) -> AsyncIterator[bytes]:
        for s in range(start, end + 1, chunk):
            yield await self.get_range(key, s, min(s + chunk - 1, end))

    async def delete(self, key: str) -> None:
        await self._req("DELETE", key, ok=(200, 204, 404))

    async def create_multipart(self, key: str, content_type: str = "application/octet-stream") -> str:
        r = await self._req("POST", key, query="uploads=", headers={"content-type": content_type})
        m = re.search(r"<UploadId>([^<]+)</UploadId>", r.text)
        if not m:
            raise S3Error(r.status_code, "BadResponse", "no UploadId")
        return m.group(1)

    async def upload_part(self, key: str, upload_id: str, number: int, data: bytes) -> str:
        r = await self._req("PUT", key, query=f"partNumber={number}&uploadId={_enc(upload_id)}", body=data)
        return r.headers.get("etag", "").strip('"')

    async def complete_multipart(self, key: str, upload_id: str, parts: list[tuple[int, str]]) -> None:
        xml = "<CompleteMultipartUpload>" + "".join(
            f"<Part><PartNumber>{n}</PartNumber><ETag>\"{e}\"</ETag></Part>" for n, e in sorted(parts)) + "</CompleteMultipartUpload>"
        r = await self._req("POST", key, query=f"uploadId={_enc(upload_id)}", body=xml.encode(), headers={"content-type": "application/xml"})
        if "<Error>" in r.text:                 # S3 may answer 200 with an error document
            raise S3Error(200, (re.search(r"<Code>([^<]+)", r.text) or [None, "CompleteFailed"])[1], r.text[:200])

    async def abort_multipart(self, key: str, upload_id: str) -> None:
        await self._req("DELETE", key, query=f"uploadId={_enc(upload_id)}", ok=(200, 204, 404))

    async def list_parts(self, key: str, upload_id: str) -> dict[int, int]:
        """{part number: size} of parts already received (resume support). Pages of 1000 are followed."""
        out: dict[int, int] = {}
        marker = 0
        while True:
            r = await self._req("GET", key, query=f"part-number-marker={marker}&uploadId={_enc(upload_id)}", ok=(200, 404))
            if r.status_code == 404:
                return out
            for m in re.finditer(r"<Part>.*?<PartNumber>(\d+)</PartNumber>.*?<Size>(\d+)</Size>.*?</Part>", r.text, re.S):
                out[int(m.group(1))] = int(m.group(2))
            nxt = re.search(r"<NextPartNumberMarker>(\d+)</NextPartNumberMarker>", r.text)
            if "<IsTruncated>true</IsTruncated>" in r.text and nxt:
                marker = int(nxt.group(1))
                continue
            return out
