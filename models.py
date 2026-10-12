from datetime import datetime, date, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def get_utc_now():
    """Returns timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)

class Task(db.Model):
    """
    Task model representing an item in the TaskMaster workflow application.
    Demonstrates SQLAlchemy ORM fundamentals, relationships, constraints,
    and Python property getters for derived business logic.
    """
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=False, default='General')
    priority = db.Column(db.String(20), nullable=False, default='Medium') # Low, Medium, High, Urgent
    status = db.Column(db.String(20), nullable=False, default='Pending')   # Pending, In Progress, Completed
    due_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=get_utc_now)
    updated_at = db.Column(db.DateTime, default=get_utc_now, onupdate=get_utc_now)

    @property
    def is_overdue(self):
        """Checks if the task is past its due date and not yet completed."""
        if self.due_date and self.status != 'Completed':
            return self.due_date < date.today()
        return False

    @property
    def days_remaining(self):
        """Calculates days left until the due date."""
        if self.due_date:
            delta = (self.due_date - date.today()).days
            return delta
        return None

    @property
    def priority_badge_class(self):
        """Returns Bootstrap color class based on priority level."""
        mapping = {
            'Urgent': 'badge-urgent',
            'High': 'badge-high',
            'Medium': 'badge-medium',
            'Low': 'badge-low'
        }
        return mapping.get(self.priority, 'badge-medium')

    @property
    def status_badge_class(self):
        """Returns Bootstrap color class based on status."""
        mapping = {
            'Completed': 'badge-completed',
            'In Progress': 'badge-in-progress',
            'Pending': 'badge-pending'
        }
        return mapping.get(self.status, 'badge-pending')

    def to_dict(self):
        """Converts task record to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'priority': self.priority,
            'status': self.status,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'is_overdue': self.is_overdue,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f'<Task {self.id}: {self.title} [{self.status}]>'
