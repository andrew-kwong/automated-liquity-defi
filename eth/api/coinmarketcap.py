from decimal import Decimal
from typing import Dict, List

from requests import Session

from automated_defi.api_utils import mount_timeout_and_retries
from automated_defi.errors import APIError


class CoinMarketCapAPI:
    """CoinMarketCap API
    Documentation Link: https://coinmarketcap.com/api/documentation/v1/#section/Introduction"""

    def __init__(self, token):
        self.api_url = "https://pro-api.coinmarketcap.com"
        self.headers = {
            "Accepts": "application/json",
            "X-CMC_PRO_API_KEY": token,
        }
        self.session = mount_timeout_and_retries(Session())
        self.session.headers.update(self.headers)

    def get_price(self, id: str) -> Decimal:
        """Returns latest price quote of token identified by CoinMarketCAP's token-`id`."""
        url = f"{self.api_url}/v2/cryptocurrency/quotes/latest"
        response = self.session.get(url, params={"id": id})
        if response.status_code != 200:
            raise APIError(
                response.status_code, response.json().get("description", str(response))
            )
        current_price = response.json()["data"][id]["quote"]["USD"]["price"]

        return Decimal(current_price)

    def get_prices_by_symbol(self, symbols: List[str]) -> Dict[str, Decimal]:
        """Returns latest price quote of token identified by `symbol` in USD."""
        url = f"{self.api_url}/v2/cryptocurrency/quotes/latest"
        response = self.session.get(
            url, params={"symbol": ",".join([symbol.upper() for symbol in symbols])}
        )
        if response.status_code != 200:
            raise APIError(
                response.status_code, response.json().get("description", str(response))
            )

        data = response.json()["data"]
        return {
            symbol: Decimal(data[symbol.upper()][0]["quote"]["USD"]["price"])
            for symbol in symbols
        }

    # Returns percent change of the token in the past hour
    def get_hourly_percent_change(self, id: str) -> Decimal:
        url = f"{self.api_url}/v2/cryptocurrency/quotes/latest"
        parameters = {"id": id}
        response = self.session.get(url, params=parameters)
        if response.status_code != 200:
            raise APIError(
                response.status_code, response.json().get("description", str(response))
            )
        hour_percent = response.json()["data"][id]["quote"]["USD"]["percent_change_1h"]

        return Decimal(hour_percent)

    # Returns percent change of token in the past 24 hours
    def get_daily_percent_change(self, id: str) -> Decimal:
        url = f"{self.api_url}/v2/cryptocurrency/quotes/latest"
        parameters = {"id": id}
        response = self.session.get(url, params=parameters)
        if response.status_code != 200:
            raise APIError(
                response.status_code, response.json().get("description", str(response))
            )
        daily_percent = response.json()["data"][id]["quote"]["USD"][
            "percent_change_24h"
        ]

        return Decimal(daily_percent)

    # Returns the volume of the token that was traded in the past 24 hours
    def get_daily_volume(self, id: str) -> Decimal:
        url = f"{self.api_url}/v2/cryptocurrency/quotes/latest"
        parameters = {"id": id}
        response = self.session.get(url, params=parameters)
        if response.status_code != 200:
            raise APIError(
                response.status_code, response.json().get("description", str(response))
            )
        daily_volume = response.json()["data"][id]["quote"]["USD"]["volume_24h"]

        return Decimal(daily_volume)
