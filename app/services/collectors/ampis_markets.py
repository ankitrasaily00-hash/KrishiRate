from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


AMPIS_BASE_URL = "https://ampis.gov.np"

MARKET_DIRECTORY_URL = (
    f"{AMPIS_BASE_URL}/contact-us"
)

DEFAULT_TIMEOUT = 30


@dataclass
class AMPISMarket:
    """
    Represents an agricultural market discovered from AMPIS.
    """

    name: str
    province: Optional[str] = None
    district: Optional[str] = None
    location: Optional[str] = None
    market_url: Optional[str] = None
    market_uuid: Optional[str] = None
    price_url: Optional[str] = None


class AMPISMarketCollector:
    """
    Discovers agricultural markets from the AMPIS
    market directory.

    AMPIS exposes market profile pages as:

        /agri-bajar/<UUID>

    The same UUID is used for daily price pages:

        /market-price/<UUID>
    """

    def __init__(
        self,
        base_url: str = AMPIS_BASE_URL,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        self.session = requests.Session()

        self.session.headers.update(
            {
                "User-Agent": (
                    "KrishiRate/1.0 "
                    "(Nepal Agriculture Price Intelligence Platform)"
                )
            }
        )

    # ---------------------------------------------------------
    # HTTP
    # ---------------------------------------------------------

    def fetch(
        self,
        url: str,
    ) -> str:
        """Fetch an AMPIS page."""

        response = self.session.get(
            url,
            timeout=self.timeout,
        )

        response.raise_for_status()

        return response.text

    # ---------------------------------------------------------
    # MARKET DISCOVERY
    # ---------------------------------------------------------

    def fetch_markets(
        self,
    ) -> list[AMPISMarket]:
        """
        Fetch agricultural markets from the AMPIS
        market directory.
        """

        html = self.fetch(
            MARKET_DIRECTORY_URL
        )

        return self.parse_markets(html)

    def parse_markets(
        self,
        html: str,
    ) -> list[AMPISMarket]:
        """
        Parse agricultural markets from the AMPIS
        contact/market directory.

        Expected table structure:

            Picture
            Market
            Province
            District
            Address
            Phone

        The market column contains an
        /agri-bajar/<UUID> link.
        """

        soup = BeautifulSoup(
            html,
            "lxml",
        )

        markets = []

        table = soup.find("table")

        if not table:
            return markets

        for row in table.find_all("tr"):
            cells = row.find_all("td")

            if len(cells) < 5:
                continue

            market_anchor = cells[1].find("a")

            if not market_anchor:
                continue

            raw_market_name = self._clean_text(
                market_anchor.get_text()
            )

            href = market_anchor.get("href")

            if not href:
                continue

            market_url = urljoin(
                self.base_url,
                href,
            )

            market_uuid = self._extract_market_uuid(
                market_url
            )

            if not market_uuid:
                continue

            province = self._clean_text(
                cells[2].get_text()
            )

            district = self._clean_text(
                cells[3].get_text()
            )

            location = self._clean_text(
                cells[4].get_text()
            )

            market_name = self._normalize_market_name(
                raw_market_name
            )

            # -------------------------------------------------
            # KALIMATI FALLBACK
            # -------------------------------------------------
            #
            # Kalimati's AMPIS row can have a different
            # organization-name structure. If the market
            # name cannot be extracted, use the address.
            #
            # Example:
            #
            #     कालीमाटी, काठमाडौं
            #
            # becomes:
            #
            #     कालीमाटी
            #

            if not market_name:
                market_name = self._market_name_from_location(
                    location
                )

            if not market_name:
                continue

            price_url = (
                f"{self.base_url}"
                f"/market-price/{market_uuid}"
            )

            markets.append(
                AMPISMarket(
                    name=market_name,
                    province=province or None,
                    district=district or None,
                    location=location or None,
                    market_url=market_url,
                    market_uuid=market_uuid,
                    price_url=price_url,
                )
            )

        return self._deduplicate_markets(
            markets
        )

    # ---------------------------------------------------------
    # MARKET NAME
    # ---------------------------------------------------------

    @staticmethod
    def _normalize_market_name(
        value: str,
    ) -> str:
        """
        Normalize AMPIS market organization names.

        Examples:

            कृषि बजार व्यवस्थापन समिति, बुटवल, रुपन्देही
                -> बुटवल

            कालीमाटी फलफूल तथा तरकारी बजार विकास समिति
                -> कालीमाटी
        """

        value = " ".join(
            value.split()
        ).strip()

        if not value:
            return ""

        # Exact Kalimati organization name.
        if (
            "कालीमाटी फलफूल तथा तरकारी बजार विकास समिति"
            in value
        ):
            return "कालीमाटी"

        prefixes = (
            "कृषि बजार व्यवस्थापन समिति,",
            "कृषि बजार व्यवस्थापन समिति",
        )

        for prefix in prefixes:
            if value.startswith(prefix):
                value = value[
                    len(prefix):
                ].strip()
                break

        # Some AMPIS names contain additional geographic
        # information separated by commas.
        if "," in value:
            value = value.split(
                ",",
                1,
            )[0].strip()

        return value

    @staticmethod
    def _market_name_from_location(
        location: str,
    ) -> str:
        """
        Extract a market name from its address.

        Example:

            कालीमाटी, काठमाडौं

        becomes:

            कालीमाटी
        """

        if not location:
            return ""

        if "," in location:
            return location.split(
                ",",
                1,
            )[0].strip()

        return location.strip()

    # ---------------------------------------------------------
    # UUID
    # ---------------------------------------------------------

    @staticmethod
    def _extract_market_uuid(
        url: str,
    ) -> Optional[str]:
        """
        Extract UUID from an AMPIS market URL.

        Supported:

            /agri-bajar/<UUID>

        and:

            /market-price/<UUID>
        """

        markers = (
            "/agri-bajar/",
            "/market-price/",
        )

        for marker in markers:
            if marker not in url:
                continue

            value = url.split(
                marker,
                1,
            )[1]

            value = value.split(
                "?",
                1,
            )[0]

            value = value.split(
                "#",
                1,
            )[0]

            value = value.strip("/")

            if value:
                return value

        return None

    # ---------------------------------------------------------
    # HELPERS
    # ---------------------------------------------------------

    @staticmethod
    def _clean_text(
        value: str,
    ) -> str:
        """Normalize whitespace."""

        return " ".join(
            value.split()
        ).strip()

    @staticmethod
    def _deduplicate_markets(
        markets: list[AMPISMarket],
    ) -> list[AMPISMarket]:
        """
        Remove duplicate markets.

        UUID is the preferred stable identity.
        """

        unique = {}

        for market in markets:
            key = (
                market.market_uuid
                or market.location
                or market.name
            )

            if not key:
                continue

            unique[key] = market

        return list(
            unique.values()
        )

    # ---------------------------------------------------------
    # CLEANUP
    # ---------------------------------------------------------

    def close(self) -> None:
        """Close HTTP session."""

        self.session.close()

    def __enter__(
        self,
    ) -> "AMPISMarketCollector":
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        self.close()