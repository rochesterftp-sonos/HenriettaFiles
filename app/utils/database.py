"""
Database utilities for managing notes and comments
Uses SQLite for persistent storage
"""
import sqlite3
from datetime import datetime
from pathlib import Path
import sys

# Add parent directory to path to import config
sys.path.append(str(Path(__file__).parent.parent.parent))
from config.settings import DATABASE_PATH, DATABASE_DIR


def init_database():
    """
    Initialize the database and create tables if they don't exist
    """
    # Ensure database directory exists
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Create notes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_number TEXT NOT NULL,
            note_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT DEFAULT 'User',
            FOREIGN KEY (job_number) REFERENCES jobs(job_number)
        )
    ''')

    # Create index on job_number for faster lookups
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_notes_job_number
        ON notes(job_number)
    ''')

    conn.commit()
    conn.close()


def add_note(job_number, note_text, created_by='User'):
    """
    Add a note to the database

    Args:
        job_number: Job number (e.g., "041265-9-1")
        note_text: The note content
        created_by: Username of the person creating the note

    Returns:
        The ID of the newly created note, or None if failed
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO notes (job_number, note_text, created_by)
            VALUES (?, ?, ?)
        ''', (job_number, note_text, created_by))

        note_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return note_id

    except Exception as e:
        print(f"Error adding note: {str(e)}")
        return None


def get_notes(job_number):
    """
    Get all notes for a specific job, ordered by most recent first

    Args:
        job_number: Job number to retrieve notes for

    Returns:
        List of tuples: (id, job_number, note_text, created_at, created_by)
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, job_number, note_text, created_at, created_by
            FROM notes
            WHERE job_number = ?
            ORDER BY created_at DESC
        ''', (job_number,))

        notes = cursor.fetchall()
        conn.close()

        return notes

    except Exception as e:
        print(f"Error retrieving notes: {str(e)}")
        return []


def delete_note(note_id):
    """
    Delete a note by ID

    Args:
        note_id: The ID of the note to delete

    Returns:
        True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute('DELETE FROM notes WHERE id = ?', (note_id,))

        conn.commit()
        conn.close()

        return True

    except Exception as e:
        print(f"Error deleting note: {str(e)}")
        return False


def get_all_notes():
    """
    Get all notes in the database

    Returns:
        List of tuples: (id, job_number, note_text, created_at, created_by)
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, job_number, note_text, created_at, created_by
            FROM notes
            ORDER BY created_at DESC
        ''')

        notes = cursor.fetchall()
        conn.close()

        return notes

    except Exception as e:
        print(f"Error retrieving all notes: {str(e)}")
        return []


def get_notes_count(job_number):
    """
    Get the count of notes for a specific job

    Args:
        job_number: Job number

    Returns:
        Count of notes
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT COUNT(*) FROM notes WHERE job_number = ?
        ''', (job_number,))

        count = cursor.fetchone()[0]
        conn.close()

        return count

    except Exception as e:
        print(f"Error counting notes: {str(e)}")
        return 0


if __name__ == "__main__":
    # Test the database functions
    print("Initializing database...")
    init_database()

    print("Adding test notes...")
    note_id = add_note("041265-9-1", "Test note: Need to check engineering", "Kyle")
    print(f"Added note with ID: {note_id}")

    note_id2 = add_note("041265-9-1", "Test note: Drawing updated", "Kyle")
    print(f"Added note with ID: {note_id2}")

    print("\nRetrieving notes for job 041265-9-1:")
    notes = get_notes("041265-9-1")
    for note in notes:
        print(f"  - [{note[3]}] {note[4]}: {note[2]}")

    print(f"\nNotes count: {get_notes_count('041265-9-1')}")

    print("\nDatabase setup complete!")
