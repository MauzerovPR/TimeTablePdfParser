import dataclasses
import typing
import warnings


@dataclasses.dataclass
class Subject:
    name: str

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.name.replace(" ", "") == other.name.replace(" ", "")

    def __hash__(self):
        return hash(self.name.replace(" ", ""))

    def __str__(self):
        return f"{self.name!r}"

    def __post_init__(self):
        words = self.name.split(" ")
        self.name = ""
        for word in words:
            if len(word) < 4 and word not in self.__class__.__SHORT_WORDS:
                self.name += word
            else:
                self.name += " " + word
        self.name = self.name.strip()

        self.__class__.ALL.add(self)

    ALL = set()
    __SHORT_WORDS = ("i", "z")


@dataclasses.dataclass
class Teacher:
    name: str
    surname: str = dataclasses.field(default=None, kw_only=True)

    def __hash__(self):
        return hash((self.name, self.surname))

    def __post_init__(self):
        if "/" in self.name:
            warnings.warn("Multiple teachers is not implemented yet.", RuntimeWarning)
            self.__class__.ALL.add(self)
            return
        space_count = self.name.count(" ")
        if space_count > 1:
            self.name = self.name.replace(" ", "", space_count - 1)

        if self.surname is None:
            self.surname, self.name = self.name.split(" ", 1)
        self.__class__.ALL.add(self)

    def __str__(self):
        return f"{self.name} {self.surname}"

    ALL = set()


@dataclasses.dataclass
class Group:
    any: typing.Any = dataclasses.field(default=None, compare=False)

    def __str__(self):
        return f"{self.any!r}"


@dataclasses.dataclass(frozen=True)
class LessonTime:
    hour: int
    day: int
    block_length: int = dataclasses.field(default=1, compare=False)

    def __iter__(self):
        return dataclasses.astuple(self).__iter__()


@dataclasses.dataclass
class Lesson:
    subject: Subject
    teacher: Teacher
    room: str
    groups: Group = dataclasses.field(default_factory=Group, compare=False)
    time: LessonTime = dataclasses.field(default=None, compare=False)

    def __str__(self):
        return f"{self.teacher=!r}, {self.subject=!r}, {self.room=!r}, {self.groups=!r}"

    def __repr__(self):
        return f"{self.__class__.__name__}"\
               f"(subject={self.subject!r},"\
               f"teacher={self.teacher!r},"\
               f"room={self.room!r},"\
               f"groups={self.groups!r})"

