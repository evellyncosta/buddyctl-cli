# BuddyCtl

CLI tool for managing StackSpot AI assistants (buddies).

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd buddyctl
```

2. Create and activate a virtual environment:

**Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

3. Install the project with dependencies:
```bash
pip install -e .
```

This will install the project in editable mode using the configuration from `pyproject.toml`, including all dependencies:
- typer[all] - CLI framework
- httpx - HTTP client
- prompt_toolkit - Interactive prompts

## Configuration

1. Copy the environment variables template:
```bash
cp .env.example .env
```

2. Edit `.env` file with your StackSpot credentials:
```env
STACKSPOT_CLIENT_ID=your_client_id_here
STACKSPOT_CLIENT_SECRET=your_client_secret_here
STACKSPOT_REALM=your_realm_here
```

You can generate these credentials in your StackSpot account.

## Running the Project

After installation and configuration, run the CLI tool:

```bash
buddyctl
```

Or directly with Python:
```bash
python -m buddyctl.main
```

## Development

The project uses `pyproject.toml` for dependency management and package configuration. The editable installation (`pip install -e .`) allows you to make changes to the code and test them immediately without reinstalling.

To deactivate the virtual environment when you're done:
```bash
deactivate
```