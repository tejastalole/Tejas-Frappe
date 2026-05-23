### AI Bot — ERP Copilot

Intelligent AI-powered assistant for Frappe / ERPNext: natural language queries, workflows, CRM, HR, inventory, reports, resume parsing, and developer script generation.

**Configure:** Setup → **AI Bot Settings** (optional OpenAI key for LLM intent parsing).

**Examples:** `Show pending purchase orders` · `Pending approvals दिखाओ` · `Approve PO-00012` · `Create lead Rahul from Pune` · `Low stock items`

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app ai_bot
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/ai_bot
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### License

mit
