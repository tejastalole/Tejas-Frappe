# Lazy import to avoid circular dependency with ai_bot.copilot

__all__ = ["process_message"]


def __getattr__(name: str):
	if name == "process_message":
		from ai_bot.skills.registry import process_message

		return process_message
	raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
