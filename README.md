---
title: TEXT-2-SQL Chatbot
emoji: 🧠
colorFrom: indigo
colorTo: blue
sdk: docker
sdk_version: "4.0.0"
app_file: app.py
pinned: false
---

# Pharma Data QA — Text-to-SQL Chatbot

## About
This application is a **Text-to-SQL Chatbot** designed to answer natural language questions about pharmaceutical sales and prescription data. It leverages a Large Language Model (LLM) to translate user queries into SQL, executes them against a local SQLite database (`pharma_data.db`), and presents the results in an interactive interface.

Key features:
- **Natural Language Querying**: Ask questions like "Which territory has the highest prescription volume?" without knowing SQL.
- **Transparent Logic**: View the generated SQL, the raw result, and a natural language explanation of the answer.
- **Interactive UI**: Built with Gradio for a user-friendly experience.

## Setup

This project uses `uv` for fast Python package management.

### Prerequisites
- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) installed

### Installation

1.  **Install uv** (if not already installed):
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

2.  **Clone the repository** Navigate to the project directory.

3.  **Sync dependencies**:
    This command will create a virtual environment and install all dependencies defined in `pyproject.toml`.
    ```bash
    uv sync
    ```

4. **Set up environment variables**:
    ```bash
    export OPENAI_API_KEY="your_openai_api_key_here"
    ```

### Running the Application

To run the Gradio application:

```bash
uv run app.py
```

The application will launch in your browser (typically at `http://127.0.0.1:7860`).


