import httpx

DEFAULT_PROVIDER_TIMEOUT = 10.0
DEFAULT_PROVIDER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/136.0.0.0 Safari/537.36"
    )
}


def build_provider_client(
    *, transport: httpx.BaseTransport | None = None
) -> httpx.Client:
    return httpx.Client(
        headers=DEFAULT_PROVIDER_HEADERS.copy(),
        timeout=httpx.Timeout(DEFAULT_PROVIDER_TIMEOUT),
        transport=transport,
    )
