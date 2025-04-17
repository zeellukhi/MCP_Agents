
# MCP Agents

A conversational AI assistant powered by Google Gemini and LangChain, capable of interacting with external services like Notion and Google Calendar using the Multi-Capability Platform (MCP) for tool integration. Features a simple web-based chat interface.

## Features

* **Conversational AI:** Utilizes Google's Gemini Pro model via LangChain for natural language understanding and generation.
* **Extensible Tools:** Integrates with Notion (tasks, checklists, expenses) and Google Calendar (event creation) through MCP. Easily extensible with more tools.
* **Web Interface:** Basic chat UI built with Starlette, HTML, CSS, and JavaScript.
* **Asynchronous Architecture:** Built with `asyncio`, Starlette, and `uvicorn` for efficient handling of concurrent requests.
* **Configuration Management:** Uses `.env` files for secure management of API keys and settings.
* **Centralized Logging:** Consistent logging to both console and a rotating file (`logs/app.log`).
* **Containerization Support:** Includes `Dockerfile` and `docker-compose.yml` for easy deployment with Docker.
* **Process Management:** Optional configuration for PM2 (`ecosystem.config.js`).

## Project Structure

```
MCP_Agents/
├── src/                     # Main source code
│   ├── api/                 # API server (Starlette app, agent orchestration)
│   ├── common/              # Shared utilities (config, logging)
│   ├── mcp/                 # MCP server (tool exposure via SSE)
│   ├── tools/               # Tool implementations (Notion, Google Calendar)
│   └── ui/                  # Frontend files (HTML, CSS, JS)
├── tests/                   # Unit and integration tests (Optional)
├── logs/                    # Log files (created automatically)
├── .env                     # Environment variables (Needs creation - VERY IMPORTANT)
├── .gitignore               # Files ignored by Git
├── Dockerfile               # Instructions to build the Docker image
├── docker-compose.yml       # Docker Compose configuration
├── ecosystem.config.js      # PM2 process manager configuration (Optional)
├── main.py                  # Main application entry point (starts servers)
├── pyproject.toml           # Project metadata and tool configuration
├── README.md                # This file
└── requirements.txt         # Python dependencies
```

## Prerequisites

* **Python:** Version 3.9 or higher.
* **pip:** Python package installer (usually comes with Python).
* **Git:** For cloning the repository.
* **Access to External Services:**
    * A Google Account (for Gemini API key and Google Calendar).
    * A Notion Account.
* **(Optional - for Docker)** Docker and Docker Compose.
* **(Optional - for PM2)** Node.js and npm (to install PM2).

## Setup & Configuration

Follow these steps carefully to set up the necessary external services and configure the application.

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd MCP_Agents
```

### 2. Set Up External Services

#### a) Google Cloud & Gemini

1.  **Gemini API Key:**
    * Go to [Google AI Studio](https://aistudio.google.com/).
    * Create an API key.
    * Copy this key. You will need it for the `GOOGLE_API_KEY` variable in your `.env` file.
2.  **Google Calendar API:**
    * Go to the [Google Cloud Console](https://console.cloud.google.com/).
    * Create a new project or select an existing one.
    * Navigate to "APIs & Services" > "Library".
    * Search for "Google Calendar API" and **enable** it for your project.
    * Navigate to "APIs & Services" > "Credentials".
    * Click "+ CREATE CREDENTIALS" and select "OAuth client ID".
    * If prompted, configure the OAuth consent screen (User Type: External, provide app name, user support email, developer contact info).
    * Select "Desktop app" as the Application type. Give it a name (e.g., "MCP Agents Desktop Client").
    * Click "Create".
    * A window will show your Client ID and Client Secret. Click "**DOWNLOAD JSON**".
    * Save this downloaded JSON file. You will need its **path** for the `GOOGLE_CLIENT_SECRET_FILE` variable in your `.env` file. **Do not commit this file to Git.**

#### b) Notion

1.  **Create Notion Integration:**
    * Go to [Notion's My Integrations](https://www.notion.so/my-integrations).
    * Click "+ New integration".
    * Give it a name (e.g., "MCP Agent Integration").
    * Select the associated workspace.
    * Ensure "Read content", "Update content", and "Insert content" capabilities are checked. No user information capabilities are needed unless you extend the tools.
    * Click "Submit".
    * Copy the "**Internal Integration Token**". This is your `NOTION_API_KEY` for the `.env` file.
2.  **Create Notion Databases:**
    * You need three databases in your Notion workspace:
        * **Tasks Database:** Must have properties matching `notion_tool.py` (e.g., `Name` (Title), `Due Date` (Date), `Priority` (Select), `Project` (Select/Relation - adjust code if Relation), `Status` (Status/Select)).
        * **Daily Checklist Database:** Must have properties like `Name` (Title), `Date` (Date), `Checked` (Checkbox).
        * **Expenses Database:** Must have properties like `Item` (Title), `Amount` (Number), `Date` (Date), `Category` (Select).
    * *Important:* The property names and types **must match** those used in `src/tools/notion_tool.py`. Check the code and adjust your database schemas or the code accordingly.
3.  **Connect Integration to Databases:**
    * Open each of the three databases you created in Notion.
    * Click the "..." menu in the top-right corner.
    * Click "+ Add connections" and search for the integration you created ("MCP Agent Integration"). Select it to grant access.
4.  **Get Database IDs:**
    * Open each database page in Notion.
    * Look at the URL in your browser's address bar. It will look like: `https://www.notion.so/your-workspace/DATABASE_ID?v=VIEW_ID`
    * Copy the `DATABASE_ID` part (the long string of characters between the last `/` and the `?`).
    * You need these IDs for the `NOTION_TASK_DB_ID`, `NOTION_DAILY_CHECKLIST_DB_ID`, and `NOTION_EXPENSE_DB_ID` variables in your `.env` file.

### 3. Create the `.env` File

In the root directory of the project (`MCP_Agents/`), create a file named `.env`. Paste the following content into it and **replace the placeholder values** with your actual credentials and settings obtained in the previous steps.

```dotenv
# MCP_Agents/.env
# --- Environment Configuration ---
# Fill in your actual credentials and settings below.
# NOTE: Ensure this file is listed in your .gitignore

# --- Google AI ---
# Required: Your API Key from Google AI Studio for Gemini LLM
GOOGLE_API_KEY="YOUR_GOOGLE_AI_STUDIO_API_KEY"

# --- Notion ---
# Required: Your internal integration token from Notion integrations page
NOTION_API_KEY="secret_YOUR_NOTION_INTEGRATION_TOKEN"
# Required: Database IDs (found in the URL of your Notion databases)
NOTION_TASK_DB_ID="YOUR_TASK_DATABASE_ID"
NOTION_DAILY_CHECKLIST_DB_ID="YOUR_CHECKLIST_DATABASE_ID"
NOTION_EXPENSE_DB_ID="YOUR_EXPENSE_DATABASE_ID"

# --- Google Calendar ---
# Required: Path to the downloaded client secrets JSON file from Google Cloud Console
# Example: credentials/client_secret.json (relative to the project root)
GOOGLE_CLIENT_SECRET_FILE="path/to/your/client_secret.json"
# Optional: Filename for storing the OAuth token after authorization (defaults to token.json)
GOOGLE_TOKEN_FILE="token.json"
# Optional: IANA Timezone name (e.g., America/New_York, Europe/London, Asia/Kolkata). Defaults to UTC.
CALENDAR_TIMEZONE="UTC"

# --- Application Settings ---
# Optional: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL). Defaults to INFO.
LOG_LEVEL="INFO"
# Optional: Set to "True" or "true" for more verbose Uvicorn logging (useful for debugging). Defaults to False.
DEBUG_MODE="False"

# Optional: Server host and port settings (can also be set via CLI args in main.py)
API_HOST="0.0.0.0"
API_PORT="8081"
MCP_HOST="0.0.0.0"
MCP_PORT="9091"

```

**Security:** Add `.env`, `token.json`, and your client secret JSON file path (or directory) to your `.gitignore` file to avoid committing sensitive credentials.

## Running Locally

### 1. Set Up a Virtual Environment

It's highly recommended to use a virtual environment to manage dependencies.

```bash
# Navigate to the project root directory (MCP_Agents/)
python -m venv .venv  # Create a virtual environment named .venv
source .venv/bin/activate  # On Windows use: .venv\Scriptsctivate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the Application

```bash
python main.py
```

This command will start both the API server (typically on `http://0.0.0.0:8081`) and the MCP server (typically on `http://0.0.0.0:9091`). Logs will be printed to the console and saved to the `logs/app.log` file.

### 4. First Time Google Authentication

The *first time* you try to use a Google Calendar function (e.g., "add an event to my calendar"), the application will trigger the OAuth flow:
1.  It will print a URL to your console.
2.  Copy this URL and paste it into your web browser.
3.  Log in to the Google account associated with the Calendar you want to use.
4.  Grant the application permission to access your calendar.
5.  After successful authorization, you might be redirected to a localhost page or shown an authorization code. The application running in your terminal should detect this and complete the process.
6.  A `token.json` file (or the name specified by `GOOGLE_TOKEN_FILE` in `.env`) will be created in your project root, storing the authorization token for future use.

### 5. Access the UI

Open your web browser and navigate to the API server's address, typically:

`http://localhost:8081`

You should see the chat interface.

### 6. Stopping the Application

Press `Ctrl + C` in the terminal where `python main.py` is running.

### (Optional) Running with PM2

If you have Node.js and PM2 installed (`npm install -g pm2`), you can manage the application process using the provided configuration file.

```bash
# Start the application in the background
pm2 start ecosystem.config.js

# View logs
pm2 logs mcp-agent

# Stop the application
pm2 stop mcp-agent

# Delete the application from PM2 list
pm2 delete mcp-agent
```

## Running with Docker

Using Docker simplifies deployment by packaging the application and its dependencies.

### 1. Prerequisites

* Docker installed and running.
* Docker Compose installed.
* Ensure you have created the `.env` file as described in the Setup section.

### 2. Build the Docker Image

This step builds the image based on the `Dockerfile`. It only needs to be done once or when dependencies (`requirements.txt`) or the `Dockerfile` change.

```bash
docker-compose build
```

### 3. Run the Container

This command starts the application container(s) defined in `docker-compose.yml`.

```bash
# Start in detached mode (runs in the background)
docker-compose up -d

# To view logs
docker-compose logs -f

# To view running containers managed by compose
docker-compose ps
```

The application (API and MCP servers) will start inside the container, using the settings from the `.env` file mounted into it. Ports `8081` and `9091` (or those specified in your `.env`) will be mapped from the container to your host machine.

### 4. First Time Google Authentication (Docker)

The Google OAuth flow works similarly with Docker:
1.  When you trigger a Google Calendar action via the chat UI, check the Docker container logs (`docker-compose logs -f`).
2.  You should see the authorization URL printed in the logs.
3.  Copy this URL and complete the authorization process in your browser as described in the local setup.
4.  The application inside the container should detect the successful authorization.
5.  The `token.json` file will be saved **inside the container**. Thanks to the volume mapping defined in `docker-compose.yml`, this file should also appear in your project's root directory on your host machine, persisting across container restarts.

### 5. Access the UI (Docker)

Open your web browser and navigate to the API server's address mapped to your host:

`http://localhost:8081` (or the host port configured via `API_PORT` in `.env`)

### 6. Stopping the Container

```bash
# Stop and remove the containers defined in docker-compose.yml
docker-compose down

# To stop without removing
# docker-compose stop
```

## Running Tests (Optional)

If tests are configured in the `tests/` directory and `pytest` is installed (e.g., via `pip install -r requirements.txt` or `pip install pytest pytest-asyncio`), you can run them using:

```bash
# Ensure virtual environment is active or pytest is globally available
pytest
```
Refer to `pyproject.toml` for `pytest` configuration options.

## Contributing

(Add guidelines for contributing if applicable, e.g., pull request process, coding standards.)

## License

This project is licensed under the MIT License - see the `LICENSE` file for details (assuming you add one).