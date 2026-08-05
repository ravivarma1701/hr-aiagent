import enum


class Role(str, enum.Enum):
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    EMPLOYEE = "EMPLOYEE"


class EmployeeStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class AttendanceStatus(str, enum.Enum):
    ON_TIME = "ON_TIME"
    LATE = "LATE"
    WFH = "WFH"
    ABSENT = "ABSENT"


class LeaveType(str, enum.Enum):
    CASUAL = "CASUAL"
    SICK = "SICK"
    EARNED = "EARNED"


class LeaveRequestStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class HalfDayPeriod(str, enum.Enum):
    FIRST_HALF = "FIRST_HALF"
    SECOND_HALF = "SECOND_HALF"


class TicketCategory(str, enum.Enum):
    IT = "IT"
    HR = "HR"
    ONBOARDING = "ONBOARDING"


class TicketPriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class TicketStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"


class SkillLevel(str, enum.Enum):
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    EXPERT = "EXPERT"


class ProjectStatus(str, enum.Enum):
    ONGOING = "ONGOING"
    COMPLETED = "COMPLETED"
    ON_HOLD = "ON_HOLD"
    PLANNED = "PLANNED"
