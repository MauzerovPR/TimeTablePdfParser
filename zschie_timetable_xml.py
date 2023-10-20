import dataclasses
import re
import sqlite3
import warnings
from typing import Iterator

import tkinter as tk

from pdfminer.layout import LAParams, LTTextBox, LTLine
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator

import db
import geometry
import school
from geometry import Line, Point, Box
from school import Subject, Teacher, Group
from pprint import pprint

import numpy as np
import pandas as pd


def processPage(
        page: PDFPage,
        *,
        pdf_interpreter: PDFPageInterpreter,
        pdf_device: PDFPageAggregator
) -> Iterator[geometry.Line | geometry.Text]:
    pdf_interpreter.process_page(page)
    layout = pdf_device.get_result()

    for lobj in layout:
        if not hasattr(lobj, "bbox"):  # skip objects without bounding box
            continue
        x1, y1, x2, y2 = map(lambda x: int(x * 10_000), lobj.bbox)
        if isinstance(lobj, LTTextBox):
            yield geometry.Text(
                lobj.get_text(),
                geometry.Box(geometry.Point(x1, y1), geometry.Point(x2, y2)),
            )
        elif isinstance(lobj, LTLine):
            yield geometry.Line(x1, y1, x2, y2)


def readPage(page: PDFPage):
    global interpreter, device

    objects = processPage(page, pdf_interpreter=interpreter, pdf_device=device)

    lines, texts = [], []
    lines: list[geometry.Line]
    for obj in objects:
        if isinstance(obj, geometry.Line):
            lines.append(obj)
        elif isinstance(obj, geometry.Text):
            texts.append(obj)
    _, class_name, _, educator, *texts = texts
    app = tk.Tk()
    canvas = tk.Canvas(app, width=1200, height=800)

    top_left_x = float("+inf")
    top_left_y = float("+inf")
    bottom_right_x = float("-inf")
    bottom_right_y = float("-inf")

    # find the top left and bottom right points
    for line in lines:
        x1, y1, x2, y2 = line
        top_left_x = min(top_left_x, x1)
        top_left_y = min(top_left_y, y1)
        bottom_right_x = max(bottom_right_x, x2)
        bottom_right_y = max(bottom_right_y, y2)

    # rotate all lines by 180 degrees on the x-axis
    for line in lines:
        line.y1 = bottom_right_y - line.y1 + top_left_y
        line.y2 = bottom_right_y - line.y2 + top_left_y

        line.y1, line.y2 = line.y2, line.y1
        canvas.create_line(*line.dimensions)
    # rotate all texts by 180 degrees on the x-axis
    for text in texts:
        text.box.top_left.y = bottom_right_y - text.box.top_left.y + top_left_y
        text.box.bottom_right.y = bottom_right_y - text.box.bottom_right.y + top_left_y

        text.box.top_left.y, text.box.bottom_right.y = text.box.bottom_right.y, text.box.top_left.y

    timetable_rect = Line(
        sorted(set(map(lambda x: x.x1, lines)))[1],
        sorted(set(map(lambda x: x.y1, lines)))[1],
        sorted(set(map(lambda x: x.x1, lines)), reverse=True)[0],
        sorted(set(map(lambda x: x.y1, lines)), reverse=True)[0]
    )

    canvas.create_rectangle(
        *timetable_rect.dimensions,
        outline="red",
        width=2
    )

    """
        Crazy algorithm to find lines that are in the same row or column and merge them into one line
    """
    left_to_right_lines_all: [Line] = list(filter(lambda x: x.x1 != x.x2, lines))
    top_to_bottom_lines_all: [Line] = list(filter(lambda x: x.y1 != x.y2, lines))
    left_to_right_lines: [Line] = []
    top_to_bottom_lines: [Line] = []
    for line in left_to_right_lines_all:
        if line.y1 < timetable_rect.y1:
            continue
        for existing_line in left_to_right_lines:
            if line.y1 != existing_line.y1:
                continue
            if line.x1 <= existing_line.x1 <= line.x2 or line.x1 <= existing_line.x2 <= line.x2:
                existing_line.x1 = max(timetable_rect.x1, min(existing_line.x1, line.x1))
                existing_line.x2 = max(existing_line.x2, line.x2)
                break
        else:
            left_to_right_lines.append(line)

    for line in top_to_bottom_lines_all:
        if line.x1 < timetable_rect.x1:
            continue
        for existing_line in top_to_bottom_lines:
            if line.x1 != existing_line.x1:
                continue
            if line.y1 <= existing_line.y1 <= line.y2 or line.y1 <= existing_line.y2 <= line.y2:
                existing_line.y1 = max(timetable_rect.y1, min(existing_line.y1, line.y1))
                existing_line.y2 = max(existing_line.y2, line.y2)
                break
        else:
            top_to_bottom_lines.append(line)
    """
        End of crazy algorithm
    """
    for line in left_to_right_lines:
        canvas.create_line(*line.dimensions, fill="green", width=2)
    for line in top_to_bottom_lines:
        canvas.create_line(*line.dimensions, fill="purple", width=2)

    intersection_points: [Point] = []
    for horizontal in left_to_right_lines:
        for vertical in top_to_bottom_lines:
            # lines are perpendicular
            if horizontal.x1 <= vertical.x1 <= horizontal.x2 and vertical.y1 <= horizontal.y1 <= vertical.y2:
                point = Point(vertical.x1, horizontal.y1)
                if point in intersection_points:
                    continue

                if horizontal.x1 < point.x:
                    point.directions.append("left")
                if horizontal.x2 > point.x:
                    point.directions.append("right")
                if vertical.y1 < point.y:
                    point.directions.append("up")
                if vertical.y2 > point.y:
                    point.directions.append("down")

                intersection_points.append(point)

    cells = set()
    for point in filter(lambda p: "right" in p.directions and "down" in p.directions, intersection_points):
        closest_right = sorted(filter(
            lambda p: "down" in p.directions and p.y == point.y and p.x > point.x,
            intersection_points
        ), key=lambda p: p.x)
        # find the closest bottom right point
        for right_point in closest_right:
            closest_down = sorted(filter(
                lambda p: "left" in p.directions and p.x == right_point.x and p.y > right_point.y,
                intersection_points
            ), key=lambda p: p.y)

            cells.add(Box(point, closest_down[0]))
            break
    cells = list(sorted(cells, key=lambda c: (c.top_left.x, c.top_left.y), reverse=True))

    max_height = max(map(lambda c: c.height, cells))
    min_width = min(map(lambda c: c.width, cells))

    lesson_cells = []
    for cell in cells:
        lesson = geometry.LessonCell.from_box(cell)
        lesson.index = school.LessonTime(
            (cell.top_left.x - top_left_x) // min_width - 1,
            (cell.top_left.y - top_left_y) // max_height,
            cell.width // min_width,
        )
        assert lesson.index.block_length > 0
        lesson_cells.append(lesson)
    cells = lesson_cells
    for text in texts:
        for cell in cells:
            if cell.top_left.x <= text.box.top_left.x <= cell.bottom_right.x and \
                    cell.top_left.y <= text.box.top_left.y <= cell.bottom_right.y:
                cell.texts.append(text)
                break

    for cell in cells:
        for text in cell.texts:
            canvas.create_text(
                *map(Line.to_cm, text.box.top_left),
                text=text.text,
                anchor="nw",
                font=("Arial", 7)
            )
        # if text := cell.get_lesson():
        #     print(text)

    lessons = list(filter(lambda x: x is not None, map(lambda x: x.get_lesson(), cells)))

    # pprint(lessons)

    def draw_cell(cell: Box):
        nonlocal canvas
        canvas.delete("all")

        for line in left_to_right_lines:
            canvas.create_line(*line.dimensions, fill="green", width=2)
        for line in top_to_bottom_lines:
            canvas.create_line(*line.dimensions, fill="purple", width=2)
        canvas.create_rectangle(
            *cell.top_left.dimensions, *cell.bottom_right.dimensions,
            fill="yellow"
        )

    def draw_next_cell():
        nonlocal cells
        cell = cells.pop()
        draw_cell(cell)

    canvas.bind("<Button-1>", lambda event: draw_next_cell())
    canvas.pack()
    # app.mainloop()
    educator_surname, educator_name = re.match("Wychowawca : (.+) (.+)", educator.text).groups()
    educator, = filter(
        lambda teacher: hash(teacher) == hash((educator_name, educator_surname)),
        Teacher.ALL
    )
    educator.class_name = class_name.text.strip()

    for lesson in lessons:
        lesson.class_name = educator.class_name

    return lessons


if __name__ == '__main__':
    fp = open('Plan-zajec-edukacyjnych-od-dnia-4.09.2023-r..pdf', 'rb')
    rsrcmgr = PDFResourceManager()
    laparams = LAParams()
    laparams.line_margin = -.1
    device = PDFPageAggregator(rsrcmgr, laparams=laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    pages = PDFPage.get_pages(fp)
    for i in range(0):  # 14
        next(pages)
    lessons: list[school.Lesson] = readPage(next(pages))
    for page in pages:
        lessons += readPage(page)

    # pprint(Teacher.ALL)

    with db.Database() as cursor:
        cursor.executemany(
            """
            INSERT INTO Teachers (name, surname, class_id)
            VALUES (?, ?, ?)
            """,
            pd.DataFrame(
                filter(
                    lambda teacher: teacher.surname is not None,
                    Teacher.ALL
                ),
            )
            .itertuples(index=False)
        )

        room_subject_group = pd.DataFrame(map(
            lambda lesson: (
                lesson.room,
                lesson.subject.name,
                lesson.groups.any is not None,
            ),
            lessons
        ))

        cursor.executemany(
            """
            INSERT INTO Subjects (name, is_group)
            VALUES (?, ?)
            """,
            room_subject_group[[1, 2]]
            .drop_duplicates()
            .itertuples(index=False)
        )

        cursor.executemany(
            """
            INSERT INTO Rooms (room_id)
            VALUES (?)
            """,
            room_subject_group[[0]]
            .drop_duplicates()
            .itertuples(index=False)
        )

        cursor.executemany(
            """
            INSERT INTO Subject_Rooms (subject_id, room_id)
            VALUES (
                (SELECT subject_id FROM Subjects WHERE name = ? LIMIT 1),
                ?)
            """,
            room_subject_group[[1, 0]]
            .drop_duplicates()
            .itertuples(index=False)
        )
        for subject_teacher_group in pd.DataFrame(map(
                    lambda lesson: (
                        lesson.subject.name,
                        lesson.teacher.name,
                        lesson.teacher.surname,
                        lesson.class_name
                    ),
                    lessons
                )) \
                .drop_duplicates() \
                .itertuples(index=False):
            try:
                cursor.execute(
                    """
                    INSERT INTO Subject_Teachers_Class (subject_id, teacher_id, class_id)
                    VALUES (
                        (SELECT subject_id FROM Subjects WHERE name = ? LIMIT 1),
                        (SELECT teacher_id FROM Teachers WHERE name = ? AND surname = ? LIMIT 1),
                        ?
                    ) ON CONFLICT DO NOTHING
                    """,
                    subject_teacher_group
                )
            except sqlite3.IntegrityError as e:
                warnings.warn(f"Subject_Teachers_Class {subject_teacher_group} was not added to the database,\ndue to {e}",
                              RuntimeWarning)

        for lesson in lessons:
            try:
                for i in range(lesson.time.block_length):
                    cursor.execute(
                        """
                        INSERT INTO Lesson (subject_id, teacher_id, room_id, class_id, day, hour)
                        VALUES (
                            (SELECT subject_id FROM Subjects WHERE name = ? LIMIT 1),
                            (SELECT teacher_id FROM Teachers WHERE name = ? AND surname = ? LIMIT 1),
                            ?, ?, ?, ?
                        )
                        """,
                        (
                            lesson.subject.name,
                            lesson.teacher.name,
                            lesson.teacher.surname,
                            lesson.room,
                            lesson.class_name,
                            lesson.time.day,
                            lesson.time.hour + i
                        )
                    )
            except sqlite3.IntegrityError as e:
                warnings.warn(f"Lesson {lesson} was not added to the database,\ndue to {e}", RuntimeWarning)
                continue  # skip block_length > 1 lessons immediately

    # with db.Database() as db:
    #     db.add_teachers(Teacher.ALL)
    #     db.add_subjects(Subject.ALL)
    #     db.add_groups(Group.ALL)
    #     db.add_lessons(lessons)
