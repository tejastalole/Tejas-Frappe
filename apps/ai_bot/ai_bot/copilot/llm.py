# Copyright (c) 2026, Tejas and contributors
# MIT License

"""Optional LLM intent parsing (OpenAI-compatible). Falls back to rule-based parser."""

import json
import re

import frappe
from frappe import _

from ai_bot.copilot.persona import get_system_prompt


def get_api_key() -> str | None:
	try:
		settings = frappe.get_single("AI Bot Settings")
		if not getattr(settings, "enable_llm", 0):
			return None
		key = settings.get_password("openai_api_key") if settings.openai_api_key else None
		return key or frappe.conf.get("ai_bot_openai_api_key")
	except Exception:
		return frappe.conf.get("ai_bot_openai_api_key")


def parse_intent_with_llm(message: str, context: dict | None = None) -> dict | None:
	"""
	Return structured intent JSON from LLM, or None to use rule-based parser.
	Requires openai package and API key in AI Bot Settings.
	"""
	api_key = get_api_key()
	if not api_key:
		return None

	try:
		import openai
	except ImportError:
		frappe.log_error("Install openai package for LLM: pip install openai")
		return None

	context = context or {}
	model = "gpt-4o-mini"
	try:
		settings = frappe.get_single("AI Bot Settings")
		if settings.llm_model:
			model = settings.llm_model
	except Exception:
		pass

	system = get_system_prompt() + (
		"\n\nRespond with ONLY valid JSON:\n"
		'{"action":"read|create|update|delete|approve|cancel|reject|report|clarification",'
		'"doctype":"DocType name or empty",'
		'"filters":{},'
		'"data":{},'
		'"message":"short user-facing reply if clarification"}'
	)

	user = message
	if context.get("doctype"):
		user += f"\nContext doctype: {context['doctype']}"
	if context.get("filters"):
		user += f"\nContext filters: {json.dumps(context['filters'])}"

	try:
		client = openai.OpenAI(api_key=api_key)
		resp = client.chat.completions.create(
			model=model,
			messages=[
				{"role": "system", "content": system},
				{"role": "user", "content": user},
			],
			temperature=0.1,
			max_tokens=500,
		)
		text = (resp.choices[0].message.content or "").strip()
		match = re.search(r"\{[\s\S]*\}", text)
		if not match:
			return None
		intent = json.loads(match.group(0))
		if isinstance(intent, dict) and intent.get("action"):
			return intent
	except Exception:
		frappe.log_error(title="AI Bot LLM")
	return None
