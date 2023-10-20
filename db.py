import os
from sqlite3 import connect
import sqlite3
import sqlalchemy as db
from typing import TypeVar


class Database:
    connection: sqlite3.Connection
    cursor: sqlite3.Cursor

    def __enter__(self):
        os.remove("database.db")
        self.connection = connect("database.db")
        self.cursor = self.connection.cursor()
        self.initialize()
        return self.cursor

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.connection.commit()
        self.connection.close()
        return False

    def initialize(self):
        # create tables if they don't exist
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Teachers (
                teacher_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                surname TEXT NOT NULL,
                class_id VARCHAR(20),
                full_name TEXT NOT NULL GENERATED ALWAYS AS (name || ' ' || surname) VIRTUAL
            );
            """
        )
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Subjects (
                subject_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                is_group BOOLEAN NOT NULL
            );
            """
        )
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Rooms (
                room_id VARCHAR(10) PRIMARY KEY
            );
            """
        )
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Subject_Rooms (
                subject_id INTEGER NOT NULL,
                room_id VARCHAR(10) NOT NULL,
                FOREIGN KEY (subject_id) REFERENCES Subjects(subject_id),
                FOREIGN KEY (room_id) REFERENCES Rooms(room_id),
                PRIMARY KEY (subject_id, room_id)
            );
            """
        )
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Subject_Teachers_Class (
                subject_id INTEGER NOT NULL,
                teacher_id INTEGER NOT NULL,
                class_id VARCHAR(20) NOT NULL,
                FOREIGN KEY (subject_id) REFERENCES Subjects(subject_id),
                FOREIGN KEY (teacher_id) REFERENCES Teachers(teacher_id),
                FOREIGN KEY (class_id) REFERENCES Teachers(class_id),
                PRIMARY KEY (subject_id, teacher_id, class_id)
            );
            """
        )
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Lesson (
                lesson_id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER NOT NULL,
                teacher_id INTEGER NOT NULL,
                room_id INTEGER NOT NULL,
                class_id VARCHAR(20) NOT NULL,
                day INTEGER NOT NULL,
                hour INTEGER NOT NULL,
                FOREIGN KEY (subject_id) REFERENCES Subjects(subject_id),
                FOREIGN KEY (teacher_id) REFERENCES Teachers(teacher_id),
                FOREIGN KEY (room_id) REFERENCES Rooms(room_id)
            );
            """
        )

    def add_teacher(self, *teachers: tuple[str, str, str]):
        self.cursor.executemany(
            """
            INSERT INTO Teachers (name, surname, class_id)
            VALUES (?, ?, ?)
            """,
            teachers
        )

    def add_subject(self, *subjects: tuple[bool, str]):
        self.cursor.executemany(
            """
            INSERT INTO Subjects (is_group, name)
            VALUES (?, ?)
            """,
            subjects
        )

    def add_room(self, *rooms: tuple[str]):
        self.cursor.executemany(
            """
            INSERT INTO Rooms (room_id)
            VALUES (?)
            """,
            rooms
        )

    def add_subject_room(self, subject: None):
        pass

