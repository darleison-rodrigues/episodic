import argparse
import json
import sqlite3
from pathlib import Path
import sys
from sentence_transformers import SentenceTransformer
import numpy as np
import spacy

# Load spaCy model
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("Downloading spaCy model 'en_core_web_sm'...", file=sys.stderr)
    from spacy.cli import download
    download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

model = None

def load_model():
    global model
    if model is None:
        print("Loading SentenceTransformer model... This may take a moment.")
        model = SentenceTransformer('all-MiniLM-L6-v2')
        print("Model loaded.")

DB_FILE = "memory.db"

def initialize_database():
    """Initializes the SQLite database and creates the episodes table if it doesn't exist."""
    try:
        con = sqlite3.connect(DB_FILE)
        cur = con.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                session_id TEXT NOT NULL,
                message_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                source_file TEXT NOT NULL,
                embedding BLOB,
                UNIQUE(source_file, message_id)
            )
        """)
        # Add embedding column if it doesn't exist
        cur.execute("PRAGMA table_info(episodes)")
        columns = [col[1] for col in cur.fetchall()]
        if 'embedding' not in columns:
            cur.execute("ALTER TABLE episodes ADD COLUMN embedding BLOB")
        con.commit()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS lexicon (
                word TEXT PRIMARY KEY,
                frequency INTEGER NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                label TEXT NOT NULL,
                episode_id INTEGER NOT NULL,
                FOREIGN KEY (episode_id) REFERENCES episodes(id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_text TEXT NOT NULL,
                relation TEXT NOT NULL,
                object_text TEXT NOT NULL,
                episode_id INTEGER NOT NULL,
                FOREIGN KEY (episode_id) REFERENCES episodes(id)
            )
        """)
        con.close()
    except sqlite3.Error as e:
        print(f"Database error: {e}", file=sys.stderr)
        sys.exit(1)

def get_processed_files():
    """Retrieves the set of already processed source files from the database."""
    try:
        con = sqlite3.connect(DB_FILE)
        cur = con.cursor()
        cur.execute("SELECT source_file FROM episodes")
        processed = {row[0] for row in cur.fetchall()}
        con.close()
        return processed
    except sqlite3.Error as e:
        print(f"Database error while fetching processed files: {e}", file=sys.stderr)
        return set()

def build_memory(logs_directory):
    """Scans for log files and incrementally builds the memory database."""
    print("Starting memory build process...")
    initialize_database()
    
    processed_files = get_processed_files()
    print(f"Found {len(processed_files)} already processed files.")

    log_files = list(Path(logs_directory).glob('**/logs.json'))
    new_files = [f for f in log_files if str(f) not in processed_files]

    if not new_files:
        print("No new log files to process. Your memory is up to date.")
        return

    print(f"Found {len(new_files)} new log files to process...")
    
    episodes_to_add = []
    for log_file in new_files:
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, list):
                    continue
                for entry in data:
                    if entry.get('type') == 'user' and 'message' in entry:
                        episodes_to_add.append((
                            entry.get('timestamp'),
                            entry.get('sessionId'),
                            entry.get('messageId'),
                            entry.get('message'),
                            str(log_file)
                        ))
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not process {log_file}. Error: {e}", file=sys.stderr)

    if not episodes_to_add:
        print("No new user messages found in the new files.")
        return

    try:
        con = sqlite3.connect(DB_FILE)
        cur = con.cursor()
        for episode in episodes_to_add:
            try:
                cur.execute("INSERT INTO episodes (timestamp, session_id, message_id, message, source_file) VALUES (?, ?, ?, ?, ?)", episode)
            except sqlite3.IntegrityError:
                # This handles the rare case where a file was processed by another run
                # after the initial check.
                print(f"Warning: {episode[4]} with message_id {episode[2]} was already in the database. Skipping.", file=sys.stderr)

        con.commit()
        con.close()
        print(f"Successfully added {len(episodes_to_add)} new entries to your memory.")
    except sqlite3.Error as e:
        print(f"Database error during insert: {e}", file=sys.stderr)

def search_memory(query):
    """Searches the memory for the given query using semantic similarity."""
    load_model()
    if model is None:
        print("Error: SentenceTransformer model not loaded.", file=sys.stderr)
        return

    query_embedding = model.encode([query])[0]

    print(f"Searching for: {query} (semantic search)")
    try:
        con = sqlite3.connect(DB_FILE)
        cur = con.cursor()
        cur.execute("SELECT id, timestamp, message, embedding FROM episodes WHERE embedding IS NOT NULL")
        all_entries = cur.fetchall()
        con.close()

        if not all_entries:
            print("No embedded entries found to search.")
            return

        # Calculate cosine similarity
        similarities = []
        for entry_id, timestamp, message, embedding_bytes in all_entries:
            stored_embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
            similarity = np.dot(query_embedding, stored_embedding) / (np.linalg.norm(query_embedding) * np.linalg.norm(stored_embedding))
            similarities.append((similarity, timestamp, message))

        similarities.sort(key=lambda x: x[0], reverse=True)

        print("\nTop 5 most similar entries:")
        for similarity, timestamp, message in similarities[:5]:
            print(f"Similarity: {similarity:.4f} | [{timestamp}] {message}")

    except sqlite3.Error as e:
        print(f"Database error during semantic search: {e}", file=sys.stderr)
    except Exception as e:
        print(f"An error occurred during semantic search: {e}", file=sys.stderr)

def embed_memory():
    """Generates and stores embeddings for messages without them."""
    load_model()
    if model is None:
        print("Error: SentenceTransformer model not loaded.", file=sys.stderr)
        return

    print("Generating embeddings for new entries...")
    try:
        con = sqlite3.connect(DB_FILE)
        cur = con.cursor()
        cur.execute("SELECT id, message FROM episodes WHERE embedding IS NULL")
        rows_to_embed = cur.fetchall()

        if not rows_to_embed:
            print("No new entries to embed.")
            con.close()
            return

        messages = [row[1] for row in rows_to_embed]
        ids = [row[0] for row in rows_to_embed]

        print(f"Embedding {len(messages)} messages...")
        embeddings = model.encode(messages, show_progress_bar=True)

        for i, embedding in enumerate(embeddings):
            cur.execute("UPDATE episodes SET embedding = ? WHERE id = ?", (embedding.tobytes(), ids[i]))
        
        con.commit()
        con.close()
        print(f"Successfully embedded {len(messages)} messages.")

    except sqlite3.Error as e:
        print(f"Database error during embedding: {e}", file=sys.stderr)
    except Exception as e:
        print(f"An error occurred during embedding: {e}", file=sys.stderr)

def build_lexicon():
    """Builds the lexicon from all messages in the episodes table."""
    print("Building lexicon...")
    try:
        con = sqlite3.connect(DB_FILE)
        cur = con.cursor()
        cur.execute("SELECT message FROM episodes")
        all_messages = cur.fetchall()

        word_frequencies = {}
        for (message,) in all_messages:
            words = message.lower().split()
            for word in words:
                word = word.strip(".,!?;:\"'()").strip()
                if word:
                    word_frequencies[word] = word_frequencies.get(word, 0) + 1

        cur.execute("DELETE FROM lexicon") # Clear existing lexicon
        for word, frequency in word_frequencies.items():
            cur.execute("INSERT OR REPLACE INTO lexicon (word, frequency) VALUES (?, ?)", (word, frequency))
        
        con.commit()
        con.close()
        print(f"Lexicon built with {len(word_frequencies)} unique words.")

    except sqlite3.Error as e:
        print(f"Database error during lexicon build: {e}", file=sys.stderr)
    except Exception as e:
        print(f"An error occurred during lexicon build: {e}", file=sys.stderr)

def search_lexicon(word):
    """Searches the lexicon for a given word and returns its frequency."""
    print(f"Searching lexicon for: {word}")
    try:
        con = sqlite3.connect(DB_FILE)
        cur = con.cursor()
        cur.execute("SELECT frequency FROM lexicon WHERE word = ?", (word.lower(),))
        result = cur.fetchone()
        con.close()

        if result:
            print(f"Word '{word}' found with frequency: {result[0]}")
        else:
            print(f"Word '{word}' not found in lexicon.")

    except sqlite3.Error as e:
        print(f"Database error during lexicon search: {e}", file=sys.stderr)

def build_knowledge_graph():
    """Builds a knowledge graph from messages in the episodes table."""
    print("Building knowledge graph...")
    try:
        con = sqlite3.connect(DB_FILE)
        cur = con.cursor()
        cur.execute("SELECT id, message FROM episodes")
        all_messages = cur.fetchall()

        for episode_id, message in all_messages:
            doc = nlp(message)
            
            # Extract entities
            for ent in doc.ents:
                cur.execute("INSERT OR IGNORE INTO entities (text, label, episode_id) VALUES (?, ?, ?)", (ent.text, ent.label_, episode_id))
            
            # Extract relationships (simple dependency parsing for now)
            for token in doc:
                if token.dep_ in ("nsubj", "dobj", "attr", "prep", "pobj"): # Simplified relations
                    if token.head.pos_ == "VERB" and token.pos_ in ("NOUN", "PROPN"):
                        subject = ""
                        obj = ""
                        # Find subject
                        for child in token.head.children:
                            if child.dep_ == "nsubj":
                                subject = child.text
                        # Find object
                        for child in token.head.children:
                            if child.dep_ == "dobj":
                                obj = child.text
                        
                        if subject and obj:
                            cur.execute("INSERT OR IGNORE INTO relationships (subject_text, relation, object_text, episode_id) VALUES (?, ?, ?, ?)", (subject, token.head.text, obj, episode_id))
        
        con.commit()
        con.close()
        print("Knowledge graph built successfully.")

    except sqlite3.Error as e:
        print(f"Database error during knowledge graph build: {e}", file=sys.stderr)
    except Exception as e:
        print(f"An error occurred during knowledge graph build: {e}", file=sys.stderr)

def main():
    """Main function to parse arguments and run the appropriate command."""
    parser = argparse.ArgumentParser(description="Episodic: Your Personal Digital Memory CLI.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build", help="Build or update the memory from log files.")
    build_parser.add_argument("directory", type=str, help="The root directory to scan for logs.json files (e.g., '.').")

    search_parser = subparsers.add_parser("search", help="Search the memory.")
    search_parser.add_argument("query", type=str, help="The keyword or phrase to search for.")

    embed_parser = subparsers.add_parser("embed", help="Generate and store embeddings for new messages.")

    lexicon_parser = subparsers.add_parser("lexicon", help="Manage the lexicon.")
    lexicon_subparsers = lexicon_parser.add_subparsers(dest="lexicon_command", required=True)

    lexicon_build_parser = lexicon_subparsers.add_parser("build", help="Build the lexicon from existing messages.")
    lexicon_search_parser = lexicon_subparsers.add_parser("search", help="Search the lexicon for a word.")
    lexicon_search_parser.add_argument("word", type=str, help="The word to search for in the lexicon.")

    kg_parser = subparsers.add_parser("kg", help="Manage the knowledge graph.")
    kg_subparsers = kg_parser.add_subparsers(dest="kg_command", required=True)
    kg_build_parser = kg_subparsers.add_parser("build", help="Build the knowledge graph from existing messages.")

    args = parser.parse_args()

    if args.command == "build":
        build_memory(args.directory)
    elif args.command == "search":
        search_memory(args.query)
    elif args.command == "embed":
        embed_memory()
    elif args.command == "lexicon":
        if args.lexicon_command == "build":
            build_lexicon()
        elif args.lexicon_command == "search":
            search_lexicon(args.word)
    elif args.command == "kg":
        if args.kg_command == "build":
            build_knowledge_graph()

if __name__ == "__main__":
    main()
