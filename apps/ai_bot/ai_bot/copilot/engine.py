# Copyright (c) 2026, Tejas and contributors
# MIT License

"""Copilot pipeline: parse intent → execute → chat response."""

import re

from ai_bot.copilot.compound_parser import parse_intents
from ai_bot.copilot.executor import execute_intent, execute_intents
from ai_bot.copilot.intent_parser import parse_intent
from ai_bot.copilot.query_planner import plan_query
from ai_bot.skills.base import BotContext, BotResponse


def _try_create_sales_order(raw: str, context: dict) -> BotResponse | None:
	from ai_bot.skills.create_sales_order_skill import CreateSalesOrderSkill

	ctx = BotContext(
		doctype=context.get("doctype"),
		filters=context.get("filters") or {},
		message=raw.lower(),
		raw_message=raw,
	)
	skill = CreateSalesOrderSkill()
	if skill.match(ctx):
		return skill.run(ctx)
	return None


def _try_domain_skills(raw: str, context: dict) -> BotResponse | None:
	"""Route CRM, HR, inventory, approvals, developer, resume, reports."""
	from ai_bot.skills.base import BotContext
	from ai_bot.skills.crm_skill import CrmSkill
	from ai_bot.skills.developer_skill import DeveloperSkill
	from ai_bot.skills.hr_skill import HrSkill
	from ai_bot.skills.inventory_skill import InventorySkill
	from ai_bot.skills.pending_approvals_skill import PendingApprovalsSkill
	from ai_bot.skills.report_skill import ReportSkill
	from ai_bot.skills.resume_parser_skill import ResumeParserSkill
	from ai_bot.skills.workflow_skill import WorkflowSkill

	ctx = BotContext(
		doctype=context.get("doctype"),
		filters=context.get("filters") or {},
		message=raw.lower(),
		raw_message=raw,
	)
	for skill in (
		WorkflowSkill(),
		PendingApprovalsSkill(),
		ResumeParserSkill(),
		DeveloperSkill(),
		ReportSkill(),
		CrmSkill(),
		HrSkill(),
		InventorySkill(),
	):
		if skill.match(ctx):
			return skill.run(ctx)
	return None


def process_copilot_query(message: str, context: dict | None = None) -> BotResponse:
	context = context or {}
	raw = message.strip()

	domain = _try_domain_skills(raw, context)
	if domain:
		return domain

	# Create Sales Order before site search misreads "item X qty Y" as lookup
	create_so = _try_create_sales_order(raw, context)
	if create_so:
		return create_so

	# Discovery / help bypass copilot JSON when clearly meta questions
	if _is_discovery_query(raw):
		from ai_bot.skills.discover_skill import DiscoverSkill

		ctx = BotContext(message=raw.lower(), raw_message=raw, **context)
		skill = DiscoverSkill()
		if skill.match(ctx):
			return skill.run(ctx)

	# Site-wide read: search, overview, record detail
	planned = plan_query(raw, context)
	if planned:
		result = execute_intent(planned, raw)
		planned["status"] = result.get("status", planned.get("status"))
		if result.get("message"):
			planned["message"] = result["message"]
		return BotResponse(
			reply=result.get("message", ""),
			actions=result.get("actions") or [],
			context={
				"doctype": planned.get("doctype") or context.get("doctype"),
				"filters": planned.get("filters") or {},
				"last_intent": planned,
			},
			intent=planned,
		)

	# Optional LLM intent (falls back to rule-based parser)
	from ai_bot.copilot.llm import parse_intent_with_llm

	llm_intent = parse_intent_with_llm(raw, context)
	if llm_intent and llm_intent.get("action") not in (None, "clarification"):
		result = execute_intent(llm_intent, raw)
		llm_intent["status"] = result.get("status", llm_intent.get("status"))
		return BotResponse(
			reply=result.get("message", ""),
			actions=result.get("actions") or [],
			context={
				"doctype": llm_intent.get("doctype") or context.get("doctype"),
				"filters": llm_intent.get("filters") or {},
				"last_intent": llm_intent,
			},
			intent=llm_intent,
		)

	intents = parse_intents(raw, context)

	# Merge ERP document IDs from raw message
	name_match = re.search(r"\b([A-Z]{2,}[-][A-Z0-9-]+)\b", raw)
	if name_match:
		for intent in intents:
			if intent.get("doctype"):
				intent.setdefault("filters", {})["name"] = name_match.group(1)

	if len(intents) == 1 and intents[0].get("action") == "clarification":
		return BotResponse(
			reply=intents[0].get("message", ""),
			context=context,
			intent=intents[0],
		)

	if len(intents) > 1:
		intent = {
			"action": "compound",
			"intents": intents,
			"status": "success",
		}
		result = execute_intents(intents, raw)
	else:
		intent = intents[0]
		result = execute_intent(intent, raw)
		intent["status"] = result.get("status", intent.get("status"))
		if result.get("message"):
			intent["message"] = result["message"]

	new_context = {
		"doctype": intent.get("doctype") or (intents[-1].get("doctype") if intents else None),
		"filters": (intents[-1].get("filters") if intents else {}) or {},
		"last_intent": intent,
	}

	return BotResponse(
		reply=result.get("message", ""),
		actions=result.get("actions") or [],
		context=new_context,
		intent=intent,
	)


def _is_discovery_query(message: str) -> bool:
	lower = message.lower()
	return bool(
		re.search(
			r"\b(what is inside|modules? in frappe|list modules?|doctypes? in|discover)\b",
			lower,
		)
	)
