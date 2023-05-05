from typing import Optional
import aiohttp

from clients.dcs import GetUpdatesResponse, SendMessageResponse, ReplyKeyboardMarkup


class PillsClient:
    def get_url(self, method: str):
        return f"http://localhost:8080/pills/{method}"

    async def pills_count(self, login: str) -> dict:
        url = self.get_url(f"pills_count?login={login}")
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                return await resp.json()
    
    async def get_me(self, login: str) -> dict:
        url = self.get_url(f"get_me?login={login}")
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                return await resp.json()
    
    async def get_user_state(self, login: str) -> dict:
        url = self.get_url(f"get_user_state?login={login}")
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                return await resp.json()
    
    async def user_state(self, login: str, state: str) -> dict:
        url = self.get_url(f"user_state")
        payload = {
            "login": login,
            "state": state
        }
        async with aiohttp.ClientSession() as session:
            async with session.put(url, json=payload) as resp:
                return await resp.json()
    
    async def add_pills(self, login: str, pill: str, count: int) -> dict:
        url = self.get_url(f"add_pills")
        payload = {
            "login": login,
            "name": pill,
            "count": count
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                return await resp.json()
    
    async def pills_safe_count(self, login: str, pill: str, count: int) -> dict:
        url = self.get_url(f"pills_safe_count?login={login}&name={pill}&add_pills={count}")
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                return await resp.json()
    
    async def set_med(self, login: str, pill: str, count: int, pills_use: int) -> dict:
        url = self.get_url(f"set_med")
        payload = {
            "login": login,
            "name": pill,
            "count": int(count),
            "pills_use": int(pills_use)
        }
        async with aiohttp.ClientSession() as session:
            async with session.put(url, json=payload) as resp:
                return await resp.json()
    
    async def delete_med(self, login: str, pill: str) -> dict:
        url = self.get_url(f"delete_med")
        payload = {
            "login": login,
            "name": pill
        }
        async with aiohttp.ClientSession() as session:
            async with session.delete(url, json=payload) as resp:
                return await resp.json()