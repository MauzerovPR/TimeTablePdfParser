import dataclasses
import typing


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
        self.__class__.ALL.add(self)

    ALL = set()


@dataclasses.dataclass
class Teacher:
    name: str
    surname: str = dataclasses.field(default=None, kw_only=True)

    def __hash__(self):
        return hash((self.name, self.surname))

    def __post_init__(self):
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


@dataclasses.dataclass
class Lesson:
    subject: Subject
    teacher: Teacher
    room: str
    groups: Group = dataclasses.field(default_factory=Group, compare=False)

    def __str__(self):
        return f"{self.teacher=!r}, {self.subject=!r}, {self.room=!r}, {self.groups=!r}"

    def __repr__(self):
        return f"{self.__class__.__name__}"\
               f"(subject={self.subject!r},"\
               f"teacher={self.teacher!r},"\
               f"room={self.room!r},"\
               f"groups={self.groups!r})"

