# Copyright (c) 2026, Tejas and contributors
# MIT License

import re

import frappe
from frappe import _

from ai_bot.services.resume_parser import parse_resume_text
from ai_bot.skills.base import BotContext, BotResponse


class ResumeParserSkill:
	def match(self, ctx: BotContext) -> bool:
		return bool(
			re.search(r"\b(resume|cv|parse resume|job applicant)\b", ctx.message, re.I)
		)

	def run(self, ctx: BotContext) -> BotResponse:
		# Resume text may be pasted after "parse resume:"
		text = ctx.raw_message
		if ":" in text:
			text = text.split(":", 1)[1].strip()
		elif len(text) < 80:
			return BotResponse(
				reply=_(
					"Paste resume text after <i>parse resume:</i> or upload via Job Applicant form. "
					"I will extract name, email, phone, skills, and gender."
				),
				actions=[],
			)

		data = parse_resume_text(text)
		if not data:
			return BotResponse(reply=_("Could not extract fields from resume."), actions=[])

		if frappe.db.exists("DocType", "Job Applicant") and frappe.has_permission(
			"Job Applicant", "create"
		):
			doc = frappe.get_doc({"doctype": "Job Applicant", **data})
			doc.insert(ignore_permissions=False)
			return BotResponse(
				reply=_(
					"<p>Job Applicant <b>{0}</b> created from resume.</p>"
					"<ul>{1}</ul>"
				).format(
					doc.name,
					"".join(f"<li>{k}: {v}</li>" for k, v in data.items()),
				),
				actions=[
					{
						"type": "open",
						"doctype": "Job Applicant",
						"name": doc.name,
						"label": doc.name,
					}
				],
			)

		lines = "".join(f"<li><b>{k}</b>: {v}</li>" for k, v in data.items())
		return BotResponse(
			reply=_("<p>Extracted resume fields:</p><ul>{0}</ul>").format(lines),
			actions=[],
		)
