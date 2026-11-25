from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.issue_workflow import IssueComment, IssueFeedback


class IssueCommentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, *, issue_id: int, author_id: int, body: str, is_internal: bool) -> IssueComment:
        comment = IssueComment(issue_id=issue_id, author_id=author_id, body=body, is_internal=is_internal)
        self.db.add(comment)
        self.db.commit()
        self.db.refresh(comment)
        return comment


class IssueFeedbackRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_issue_id(self, issue_id: int) -> Optional[IssueFeedback]:
        stmt = select(IssueFeedback).where(IssueFeedback.issue_id == issue_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, *, issue_id: int, citizen_id: int, rating: int, comment: Optional[str]) -> IssueFeedback:
        feedback = IssueFeedback(issue_id=issue_id, citizen_id=citizen_id, rating=rating, comment=comment)
        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)
        return feedback
