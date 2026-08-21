# Copyright (c) 2026, Tejas and contributors
# MIT License

"""HTTP client for ZKTeco Easy TimePro / BioTime-compatible API."""

from __future__ import annotations

from typing import Any

import frappe
import requests


class EasyTimeProClient:
	def __init__(self, base_url: str, username: str, password: str):
		self.base_url = (base_url or "").rstrip("/")
		self.username = username
		self.password = password
		self._token: str | None = None

	@classmethod
	def from_settings(cls) -> "EasyTimeProClient":
		settings = frappe.get_single("Easy TimePro Settings")
		password = settings.get_password("password")
		if not settings.base_url or not settings.username or not password:
			frappe.throw("Please configure Easy TimePro Settings (URL, username, password).")
		return cls(settings.base_url, settings.username, password)

	def get_token(self, force: bool = False) -> str:
		if self._token and not force:
			return self._token

		url = f"{self.base_url}/api-token-auth/"
		response = requests.post(
			url,
			json={"username": self.username, "password": self.password},
			headers={"Content-Type": "application/json"},
			timeout=30,
		)
		if response.status_code >= 400:
			frappe.throw(f"Easy TimePro login failed ({response.status_code}): {response.text[:300]}")

		payload = response.json()
		token = payload.get("token")
		if not token:
			frappe.throw(f"Easy TimePro token missing in response: {payload}")
		self._token = token
		return token

	def _headers(self) -> dict[str, str]:
		return {
			"Authorization": f"Token {self.get_token()}",
			"Content-Type": "application/json",
		}

	def get(self, path: str, params: dict | None = None) -> dict[str, Any]:
		url = f"{self.base_url}{path}"
		response = requests.get(url, headers=self._headers(), params=params or {}, timeout=60)
		if response.status_code == 401:
			self.get_token(force=True)
			response = requests.get(url, headers=self._headers(), params=params or {}, timeout=60)
		if response.status_code >= 400:
			frappe.throw(f"Easy TimePro API error ({response.status_code}): {response.text[:400]}")
		return response.json()

	def get_transaction_count(self) -> int:
		payload = self.get("/iclock/api/transactions/", {"page": 1, "page_size": 1})
		return int(payload.get("count") or 0)

	def iter_transactions(
		self,
		*,
		start_time: str | None = None,
		end_time: str | None = None,
		page_size: int = 100,
		min_id: int | None = None,
	):
		"""
		Yield transactions.

		When min_id is set, fetch newest-first and stop once we reach already-synced ids
		so new punches appear within one page instead of walking the full history.
		"""
		page = 1
		newest_first = bool(min_id)

		while True:
			params: dict[str, Any] = {"page": page, "page_size": page_size}
			if start_time:
				params["start_time"] = start_time
			if end_time:
				params["end_time"] = end_time
			if newest_first:
				params["ordering"] = "-id"

			payload = self.get("/iclock/api/transactions/", params)
			rows = payload.get("data") or []
			if not rows:
				break

			stop = False
			batch = []
			for row in rows:
				tx_id = int(row.get("id") or 0)
				if min_id and tx_id <= min_id:
					if newest_first:
						stop = True
						break
					continue
				batch.append(row)

			# newest-first: reverse so callers process in chronological order
			if newest_first:
				batch.reverse()

			for row in batch:
				yield row

			if stop or not payload.get("next"):
				break
			page += 1
