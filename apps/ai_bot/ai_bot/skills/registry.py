# Copyright (c) 2026, Tejas and contributors
# MIT License

from ai_bot.copilot.engine import process_copilot_query
from ai_bot.skills.base import BotContext, BotResponse
from ai_bot.skills.count_skill import CountSkill
from ai_bot.skills.aggregate_skill import AggregateSkill
from ai_bot.skills.follow_up_skill import FollowUpSkill
from ai_bot.skills.help_skill import HelpSkill
from ai_bot.skills.create_sales_order_skill import CreateSalesOrderSkill
from ai_bot.skills.discover_skill import DiscoverSkill
from ai_bot.skills.list_records_skill import ListRecordsSkill
from ai_bot.skills.open_record_skill import OpenRecordSkill

# Domain skills are routed inside copilot/engine.py (CRM, HR, workflow, etc.)

SKILLS = [
	FollowUpSkill(),
	CreateSalesOrderSkill(),
	OpenRecordSkill(),
	DiscoverSkill(),
	ListRecordsSkill(),
	AggregateSkill(),
	CountSkill(),
	HelpSkill(),
]


def process_message(message: str, context: dict | None = None) -> BotResponse:
	context = context or {}
	copilot = process_copilot_query(message, context)
	if copilot.intent.get("action") != "clarification":
		return copilot

	ctx = BotContext(
		doctype=context.get("doctype"),
		filters=context.get("filters") or {},
		message=message.lower().strip(),
		raw_message=message.strip(),
	)

	for skill in SKILLS:
		if skill.match(ctx):
			result = skill.run(ctx)
			if result:
				if copilot.intent:
					result.intent = copilot.intent
				return result

	fallback = HelpSkill().run(ctx)
	if copilot.intent:
		fallback.intent = copilot.intent
	return fallback
