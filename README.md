# Episodic: Your Personal Digital Memory CLI

**Episodic** is a command-line tool for building, maintaining, and searching a personal, persistent "digital episodic memory" from your Gemini CLI interactions. It transforms scattered `logs.json` files into a structured, queryable, and permanent local database.

## The Problem

Your interactions with the Gemini CLI are a valuable log of your thoughts, queries, and development process. However, this data is spread across numerous `logs.json` files in hashed directories, making it difficult to revisit or learn from. Searching this history is impossible, and processing all the files every time you want to analyze them is inefficient.

## The Solution

Episodic provides a robust, local-first solution to this problem. It creates a single, permanent SQLite database (`memory.db`) that acts as your digital memory.

### Features

- **Persistent Storage:** All your user interactions are stored in a single, portable SQLite database file.
- **Incremental Building:** The tool is smart enough to only process new or updated log files, making updates fast and efficient.
- **Structured Data:** Raw logs are parsed into a clean, relational schema, ready for complex queries.
- **Local First:** Your data stays on your machine, ensuring privacy and availability.
- **Foundation for AI:** Creates the perfect foundation for future semantic search and AI-powered memory exploration by providing a clean, consolidated data source.

## Architecture

- **Backend:** A single Python script (`episodic.py`) containing all the logic.
- **Database:** A SQLite database file (`memory.db`) created in the project root.
- **Dependencies:** Standard Python libraries (no external packages required for the initial version).

## Usage

The tool will be operated via a simple command-line interface.

### 1. Build Your Memory

This command scans a directory for `logs.json` files and builds or updates your memory database. It is safe to run this command multiple times; it will only add new entries.

```bash
# To be implemented
python episodic.py build <path_to_logs_directory>
```
**Example:**
```bash
python episodic.py build .
```

### 2. Search Your Memory (Future)

This command will allow you to perform powerful searches over your entire interaction history.

```bash
# To be implemented
python episodic.py search "your query here"
```

## Roadmap

- [X] **Project Scoping & README:** Define the vision and architecture.
- [ ] **Initial Script (`episodic.py`):** Create the core Python script with CLI argument parsing.
- [ ] **SQLite Backend:** Implement the database creation and schema.
- [ ] **Implement `build` command:** Create the logic to scan, parse, and incrementally add log entries to the database.
- [ ] **Implement `search` command:** Add basic keyword search functionality.
- [ ] **Embeddings:** Generate and store vector embeddings for each memory entry.
- [ ] **Semantic Search:** Implement a true semantic search using vector similarity.
