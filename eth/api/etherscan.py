from requests import Session

from automated_defi.api_utils import mount_timeout_and_retries
from automated_defi.errors import APIError
from automated_defi.eth import assets


class EtherscanAPI:
    """Etherscan API
    Documentation Link: https://docs.etherscan.io/"""

    def __init__(self, token):
        self.api_url = "https://api.etherscan.io/api"
        self.headers = {
            "Accepts": "application/json",
            "Authorization": token,
        }
        self.token = token
        self.session = mount_timeout_and_retries(Session())
        self.session.headers.update(self.headers)

    # Returns amount of gas needed (in Gwei) by user preferance: fast, average, and safe
    def select_gas_fee(self, execution_time: str) -> assets.GWEI:
        url = f"{self.api_url}?module=gastracker&action=gasoracle&apikey={self.token}"
        response = self.session.get(url)
        if response.status_code != 200:
            raise APIError(
                response.status_code, response.json().get("description", str(response))
            )

        if execution_time == "fast":
            fast_gas_price = response.json()["result"]["FastGasPrice"]
            return int(fast_gas_price)

        if execution_time == "average":
            avg_gas_price = response.json()["result"]["ProposeGasPrice"]
            return int(avg_gas_price)

        if execution_time == "safe":
            safe_gas_price = response.json()["result"]["SafeGasPrice"]
            return int(safe_gas_price)

        return 0
