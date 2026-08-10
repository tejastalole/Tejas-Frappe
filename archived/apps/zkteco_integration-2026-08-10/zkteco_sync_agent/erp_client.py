# Copyright (c) 2026, Exacuer
"""HTTPS client for ERPNext Cloud APIs (API Key auth). Never logs secrets."""

from __future__ import annotations

from typing import Any

import requests


class ErpClient:
	def __init__(self, erp_url: str, api_key: str, api_secret: str, timeout: int = 30):
		self.base = erp_url.rstrip("/")
		self.timeout = timeout
		self.session = requests.Session()
		self.session.headers.update(
			{
				"Authorization": f"token {api_key}:{api_secret}",
				"Content-Type": "application/json",
				"Accept": "application/json",
			}
		)

	def _post(self, method: str, data: dict[str, Any]) -> dict[str, Any]:
		url = f"{self.base}/api/method/{method}"
		resp = self.session.post(url, json=data, timeout=self.timeout)
		resp.raise_for_status()
		payload = resp.json()
		return payload.get("message", payload)

	def heartbeat(self, device_id: str, status: str = "Online", last_error: str | None = None, **kwargs) -> dict:
		body = {"device_id": device_id, "status": status, "last_error": last_error or ""}
		body.update(kwargs)
		return self._post("zkteco_integration.api.device_heartbeat", body)

	def sync_attendance(self, device_id: str, records: list[dict[str, Any]]) -> dict:
		return self._post(
			"zkteco_integration.api.sync_attendance",
			{"device_id": device_id, "records": records},
		)

	def create_checkin(self, **kwargs) -> dict:
		return self._post("zkteco_integration.api.create_employee_checkin", kwargs)
