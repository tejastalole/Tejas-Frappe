# Copyright (c) 2026, Tejas and contributors
# MIT License

from datetime import date, datetime


def json_safe(value):
	if isinstance(value, (date, datetime)):
		return value.strftime("%Y-%m-%d")
	if isinstance(value, dict):
		return {k: json_safe(v) for k, v in value.items()}
	if isinstance(value, (list, tuple)):
		return [json_safe(v) for v in value]
	return value


def json_safe_filters(filters: dict) -> dict:
	return json_safe(filters or {})
