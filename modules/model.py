from logging import log
import sqlite3
from datetime import datetime
import os

from modules.common import log_msg


class DatabaseManager:
    def __init__(self, db_path: str = "chores.db", reset: bool = False):
        if reset and os.path.exists(db_path):
            os.remove(db_path)
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.setup_database()

    def setup_database(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS Chores (
                chore_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                created INTEGER DEFAULT 0,
                first_completion INTEGER DEFAULT 0,
                last_completion INTEGER DEFAULT 0,
                mean_interval INTEGER DEFAULT 0,
                mad_more INTEGER DEFAULT 0,
                mad_less INTEGER DEFAULT 0,
                next INTEGER DEFAULT 0
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS Intervals (
                interval_id INTEGER PRIMARY KEY AUTOINCREMENT,
                chore_id INTEGER,
                interval INTEGER,
                FOREIGN KEY (chore_id) REFERENCES Chores(chore_id) ON DELETE CASCADE
            )
        """)
        self.conn.commit()

    def add_chore(self, name, created):
        """Add a new chore and return its ID."""
        if isinstance(created, datetime):
            created = round(created.timestamp())
        self.cursor.execute(
            "INSERT INTO Chores (name, created) VALUES (?, ?)", (name, created)
        )
        new_chore_id = self.cursor.lastrowid  # Retrieve the new record ID
        self.conn.commit()
        log_msg(f"Added chore {name} with ID {new_chore_id}.")
        return new_chore_id  # Return the ID to the caller

    def remove_chore(self, chore_id):
        self.cursor.execute("DELETE FROM Chores WHERE chore_id = ?", (chore_id,))
        self.conn.commit()

    def complete_chore(self, chore_id, completion_datetime):
        self.cursor.execute(
            "SELECT chore_id, last_completion FROM Chores WHERE chore_id = ?",
            (chore_id,),
        )
        log_msg(f"In dbm, beginning completion of chore {chore_id}")
        chore = self.cursor.fetchone()

        if not chore:
            return

        chore_id, last_completion = chore
        if isinstance(completion_datetime, datetime):
            completion_datetime = round(completion_datetime.timestamp())

        log_msg(
            f"*Completing chore {chore_id} at {completion_datetime}, {type(completion_datetime) = }."
        )

        if last_completion:
            interval = completion_datetime - last_completion
            self.cursor.execute(
                "INSERT INTO Intervals (chore_id, interval) VALUES (?, ?)",
                (chore_id, interval),
            )

            self.cursor.execute(
                "SELECT interval FROM Intervals WHERE chore_id = ?", (chore_id,)
            )
            intervals = [row[0] for row in self.cursor.fetchall()]

            if len(intervals) >= 1:
                mean_interval = round(sum(intervals) / len(intervals))
                next_due = completion_datetime + mean_interval

                if len(intervals) >= 3:
                    positive_deviations = [
                        i - mean_interval for i in intervals if i > mean_interval
                    ]
                    negative_deviations = [
                        mean_interval - i for i in intervals if i < mean_interval
                    ]

                    mad_more = (
                        round(sum(positive_deviations) / len(positive_deviations))
                        if positive_deviations
                        else 0
                    )
                    mad_less = (
                        round(sum(negative_deviations) / len(negative_deviations))
                        if negative_deviations
                        else 0
                    )

                    self.cursor.execute(
                        """
                        UPDATE Chores 
                        SET mean_interval = ?, mad_more = ?, mad_less = ?, next = ?
                        WHERE chore_id = ?
                        """,
                        (
                            mean_interval,
                            mad_more,
                            mad_less,
                            next_due,
                            chore_id,
                        ),
                    )
                else:
                    self.cursor.execute(
                        "UPDATE Chores SET mean_interval = ?, next = ? WHERE chore_id = ?",
                        (mean_interval, next_due, chore_id),
                    )
        else:
            self.cursor.execute(
                "UPDATE Chores SET first_completion = ? WHERE chore_id = ?",
                (completion_datetime, chore_id),
            )

        self.cursor.execute(
            "UPDATE Chores SET last_completion = ? WHERE chore_id = ?",
            (completion_datetime, chore_id),
        )
        self.conn.commit()

    def list_chores(self):
        self.cursor.execute("""
            SELECT chore_id, name, created, first_completion, last_completion, mean_interval, mad_less, mad_more, next, (SELECT COUNT(*) FROM Intervals WHERE Intervals.chore_id = Chores.chore_id) AS num_completions
            FROM Chores 
            ORDER BY next, name
        """)
        return self.cursor.fetchall()

    def show_chore(self, name):
        self.cursor.execute(
            """
            SELECT chore_id, name, created, first_completion, last_completion, mean_interval, mad_less, mad_more, next, (SELECT COUNT(*) FROM Intervals WHERE Intervals.chore_id = Chores.chore_id) AS num_completions
            FROM Chores WHERE chore_id = ?
        """,
            (name,),
        )
        return self.cursor.fetchone()

    def close(self):
        self.conn.close()
