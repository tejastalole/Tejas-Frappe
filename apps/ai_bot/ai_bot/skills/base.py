# Copyright (c) 2026, Tejas and contributors
# MIT License

from dataclasses import dataclass, field


@dataclass
class BotContext:
	"""Conversation context for multi-turn queries."""

	doctype: str | None = None
	filters: dict = field(default_factory=dict)
	message: str = ""
	raw_message: str = ""


@dataclass
class BotResponse:
	reply: str
	actions: list[dict] = field(default_factory=list)
	context: dict = field(default_factory=dict)
	intent: dict = field(default_factory=dict)

	def to_dict(self) -> dict:
		from ai_bot.utils.serialize import json_safe

		out = {
			"reply": self.reply,
			"actions": json_safe(self.actions),
			"context": json_safe(self.context),
		}
		if self.intent:
			out["intent"] = json_safe(self.intent)
		return out
