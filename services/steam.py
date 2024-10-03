import re
import requests


class SteamName:
    def __init__(self):
        self.api_key = ""

    @staticmethod
    def extract_partner_id(trade_url: str) -> str:
        match = re.search(r"partner=(\d+)", trade_url)
        if match:
            return match.group(1)
        else:
            raise ValueError("Некорректная торговая ссылка")

    @staticmethod
    def convert_to_steamid64(partner_id: str) -> int:
        return int(partner_id) + 76561197960265728

    @staticmethod
    def get_steam_username(steamid64: int, api_key: str) -> str:
        url = f"https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/?key={api_key}&steamids={steamid64}"
        response = requests.get(url)
        data = response.json()
        if "response" in data and "players" in data["response"] and data["response"]["players"]:
            return data["response"]["players"][0]["personaname"]
        else:
            raise ValueError("Не удалось получить данные пользователя")

    def get_steam_username_from_trade_url(self, trade_url: str) -> str:
        try:
            partner_id = self.extract_partner_id(trade_url)
            steamid64 = self.convert_to_steamid64(partner_id)
            username = self.get_steam_username(steamid64, self.api_key)
            return username
        except Exception as e:
            return str(e)


#trade_url = "https://steamcommunity.com/tradeoffer/new/?partner=&token="
#api_key = ""  # Замените на ваш API ключ
#username = get_steam_username_from_trade_url(trade_url, api_key)
#print(username)
