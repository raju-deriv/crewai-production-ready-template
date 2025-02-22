# CrewAI Production Ready Template

A production-ready template for building multi-agent systems with [CrewAI](https://github.com/joaomdmoura/crewAI), integrated with Slack using `slack-bolt`. This project provides a scalable, modular foundation for developing AI-driven workflows with multiple agents and tools, designed for real-world deployment.

## Overview

This template showcases a Slack bot powered by CrewAI, featuring a research and writing crew as an example. It’s built with best practices to support:
- **Multi-Agent Development**: Easily add new agents and tools via modular design.
- **Production Readiness**: Robust error handling, structured logging, and configuration management.
- **Scalability**: Abstract crew base class and dependency injection for flexibility.
- **Rich Text Responses**: Formatted Slack messages using `mrkdwn`.

## Features

- Multi-agent system with CrewAI (v0.102.0)
- Slack integration via `slack-bolt` (v1.22.0)
- Agents powered by OpenAI (v1.63.2) and Anthropic (v0.34.1) LLMs
- Configuration via `.env` with `python-dotenv` (v1.0.1)
- Structured JSON logging with `structlog` (v24.4.0)
- Dependency management with `pyproject.toml`
- Comprehensive unit tests using `pytest` (v8.3.2) and `pytest-asyncio` (v0.23.8)
- Python 3.12+ compatibility with modern type hints

## Project Structure
crewai_slack_bot/
├── src/
│   ├── config/          # Configuration loading
│   ├── agents/          # Agent definitions
│   ├── tasks/           # Task definitions
│   ├── crew/            # Crew implementations
│   ├── slack/           # Slack app and message handling
│   ├── utils/           # Logging and formatting utilities
├── tests/               # Unit tests
├── .env                 # Environment variables
├── main.py             # Entry point
├── pyproject.toml      # Dependencies and metadata
├── .gitignore          # Git ignore rules
└── README.md           # Project documentation



## Setup

### Prerequisites
- Python 3.12+
- Slack app with Bot Token (`xoxb-...`) and App Token (`xapp-...`)
- OpenAI and Anthropic API keys

### Installation
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/raju-deriv/crewai-production-ready-template
   cd crewai-production-ready-template