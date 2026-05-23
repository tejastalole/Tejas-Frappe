__all__ = ["process_copilot_query"]


def __getattr__(name: str):
	if name == "process_copilot_query":
		from ai_bot.copilot.engine import process_copilot_query

		return process_copilot_query
	raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
