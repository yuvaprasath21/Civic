from app.models.user import User, Role, Permission, UserRoleAssignment          # noqa: F401
from app.models.profile import CitizenProfile, StaffProfile                     # noqa: F401
from app.models.department import Department, IssueCategoryMapping              # noqa: F401
from app.models.location import Location, RiskZone                              # noqa: F401
from app.models.civic_issue import CivicIssue                                   # noqa: F401
from app.models.issue_image import IssueImage                                   # noqa: F401
from app.models.ai_prediction import AIPrediction                               # noqa: F401
from app.models.issue_workflow import (                                        # noqa: F401
    IssueAssignment,
    IssueStatusHistory,
    IssueComment,
    IssueDuplicate,
    IssueFeedback,
)
from app.models.notification import Notification, AuditLog                      # noqa: F401
from app.models.otp import OtpVerification                                      # noqa: F401

__all__ = [
    "User", "Role", "Permission", "UserRoleAssignment",
    "CitizenProfile", "StaffProfile",
    "Department", "IssueCategoryMapping",
    "Location", "RiskZone",
    "CivicIssue",
    "IssueImage",
    "AIPrediction",
    "IssueAssignment", "IssueStatusHistory", "IssueComment", "IssueDuplicate", "IssueFeedback",
    "Notification", "AuditLog",
    "OtpVerification",
]
