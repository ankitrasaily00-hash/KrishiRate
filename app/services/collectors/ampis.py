from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Optional

import requests
from bs4 import BeautifulSoup
from bikram_sambat import date as bs_date


AMPIS_BASE_URL = "https://ampis.gov.np"
AVAILABLE_COMMODITIES_URL = f"{AMPIS_BASE_URL}/available-commodity"
DEFAULT_TIMEOUT = 30


NEPALI_MONTHS = {
    "बैशाख": 1,
    "वैशाख": 1,
    "जेठ": 2,
    "असार": 3,
    "श्रावण": 4,
    "साउन": 4,
    "भाद्र": 5,
    "भदौ": 5,
    "आश्विन": 6,
    "असोज": 6,
    "कार्तिक": 7,
    "मंसिर": 8,
    "पौष": 9,
    "पुष": 9,
    "माघ": 10,
    "फाल्गुण": 11,
    "फागुन": 11,
    "चैत्र": 12,
}


@dataclass
class AMPISCommodity:
    code: str
    name: str


@dataclass
class AMPISPrice:
    commodity_code: Optional[str]
    commodity: str
    unit: str
    minimum: Optional[Decimal]
    maximum: Optional[Decimal]
    average: Optional[Decimal]
    price_date: date


class AMPISCollector:
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
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/140.0 Safari/537.36"
                )
            }
        )

    def fetch(self, url: str) -> str:
        response = self.session.get(
            url,
            timeout=self.timeout,
        )

        response.raise_for_status()

        response.encoding = (
            response.apparent_encoding or response.encoding
        )

        return response.text

    @staticmethod
    def _normalize_text(value: Optional[str]) -> str:
        if not value:
            return ""

        return " ".join(
            value.replace("\xa0", " ").split()
        ).strip()

    @staticmethod
    def _normalize_nepali_digits(value: str) -> str:
        translation = str.maketrans(
            "०१२३४५६७८९",
            "0123456789",
        )

        return value.translate(translation)

    @staticmethod
    def _parse_decimal(
        value: Optional[str],
    ) -> Optional[Decimal]:
        if not value:
            return None

        value = value.strip()
        value = value.replace(",", "")
        value = value.replace("रु.", "")
        value = value.replace("रु", "")
        value = value.strip()

        if not value:
            return None

        value = AMPISCollector._normalize_nepali_digits(value)

        try:
            return Decimal(value)
        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def _bs_to_ad(
        year: int,
        month: int,
        day: int,
    ) -> date:
        try:
            converted = bs_date(
                year,
                month,
                day,
            ).togregorian()
        except Exception as exc:
            raise ValueError(
                f"Unable to convert BS date "
                f"{year}-{month:02d}-{day:02d}: {exc}"
            ) from exc

        if isinstance(converted, date):
            return converted

        return converted.date()

    @classmethod
    def _parse_nepali_date(
        cls,
        value: str,
    ) -> date:
        value = cls._normalize_text(value)

        if not value:
            raise ValueError("Empty AMPIS date")

        value = cls._normalize_nepali_digits(value)
        value = value.replace(",", " ")

        parts = value.split()

        if len(parts) < 3:
            raise ValueError(
                f"Invalid AMPIS Nepali date: {value}"
            )

        month_text = parts[0]
        day_text = parts[1]
        year_text = parts[2]

        month = NEPALI_MONTHS.get(month_text)

        if month is None:
            english_months = {
                "baishakh": 1,
                "baisakh": 1,
                "jestha": 2,
                "jetha": 2,
                "ashadh": 3,
                "asad": 3,
                "shrawan": 4,
                "shravan": 4,
                "saun": 4,
                "bhadra": 5,
                "ashwin": 6,
                "asoj": 6,
                "kartik": 7,
                "mangsir": 8,
                "poush": 9,
                "push": 9,
                "magh": 10,
                "falgun": 11,
                "fagun": 11,
                "chaitra": 12,
            }

            month = english_months.get(
                month_text.lower()
            )

        if month is None:
            raise ValueError(
                f"Unknown AMPIS Nepali month: {month_text}"
            )

        try:
            day = int(day_text)
            year = int(year_text)
        except ValueError as exc:
            raise ValueError(
                f"Invalid AMPIS date numbers: {value}"
            ) from exc

        if year < 1900 or year > 2200:
            raise ValueError(
                f"Unsupported AMPIS BS year: {year}"
            )

        if day < 1 or day > 32:
            raise ValueError(
                f"Invalid AMPIS BS day: {day}"
            )

        return cls._bs_to_ad(
            year,
            month,
            day,
        )

    @classmethod
    def parse_source_date(
        cls,
        html: str,
    ) -> date:
        soup = BeautifulSoup(
            html,
            "html.parser",
        )

        date_element = soup.select_one(
            ".export-title-date"
        )

        if not date_element:
            raise ValueError(
                "AMPIS source date element "
                "'.export-title-date' was not found"
            )

        raw_date = cls._normalize_text(
            date_element.get_text(
                " ",
                strip=True,
            )
        )

        if not raw_date:
            raise ValueError(
                "AMPIS source date is empty"
            )

        return cls._parse_nepali_date(
            raw_date
        )

    def get_available_commodities(
        self,
    ) -> list[AMPISCommodity]:
        html = self.fetch(
            AVAILABLE_COMMODITIES_URL
        )

        soup = BeautifulSoup(
            html,
            "html.parser",
        )

        commodities: list[AMPISCommodity] = []
        seen: set[str] = set()

        for row in soup.select(
            "table tbody tr"
        ):
            cells = row.find_all("td")

            if len(cells) < 2:
                continue

            code = self._normalize_text(
                cells[0].get_text(
                    " ",
                    strip=True,
                )
            )

            name = self._normalize_text(
                cells[1].get_text(
                    " ",
                    strip=True,
                )
            )

            if not name:
                continue

            key = code or name

            if key in seen:
                continue

            seen.add(key)

            commodities.append(
                AMPISCommodity(
                    code=code,
                    name=name,
                )
            )

        return commodities

    def parse_price_page(
        self,
        html: str,
        price_date: Optional[date] = None,
        commodities: Optional[
            list[AMPISCommodity]
        ] = None,
    ) -> list[AMPISPrice]:
        soup = BeautifulSoup(
            html,
            "html.parser",
        )

        source_date = self.parse_source_date(
            html
        )

        commodity_lookup: dict[str, str] = {}

        if commodities:
            for commodity in commodities:
                normalized_name = self._normalize_text(
                    commodity.name
                )

                if normalized_name:
                    commodity_lookup[
                        normalized_name
                    ] = commodity.code

        prices: list[AMPISPrice] = []

        for table in soup.find_all("table"):
            rows = table.select("tbody tr")

            if not rows:
                rows = table.find_all("tr")

            for row in rows:
                cells = row.find_all("td")

                if len(cells) < 4:
                    continue

                values = [
                    self._normalize_text(
                        cell.get_text(
                            " ",
                            strip=True,
                        )
                    )
                    for cell in cells
                ]

                if not values:
                    continue

                commodity_name = values[0]

                if not commodity_name:
                    continue

                header_text = commodity_name.lower()

                if (
                    "commodity" in header_text
                    or "वस्तु" in commodity_name
                    or "कृषि उपज" in commodity_name
                ):
                    continue

                unit = (
                    values[1]
                    if len(values) > 1
                    else ""
                )

                minimum = (
                    self._parse_decimal(values[2])
                    if len(values) > 2
                    else None
                )

                maximum = (
                    self._parse_decimal(values[3])
                    if len(values) > 3
                    else None
                )

                average = (
                    self._parse_decimal(values[4])
                    if len(values) > 4
                    else None
                )

                if (
                    average is None
                    and minimum is not None
                    and maximum is not None
                ):
                    average = (
                        minimum + maximum
                    ) / Decimal("2")

                if (
                    minimum is None
                    and maximum is None
                    and average is None
                ):
                    continue

                commodity_code = commodity_lookup.get(
                    commodity_name
                )

                prices.append(
                    AMPISPrice(
                        commodity_code=commodity_code,
                        commodity=commodity_name,
                        unit=unit,
                        minimum=minimum,
                        maximum=maximum,
                        average=average,
                        price_date=source_date,
                    )
                )

        return prices

    def get_market_prices(
        self,
        market_url: str,
        commodities: Optional[
            list[AMPISCommodity]
        ] = None,
    ) -> list[AMPISPrice]:
        html = self.fetch(
            market_url
        )

        return self.parse_price_page(
            html,
            commodities=commodities,
        )

    def fetch_commodities(
        self,
    ) -> list[AMPISCommodity]:
        return self.get_available_commodities()

    def close(self) -> None:
        self.session.close()

