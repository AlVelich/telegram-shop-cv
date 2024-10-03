import aiohttp
from aiogram.types import InputFile
from aiogram import Bot
from config import YOUR_SECRET_KEY
import requests
import uuid
import logging
from io import BytesIO

logger = logging.getLogger(__name__)

def get_balance():
    url = f"https://market.dota2.net/api/GetMoney/?key={YOUR_SECRET_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data["money"] / 100  # Возвращаем баланс в рублях
    except requests.RequestException as e:
        logger.error(f"Error fetching balance: {e}")
        return None

def get_price_list(market_hash_name, domain):
    search_url_template = 'https://{}/api/v2/search-item-by-hash-name-specific?key={}&hash_name={}'
    url = search_url_template.format(domain, YOUR_SECRET_KEY, market_hash_name)
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if data.get('success') and 'data' in data:
            return True, data['data']
        else:
            return False, {'error': 'No data in response'}
    except requests.RequestException as e:
        return False, {'error': str(e)}

def make_request(item_id, price, domain, partner='', token=''):
    buy_for_url_template = 'https://{}/api/v2/buy-for?key={}&id={}&price={}&partner={}&token={}&custom_id={}'
    custom_id = str(uuid.uuid4())
    url = buy_for_url_template.format(domain, YOUR_SECRET_KEY, item_id, int(price * 100), partner, token, custom_id)
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if data.get('success'):
            return True, data, custom_id
        else:
            return False, data, custom_id
    except requests.RequestException as e:
        return False, {'error': str(e)}, custom_id

def check_status(custom_id, domain):
    status_url_template = 'https://{}/api/v2/get-buy-info-by-custom-id?key={}&custom_id={}'
    url = status_url_template.format(domain, YOUR_SECRET_KEY, custom_id)
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if data.get('success'):
            return True, data['data']
        else:
            return False, {'error': 'No data in response'}
    except requests.RequestException as e:
        return False, {'error': str(e)}

async def send_image(url: str, chat_id: int, bot: Bot):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                image_data = await response.read()
                image = InputFile(BytesIO(image_data), filename=f"image.png")
                await bot.send_photo(chat_id, photo=image)
            else:
                raise Exception(f"Failed to fetch image. Status code: {response.status}")
#https://steamcommunity.com/market/listings/
#https://api.steamapis.com/image/item/440/Mann%20Co.%20Supply%20Crate%20Key