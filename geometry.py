import dataclasses
import re

from school import Lesson, Subject, Teacher, Group


@dataclasses.dataclass
class Line:
    x1: int
    y1: int
    x2: int
    y2: int

    def __post_init__(self):
        assert self.x1 <= self.x2 and self.y1 <= self.y2
        self.x1 = round(self.x1, -2)
        self.y1 = round(self.y1, -2)
        self.x2 = round(self.x2, -2)
        self.y2 = round(self.y2, -2)

    @property
    def width(self):
        return abs(self.x2 - self.x1)

    @property
    def height(self):
        return abs(self.y2 - self.y1)

    @property
    def dimensions(self):
        return (
            self.to_cm(self.x1),
            self.to_cm(self.y1),
            self.to_cm(self.x2),
            self.to_cm(self.y2)
        )

    @classmethod
    def to_cm(cls, number: float):
        return f"{number / 300_000}cm"

    def __iter__(self):
        return iter((self.x1, self.y1, self.x2, self.y2))


@dataclasses.dataclass
class Point:
    x: int = dataclasses.field(compare=True)
    y: int = dataclasses.field(compare=True)
    directions: list[str] = dataclasses.field(default_factory=list, kw_only=True, compare=False)

    def __hash__(self):
        return hash((self.x, self.y))

    @property
    def dimensions(self):
        return Line.to_cm(self.x), Line.to_cm(self.y)

    def __lt__(self, other):
        return self.x < other.x and self.y < other.y

    def __iter__(self):
        return iter((self.x, self.y))


@dataclasses.dataclass
class Box:
    top_left: Point
    bottom_right: Point

    @property
    def top_right(self):
        return Point(self.bottom_right.x, self.top_left.y)

    @property
    def x1(self):
        return self.top_left.x

    @property
    def y1(self):
        return self.top_left.y

    @property
    def x2(self):
        return self.bottom_right.x

    @property
    def y2(self):
        return self.bottom_right.y

    def __hash__(self):
        return hash((self.top_left, self.bottom_right))


@dataclasses.dataclass
class Text:
    text: str
    box: Box

    def __hash__(self):
        return hash(self.box)


@dataclasses.dataclass
class LessonCell(Box):
    texts: list[Text] = dataclasses.field(default_factory=list, compare=False, init=False)

    @property
    def combined_text(self):
        texts: dict[int, [Text]] = dict()
        for text in sorted(self.texts, key=lambda t: (round(t.box.y2 - t.box.y2, -1), t.box.y2)):
            index = round(text.box.y1 - text.box.y2, -1)
            texts.setdefault(index, [])
            texts[index] += [text]

        text_items = tuple(texts.items())
        for old_key, value in text_items:
            key = sorted(value, key=lambda t: t.box.y2)[0].box.top_left
            texts[key] = value
            del texts[old_key]

        texts = dict(sorted(texts.items(), key=lambda t: t[0].y))

        for key, value in texts.items():
            texts[key] = ' '.join(map(lambda t: t.text, value))
            texts[key] = re.sub(r"\s+", " ", texts[key]).strip()

        match list(texts.items()):
            case [(_, teacher), (_, subject), (_, room)]:
                lesson = Lesson(Subject(subject), Teacher(teacher), room)
            case [(_, teacher), (_, subject), (_, room), (_, groups)]:
                lesson = Lesson(Subject(subject), Teacher(teacher), room, Group(groups))
            case _:
                return None

        return repr(lesson)
