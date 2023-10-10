import dataclasses
import re

from school import Lesson, Subject, Teacher, Group, LessonTime


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

    @property
    def width(self):
        return abs(self.x2 - self.x1)

    @property
    def height(self):
        return abs(self.y2 - self.y1)

    def __hash__(self):
        return hash((self.top_left, self.bottom_right))

    @staticmethod
    def overlap(box1, box2):
        return box1.x1 <= box2.x2 and box1.x2 >= box2.x1 and box1.y1 <= box2.y2 and box1.y2 >= box2.y1


@dataclasses.dataclass
class Text:
    text: str
    box: Box

    def __hash__(self):
        return hash(self.box)


@dataclasses.dataclass
class LessonCell(Box):
    @classmethod
    def from_box(cls, box: Box):
        return cls(box.top_left, box.bottom_right)

    texts: list[Text] = dataclasses.field(default_factory=list, compare=False, init=False)
    index: LessonTime = dataclasses.field(default=None, compare=False, init=False)

    @staticmethod
    def combine_texts(list_of_texts: list[Text]) -> list[Text]:
        # Matrix of distances between texts
        matrix = [
            [
                (
                    round(abs(list_of_texts[i].box.y2 - list_of_texts[j].box.y1), -1),
                    round(list_of_texts[i].box.height, -1) == round(list_of_texts[j].box.height, -1)
                )
                for j in range(len(list_of_texts))
            ] for i in range(len(list_of_texts))
        ]

        all_distances = dict()
        for i, _texts in enumerate(matrix):
            for j, distance_height in enumerate(_texts[:i]):
                # TODO: this may result in more texts being combined than necessary
                #  (e.g. if there are 2 or more texts span across multiple lines
                #  and theirs spaces between them are the same, they will be combined)
                #  although for the current data set it works fine
                all_distances.setdefault(distance_height, set())
                all_distances[distance_height] |= {list_of_texts[i], list_of_texts[j]}

        # remove distances that are too rare
        for distance_height, count in list(all_distances.items()):
            if len(count) < 2 or not distance_height[1]:
                del all_distances[distance_height]

        new_all_distances = dict()
        for (distance, _), _texts in all_distances.items():
            texts = list(_texts)
            for new_distance, new_all_distance_texts in new_all_distances.items():
                if texts[0] == new_all_distance_texts[0]:
                    if len(texts) > len(new_all_distance_texts):
                        new_all_distances[new_distance] = texts
                    break
            else:
                new_all_distances[distance] = texts

        text_lines = []
        for texts in list(new_all_distances.values()):
            sorted_texts = sorted(texts, key=lambda t: t.box.y1)
            text_lines.append(Text(
                ' '.join(map(lambda t: t.text, sorted_texts)),
                Box(sorted_texts[0].box.top_left, sorted_texts[-1].box.bottom_right)
            ))
        for text in list_of_texts:
            if any(map(lambda t: text in t, new_all_distances.values())):
                continue
            text_lines.append(text)

        return sorted(text_lines, key=lambda t: t.box.y1)

    def get_lesson(self):
        texts = LessonCell.combine_texts(self.texts)

        texts = list(map(lambda t: re.sub(r"\s+", " ", t.text).strip(), texts))

        match texts:
            case [teacher, subject, room]:
                lesson = Lesson(Subject(subject), Teacher(teacher), room, time=LessonTime(*self.index))
            case [teacher, subject, room, groups]:
                if teacher[0].islower():
                    teacher, subject = subject, teacher
                lesson = Lesson(Subject(subject), Teacher(teacher), room, Group(groups), time=LessonTime(*self.index))
            case _:
                return None
        return lesson
