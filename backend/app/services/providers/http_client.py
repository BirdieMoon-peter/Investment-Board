import httpx
import time

DEFAULT_PROVIDER_TIMEOUT = 25.0
DEFAULT_PROVIDER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/136.0.0.0 Safari/537.36"
    ),
    "Referer": "https://quote.eastmoney.com/",
}


def build_provider_client(
    *, transport: httpx.BaseTransport | None = None
) -> httpx.Client:
    return httpx.Client(
        headers=DEFAULT_PROVIDER_HEADERS.copy(),
        timeout=httpx.Timeout(DEFAULT_PROVIDER_TIMEOUT),
        transport=transport,
    )


def retry_request(client: httpx.Client, method: str, url: str, max_retries: int = 5, **kwargs) -> httpx.Response:
    """Retry HTTP requests with exponential backoff for connection errors."""
    last_exc = None
    for attempt in range(max_retries):
        try:
            response = client.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except (httpx.RemoteProtocolError, httpx.ConnectError, httpx.ReadTimeout) as exc:
            last_exc = exc
            if attempt < max_retries - 1:
                time.sleep(1.0 * (attempt + 1))  # 1s, 2s, 3s, 4s, 5s
    raise last_exc
