import json

import httpx
import hmac
import hashlib


class AIFORYClient:
    def __init__(self, api_key: str, secret_key: str, user_agent: str):
        self.api_key = api_key
        self.secret_key = secret_key
        self.crypto_methods = [1015, 1013, 1002, 1003, 1004, 1027, 1008, 1005, 1021, 1010]
        self.rub_methods = [10, 3, 61]
        self.headers = {"Content-Type": "application/json", "API-Key": api_key, "user-agent": user_agent}
        self.session = httpx.AsyncClient(headers=self.headers, base_url="https://api.aifory.io/")

    @staticmethod
    def sign_data(key: str, msg: str) -> str:
        return hmac.new(key.encode(), msg.encode(), hashlib.sha512).hexdigest()

    @staticmethod
    def analyze_response(resp):
        try:
            return resp.json()
        except json.decoder.JSONDecodeError:
            print(f"Error converting response to json - {resp.text}")
            raise
        except httpx.HTTPError:
            print(f"Wrong code status - {resp.status_code} {resp.text}")
            raise

    async def get(self, url: str):
        self.session.headers.update({"Signature": self.sign_data(self.secret_key, "")})
        resp = await self.session.get(url=url)
        return self.analyze_response(resp)

    async def post(self, url: str, body: dict):
        self.session.headers.update({"Signature": self.sign_data(self.secret_key, json.dumps(body))})
        resp = await self.session.post(url=url, json=body)
        return self.analyze_response(resp)

    async def balance(self, currency: str):
        url = "account/balance"
        res = await self.get(url=url)
        return list(filter(lambda x: x["currencyName"] == currency, res))[0]['balance']

    async def create_invoice(self,
                             amount: int | float,
                             invoice_id: str,
                             ttl: int,
                             web_hook_url: str,
                             success_url: str,
                             failed_url: str,
                             ip: str,
                             user_id: str,
                             time_register: int,
                             payment_type_id: int):
        url = "payin/process"
        body = {
            "amount": amount,
            "currencyID": 3,
            "typeID": payment_type_id,
            "clientOrderID": invoice_id,
            "webhookURL": web_hook_url,
            "TTL": ttl,
            "extra": {
                "payerInfo": {"IP": ip,
                              "userID": user_id,
                              "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6_1 like Mac OS X) AppleWebKit/655.1.15 (KHTML, like Gecko) Version/16.4 Mobile/148 Safari/04.1",
                              "registeredAt": int(time_register)
                              },
                "comment": "Test payment",
                "allowedMethodIDs": self.crypto_methods if payment_type_id in self.crypto_methods else self.rub_methods,
                "successRedirectURL": success_url,
                "failedRedirectURL": failed_url
            }
        }
        return await self.post(url=url, body=body)

    async def status_invoice(self, invoice_id: str):
        url = "payin/details"
        body = {
            "clientOrderID": invoice_id
        }
        return await self.post(url=url, body=body)

    async def create_withdraw(self,
                              invoice_id: str,
                              amount: int,
                              recipient_type_id: int,
                              wallet: int,
                              web_hook: str):
        url = "payout/process"
        body = {
            "currencyID": 3,
            "amount": amount,
            "recipientTypeID": recipient_type_id,
            "recipient": wallet,
            "clientOrderID": invoice_id,
            "webhookURL": web_hook
        }
        return await self.post(url=url, body=body)

    def validate_credit_card(self, card_number):
        # Удаление пробелов и дефисов из номера карты
        card_number = card_number.replace(" ", "").replace("-", "")

        # Проверка, что номер карты состоит только из цифр
        if not card_number.isdigit():
            return False

        # Проверка длины номера карты
        if len(card_number) < 13 or len(card_number) > 16:
            return False

        # Реверсирование номера карты
        reversed_card_number = card_number[::-1]

        # Вычисление контрольной суммы
        total = 0
        for index, digit in enumerate(reversed_card_number):
            if index % 2 == 1:
                doubled_digit = int(digit) * 2
                if doubled_digit > 9:
                    doubled_digit -= 9
                total += doubled_digit
            else:
                total += int(digit)

        # Проверка валидности
        return total % 10 == 0

    def get_status(self, status):
        states = {
            1: "process (order pending)",
            2: "success",
            3: "failed (failed order)",
        }
        return states.get(status, status)