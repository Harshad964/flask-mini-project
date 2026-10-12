import os
import csv
import io
from datetime import datetime, date, timedelta, timezone
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response
from models import db, Task

def get_utc_now():
    """Returns timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)

def create_app():
    """Application factory for Flask application."""
    app = Flask(__name__)

    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'interview-secret-key-taskmaster-2026')
    
    # Ensure instance folder exists for SQLite database
    base_dir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(base_dir, 'instance', 'taskmaster.db')
    os.makedirs(os.path.join(base_dir, 'instance'), exist_ok=True)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize extensions
    db.init_app(app)

    # -------------------------------------------------------------
    # Database Initialization & Seed Data Helper
    # -------------------------------------------------------------
    with app.app_context():
        db.create_all()
        seed_sample_data()

    # -------------------------------------------------------------
    # ROUTES
    # -------------------------------------------------------------

    @app.route('/', methods=['GET'])
    def index():
        """
        Dashboard & Task List route.
        Demonstrates GET query parameters handling:
        - Search query (?search=...)
        - Filtering by status, priority, category
        - Sorting options
        - Aggregated metric calculations
        """
        search_query = request.args.get('search', '').strip()
        status_filter = request.args.get('status', '').strip()
        priority_filter = request.args.get('priority', '').strip()
        category_filter = request.args.get('category', '').strip()
        sort_by = request.args.get('sort', 'created_desc').strip()

        # Base query
        query = db.select(Task)

        # Apply search filter
        if search_query:
            query = query.filter(
                (Task.title.ilike(f'%{search_query}%')) | 
                (Task.description.ilike(f'%{search_query}%'))
            )

        # Apply categorical filters
        if status_filter:
            query = query.filter(Task.status == status_filter)
        if priority_filter:
            query = query.filter(Task.priority == priority_filter)
        if category_filter:
            query = query.filter(Task.category == category_filter)

        # Apply sorting
        if sort_by == 'due_asc':
            query = query.order_by(Task.due_date.asc().nullslast())
        elif sort_by == 'due_desc':
            query = query.order_by(Task.due_date.desc().nullslast())
        elif sort_by == 'priority_desc':
            query = query.order_by(Task.priority.asc())
        elif sort_by == 'created_asc':
            query = query.order_by(Task.created_at.asc())
        else: # default: created_desc
            query = query.order_by(Task.created_at.desc())

        tasks = db.session.scalars(query).all()

        # Compute dashboard analytics metrics
        all_tasks = db.session.scalars(db.select(Task)).all()
        total_count = len(all_tasks)
        completed_count = sum(1 for t in all_tasks if t.status == 'Completed')
        in_progress_count = sum(1 for t in all_tasks if t.status == 'In Progress')
        pending_count = sum(1 for t in all_tasks if t.status == 'Pending')
        overdue_count = sum(1 for t in all_tasks if t.is_overdue)
        completion_rate = int((completed_count / total_count * 100)) if total_count > 0 else 0

        # Unique categories for filter dropdown
        categories = sorted(list(set(t.category for t in all_tasks if t.category)))
        if not categories:
            categories = ['Interview Prep', 'Backend', 'Frontend', 'Database', 'DevOps']

        return render_template(
            'index.html',
            tasks=tasks,
            total_count=total_count,
            completed_count=completed_count,
            in_progress_count=in_progress_count,
            pending_count=pending_count,
            overdue_count=overdue_count,
            completion_rate=completion_rate,
            categories=categories,
            search_query=search_query,
            status_filter=status_filter,
            priority_filter=priority_filter,
            category_filter=category_filter,
            sort_by=sort_by
        )

    @app.route('/tasks/new', methods=['GET', 'POST'])
    def create_task():
        """
        Create a new task.
        Demonstrates GET to render form and POST to process form submission.
        Includes server-side input validation and user flash notifications.
        """
        if request.method == 'POST':
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            category = request.form.get('category', 'General').strip()
            priority = request.form.get('priority', 'Medium').strip()
            status = request.form.get('status', 'Pending').strip()
            due_date_str = request.form.get('due_date', '').strip()

            # Server-side validation
            if not title:
                flash('Task title is required!', 'danger')
                return render_template('task_form.html', action='Create', task=None, form_data=request.form)

            if len(title) > 150:
                flash('Title cannot exceed 150 characters.', 'warning')
                return render_template('task_form.html', action='Create', task=None, form_data=request.form)

            parsed_due_date = None
            if due_date_str:
                try:
                    parsed_due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
                except ValueError:
                    flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
                    return render_template('task_form.html', action='Create', task=None, form_data=request.form)

            # Create and persist new Task entity
            new_task = Task(
                title=title,
                description=description,
                category=category or 'General',
                priority=priority or 'Medium',
                status=status or 'Pending',
                due_date=parsed_due_date
            )

            try:
                db.session.add(new_task)
                db.session.commit()
                flash(f'Task "{title}" created successfully!', 'success')
                return redirect(url_for('index'))
            except Exception as e:
                db.session.rollback()
                flash(f'Database error occurred: {str(e)}', 'danger')

        return render_template('task_form.html', action='Create', task=None, form_data={})

    @app.route('/tasks/<int:task_id>', methods=['GET'])
    def task_detail(task_id):
        """
        Task Detail view.
        Demonstrates parameterized URL routing and db.get_or_404 lookup.
        """
        task = db.get_or_404(Task, task_id)
        return render_template('task_detail.html', task=task)

    @app.route('/tasks/<int:task_id>/edit', methods=['GET', 'POST'])
    def edit_task(task_id):
        """
        Edit an existing task.
        Demonstrates pre-populating form on GET and mutating record on POST.
        """
        task = db.get_or_404(Task, task_id)

        if request.method == 'POST':
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            category = request.form.get('category', 'General').strip()
            priority = request.form.get('priority', 'Medium').strip()
            status = request.form.get('status', 'Pending').strip()
            due_date_str = request.form.get('due_date', '').strip()

            if not title:
                flash('Task title is required!', 'danger')
                return render_template('task_form.html', action='Edit', task=task, form_data=request.form)

            parsed_due_date = None
            if due_date_str:
                try:
                    parsed_due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
                except ValueError:
                    flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
                    return render_template('task_form.html', action='Edit', task=task, form_data=request.form)

            # Update entity fields
            task.title = title
            task.description = description
            task.category = category or 'General'
            task.priority = priority or 'Medium'
            task.status = status or 'Pending'
            task.due_date = parsed_due_date
            task.updated_at = get_utc_now()

            try:
                db.session.commit()
                flash(f'Task "{task.title}" updated successfully!', 'success')
                return redirect(url_for('index'))
            except Exception as e:
                db.session.rollback()
                flash(f'Error updating task: {str(e)}', 'danger')

        return render_template('task_form.html', action='Edit', task=task, form_data={})

    @app.route('/tasks/<int:task_id>/toggle', methods=['POST'])
    def toggle_task(task_id):
        """
        Cycle task status (Pending -> In Progress -> Completed -> Pending).
        Demonstrates state mutation via POST request to follow REST safety principles.
        """
        task = db.get_or_404(Task, task_id)
        status_cycle = {
            'Pending': 'In Progress',
            'In Progress': 'Completed',
            'Completed': 'Pending'
        }
        old_status = task.status
        task.status = status_cycle.get(task.status, 'Pending')
        task.updated_at = get_utc_now()

        db.session.commit()
        flash(f'Status changed from "{old_status}" to "{task.status}"', 'info')
        return redirect(request.referrer or url_for('index'))

    @app.route('/tasks/<int:task_id>/delete', methods=['POST'])
    def delete_task(task_id):
        """
        Delete a task record.
        Demonstrates safe deletion requiring POST request to avoid CSRF/crawler issues.
        """
        task = db.get_or_404(Task, task_id)
        title = task.title
        try:
            db.session.delete(task)
            db.session.commit()
            flash(f'Task "{title}" was deleted.', 'warning')
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to delete task: {str(e)}', 'danger')

        return redirect(url_for('index'))

    @app.route('/tasks/clear-completed', methods=['POST'])
    def clear_completed():
        """Bulk delete all completed tasks."""
        try:
            completed_tasks = db.session.scalars(db.select(Task).filter_by(status='Completed')).all()
            count = len(completed_tasks)
            for t in completed_tasks:
                db.session.delete(t)
            db.session.commit()
            flash(f'Cleared {count} completed task(s)!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to clear completed tasks: {str(e)}', 'danger')

        return redirect(url_for('index'))

    # -------------------------------------------------------------
    # EXTRA DEMO FEATURES: REST API JSON Endpoint & CSV Export
    # -------------------------------------------------------------

    @app.route('/api/tasks', methods=['GET'])
    def api_get_tasks():
        """
        RESTful API endpoint returning all tasks as JSON.
        Demonstrates Flask serialization and API integration capabilities.
        """
        tasks = db.session.scalars(db.select(Task).order_by(Task.created_at.desc())).all()
        return jsonify({
            'status': 'success',
            'count': len(tasks),
            'tasks': [t.to_dict() for t in tasks]
        })

    @app.route('/export/csv', methods=['GET'])
    def export_csv():
        """
        Export tasks to a downloadable CSV file.
        Demonstrates streaming HTTP responses and dynamic headers in Flask.
        """
        tasks = db.session.scalars(db.select(Task).order_by(Task.created_at.desc())).all()
        output = io.StringIO()
        writer = csv.writer(output)

        # Header row
        writer.writerow(['ID', 'Title', 'Description', 'Category', 'Priority', 'Status', 'Due Date', 'Created At'])

        for t in tasks:
            writer.writerow([
                t.id,
                t.title,
                t.description or '',
                t.category,
                t.priority,
                t.status,
                t.due_date.isoformat() if t.due_date else '',
                t.created_at.strftime('%Y-%m-%d %H:%M:%S') if t.created_at else ''
            ])

        response = Response(output.getvalue(), mimetype='text/csv')
        response.headers['Content-Disposition'] = 'attachment; filename=tasks_export.csv'
        return response

    # -------------------------------------------------------------
    # ERROR HANDLERS
    # -------------------------------------------------------------

    @app.errorhandler(404)
    def page_not_found(e):
        """Custom 404 handler for missing resources."""
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        """Custom 500 handler for unexpected server exceptions."""
        return render_template('404.html', error_code=500, error_message="Internal Server Error"), 500

    return app


def seed_sample_data():
    """Seeds rich, realistic initial tasks if the database is brand new."""
    if db.session.scalar(db.select(Task)) is None:
        today = date.today()
        sample_tasks = [
            Task(
                title="Prepare Flask Backend Architecture for Technical Interview",
                description="Review Flask application factory pattern, Jinja2 inheritance, SQLAlchemy ORM queries, and RESTful routing conventions.",
                category="Interview Prep",
                priority="Urgent",
                status="In Progress",
                due_date=today + timedelta(days=1)
            ),
            Task(
                title="Design Clean Bootstrap 5 Responsive Dashboard UI",
                description="Implement modern KPI metric cards, intuitive search/filter toolbar, dynamic status badges, and mobile-responsive layouts.",
                category="Frontend",
                priority="High",
                status="Completed",
                due_date=today - timedelta(days=1)
            ),
            Task(
                title="Configure SQLite & Flask-SQLAlchemy Database Models",
                description="Build relational tables with field validation, date fields, custom helper properties, and dictionary serialization for REST API endpoints.",
                category="Database",
                priority="High",
                status="Completed",
                due_date=today
            ),
            Task(
                title="Implement GET & POST Form Handling with Flash Messages",
                description="Handle form submissions, sanitize input, validate data on both client and server side, and display dismissal alert notifications.",
                category="Backend",
                priority="Medium",
                status="Completed",
                due_date=today + timedelta(days=2)
            ),
            Task(
                title="Deploy Web App to Free Cloud Hosting (Render / PythonAnywhere)",
                description="Set up requirements.txt, Procfile, wsgi.py entry point, and test production deployment with live demo URL.",
                category="DevOps",
                priority="Medium",
                status="Pending",
                due_date=today + timedelta(days=4)
            ),
            Task(
                title="Review Python Data Structures and Algorithmic Complexity",
                description="Practice dictionary hashing, sets, list comprehensions, and generator functions for standard interview rounds.",
                category="Study",
                priority="Low",
                status="Pending",
                due_date=today + timedelta(days=7)
            ),
        ]
        db.session.add_all(sample_tasks)
        db.session.commit()


# Create application instance for development and WSGI servers
app = create_app()

if __name__ == '__main__':
    # Running on 127.0.0.1:5000 with debug enabled for local development
    app.run(debug=True, host='127.0.0.1', port=5000)
