from decimal import Decimal

from requests import Session

from automated_defi.api_utils import mount_timeout_and_retries
from automated_defi.errors import APIError


class NomicsAPI:
    """Nomics API
    To be used as secondary fallback
    Currencies Ticker Endpoint is the only free api endpoint by Nomics
    Documentation Link: https://nomics.com/docs/#tag/Currencies-Ticker"""

    def __init__(self):
        self.api_url = "https://api.nomics.com"
        self._client = mount_timeout_and_retries(Session())

    # Returns latest price quote
    def get_price(self, token, symbol) -> Decimal:
        url = f"{self.api_url}/v1/currencies/ticker?key={token}&ids={symbol}"
        response = self._client.get(url)
        if response.status_code != 200:
            raise APIError(
                response.status_code, response.json().get("description", str(response))
            )
        current_price = response.json()[0]["price"]

        return Decimal(current_price)

    # Returns percent change of the token in the past hour
    def get_hourly_percent_change(self, token, symbol) -> Decimal:
        url = (
            f"{self.api_url}/v1/currencies/ticker?key={token}&ids={symbol}&interval=1h"
        )
        response = self._client.get(url)
        if response.status_code != 200:
            raise APIError(
                response.status_code, response.json().get("description", str(response))
            )
        hour_percent = response.json()[0]["1h"]["price_change_pct"]

        return Decimal(hour_percent) * 100

    # Returns percent change of token in the past 24 hours
    def get_daily_percent_change(self, token, symbol) -> Decimal:
        url = (
            f"{self.api_url}/v1/currencies/ticker?key={token}&ids={symbol}&interval=1d"
        )
        response = self._client.get(url)
        if response.status_code != 200:
            raise APIError(
                response.status_code, response.json().get("description", str(response))
            )
        daily_percent = response.json()[0]["1d"]["price_change_pct"]

        return Decimal(daily_percent) * 100

    # Returns the volume of the token that was traded in the past 24 hours
    def get_daily_volume(self, token, symbol) -> Decimal:
        url = (
            f"{self.api_url}/v1/currencies/ticker?key={token}&ids={symbol}&interval=1d"
        )
        response = self._client.get(url)
        if response.status_code != 200:
            raise APIError(
                response.status_code, response.json().get("description", str(response))
            )
        daily_volume = response.json()[0]["1d"]["volume"]

        return Decimal(daily_volume)
