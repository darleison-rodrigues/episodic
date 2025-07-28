# Documentation for `episodic.py`

This document provides a detailed explanation of the `episodic.py` script, its functions, and its architecture.

## Overview

The `episodic.py` script is a command-line tool for building and maintaining a personal digital memory from Gemini CLI log files. It uses a SQLite database to store the data, ensuring persistence and efficient querying.

## Architecture

- **Database:** A single SQLite file named `memory.db` is used to store all the data.
- **CLI:** The `argparse` module is used to create a simple command-line interface.
- **Modularity:** The script is divided into several functions, each with a specific responsibility.

## Functions

### `initialize_database()`

- **Purpose:** Creates the `memory.db` file if it doesn't exist and sets up the `episodes` table.
- **Schema:** The `episodes` table has the following columns:
    - `id`: An auto-incrementing primary key.
    - `timestamp`: The timestamp of the user's message.
    - `session_id`: The session ID of the conversation.
    - `message`: The content of the user's message.
    - `message_id`: The ID of the message within its session.
    - `source_file`: The path to the `logs.json` file from which the data was extracted. The combination of `source_file` and `message_id` forms a unique constraint to prevent duplicate entries.

    - `embedding`: A BLOB field to store the vector embedding of the message.

### `get_processed_files()`

- **Purpose:** Retrieves a set of all `source_file` paths that have already been processed and stored in the database.
- **Return Value:** A `set` of strings, where each string is a file path. This is used to efficiently check which files are new and need to be processed.

### `build_memory(logs_directory)`

- **Purpose:** This is the core function for building and updating the memory.
- **Process:**
    1. It calls `initialize_database()` to ensure the database is ready.
    2. It calls `get_processed_files()` to get the set of already processed files.
    3. It scans the specified `logs_directory` for all `logs.json` files.
    4. It compares the list of found files with the set of processed files to identify new files.
    5. It iterates through the new files, parses the JSON, and extracts user messages.
    6. It inserts the new messages into the `episodes` table in the database.

### `search_memory(query)`

- **Purpose:** Searches the `episodes` table for messages matching the given query using semantic similarity.
- **Functionality:**
    - Loads the SentenceTransformer model.
    - Generates an embedding for the input `query`.
    - Retrieves all stored message embeddings from the database.
    - Calculates the cosine similarity between the query embedding and each stored embedding.
    - Returns the top 5 most similar entries, ordered by similarity.

### `embed_memory()`

- **Purpose:** Generates and stores vector embeddings for messages that do not yet have them.
- **Functionality:**
    - Loads a SentenceTransformer model (`all-MiniLM-L6-v2`).
    - Queries the database for messages with `NULL` embeddings.
    - Encodes these messages into vector embeddings.
    - Updates the database, storing the embeddings as BLOBs.

### `build_lexicon()`

- **Purpose:** Builds a lexicon (word frequencies) from all messages in the database.
- **Functionality:**
    - Iterates through all messages in the `episodes` table.
    - Tokenizes messages and counts word frequencies.
    - Stores words and their frequencies in the `lexicon` table.

### `search_lexicon(word)`

- **Purpose:** Searches the lexicon for a given word and returns its frequency.
- **Functionality:** Returns the frequency of the word if found, otherwise indicates it's not in the lexicon.

### `main()`

- **Purpose:** The main entry point of the script.
- **Functionality:**
    - It uses `argparse` to define the command-line arguments.
    - It currently supports three top-level commands: `build`, `search`, and `embed`.
    - It also supports a `lexicon` subcommand with `build` and `search` sub-commands.
    - The `build` command takes one argument: `directory`, which is the path to the directory containing the log files.
    - The `search` command takes one argument: `query`, which is the keyword or phrase to search for.
    - The `embed` command takes no arguments.
    - The `lexicon build` command takes no arguments.
    - The `lexicon search` command takes one argument: `word`, the word to search for.
    - It calls the appropriate function based on the command-line arguments.

## How to Run

To build the memory, run the following command from your terminal:

```bash
python episodic.py build <path_to_your_logs>
```

For example:

```bash
python episodic.py build .
```

To generate embeddings for your memory, run:

```bash
python episodic.py embed
```

To search your memory (semantic search), run:

```bash
python episodic.py search "your query here"
```

For example:

```bash
python episodic.py search "knowledge graph"
```

To build the lexicon, run:

```bash
python episodic.py lexicon build
```

To search the lexicon for a word, run:

```bash
python episodic.py lexicon search <word>
```

For example:

```bash
python episodic.py lexicon search "python"
```

## Roadmap

- [X] **Project Scoping & README:** Define the vision and architecture.
- [X] **Initial Script (`episodic.py`):** Create the core Python script with CLI argument parsing.
- [X] **SQLite Backend:** Implement the database creation and schema.
- [X] **Implement `build` command:** Create the logic to scan, parse, and incrementally add log entries to the database.
- [X] **Implement `search` command:** Add basic keyword search functionality.
- [X] **Embeddings:** Generate and store vector embeddings for each memory entry.
- [X] **Semantic Search:** Implement a true semantic search using vector similarity.
- [X] **Lexicon Builder:** Implement a lexicon builder with word frequency counting.
- [ ] **Knowledge Graph Builder:** Implement a knowledge graph builder.
- [ ] **Agent Interface:** Create an agent interface.
- [ ] **WebAssembly (WASM) Integration:** Explore WASM for client-side performance.
- [ ] **Websocket Communication:** Implement websocket communication for teams.