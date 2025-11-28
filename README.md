# Bookkeeper

AI-powered financial data cleanup for better reporting.

## Overview

Bookkeeper helps you maintain clean, well-categorized financial data in Quicken Classic Deluxe. It uses AI to intelligently categorize transactions by analyzing all available transaction data, not just the payee field.

## Features

- **Direct SQLite access**: Works directly with Quicken's database (no export/import needed)
- **AI-powered classification**: Uses LLM + ML to suggest better categories
- **Automatic backups**: Creates timestamped backups before any changes
- **Dry-run mode**: Preview all suggested changes before applying
- **Date range filtering**: Process specific time periods
- **Learning system**: Improves from your corrections over time

## Installation

### Using pipx (recommended for CLI tools)
```bash
pipx install -e .
```

### Using pip
```bash
pip install -e .
```

## Setup

You'll need an Anthropic API key for AI-powered classification:

1. Sign up at https://console.anthropic.com
2. Create an API key
3. Set it as an environment variable:
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-..."
   ```

## Usage

```bash
# Dry run - preview suggested changes
bookkeeper /path/to/file.quicken --start-date 2024-01-01 --dry-run

# Apply changes (creates backup automatically)
bookkeeper /path/to/file.quicken --start-date 2024-01-01

# Specify date range
bookkeeper /path/to/file.quicken --start-date 2024-01-01 --end-date 2024-12-31

# Or pass API key directly
bookkeeper /path/to/file.quicken --api-key "sk-ant-..." --dry-run
```

## How It Works

1. **Backup**: Automatically creates a timestamped backup of your Quicken file
2. **Read**: Extracts transactions from the SQLite database inside the .quicken package
3. **Classify**: Uses AI to suggest better categories based on full transaction context
4. **Apply**: Updates categories directly in the database (or shows preview in dry-run mode)
5. **Learn**: Tracks your corrections to improve future classifications

## Architecture

- Direct SQLite database access (no FITID/duplicate concerns)
- Ensemble classification: baseline rules + ML + LLM
- Built-in eval framework for continuous improvement
- Clean separation: reader, classifier, writer, eval components
