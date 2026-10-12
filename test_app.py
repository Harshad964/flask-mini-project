import pytest
from app import create_app
from models import db, Task

@pytest.fixture
def test_client():
    """Sets up an isolated in-memory SQLite database and test client."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()

def test_index_page(test_client):
    """Verifies that the dashboard loads successfully with status code 200."""
    response = test_client.get('/')
    assert response.status_code == 200
    assert b'TaskMaster' in response.data
    assert b'Dashboard' in response.data

def test_create_task(test_client):
    """Verifies creating a new task via POST request."""
    response = test_client.post('/tasks/new', data={
        'title': 'Test Flask CRUD Functionality',
        'description': 'Integration testing with pytest',
        'category': 'Backend',
        'priority': 'Urgent',
        'status': 'Pending',
        'due_date': '2026-12-31'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'Test Flask CRUD Functionality' in response.data
    assert b'created successfully!' in response.data

def test_create_task_validation_failure(test_client):
    """Verifies that submitting empty title fails with validation flash message."""
    response = test_client.post('/tasks/new', data={
        'title': '',
        'category': 'Backend'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'Task title is required!' in response.data

def test_task_detail_and_edit(test_client):
    """Verifies reading task details and updating fields."""
    # Create task
    test_client.post('/tasks/new', data={
        'title': 'Original Task Title',
        'category': 'General',
        'priority': 'Medium',
        'status': 'Pending'
    }, follow_redirects=True)

    # Get created task
    task = db.session.scalar(db.select(Task).filter_by(title='Original Task Title'))
    assert task is not None

    # View details
    detail_res = test_client.get(f'/tasks/{task.id}')
    assert detail_res.status_code == 200
    assert b'Original Task Title' in detail_res.data

    # Edit task
    edit_res = test_client.post(f'/tasks/{task.id}/edit', data={
        'title': 'Updated Task Title',
        'category': 'Updated Category',
        'priority': 'High',
        'status': 'In Progress'
    }, follow_redirects=True)

    assert edit_res.status_code == 200
    assert b'Updated Task Title' in edit_res.data

def test_toggle_task_status(test_client):
    """Verifies status cycling: Pending -> In Progress -> Completed."""
    test_client.post('/tasks/new', data={
        'title': 'Toggle Test Task',
        'status': 'Pending'
    }, follow_redirects=True)

    task = db.session.scalar(db.select(Task).filter_by(title='Toggle Test Task'))
    assert task.status == 'Pending'

    # Toggle to In Progress
    test_client.post(f'/tasks/{task.id}/toggle', follow_redirects=True)
    db.session.refresh(task)
    assert task.status == 'In Progress'

    # Toggle to Completed
    test_client.post(f'/tasks/{task.id}/toggle', follow_redirects=True)
    db.session.refresh(task)
    assert task.status == 'Completed'

def test_delete_task(test_client):
    """Verifies deleting a task via POST."""
    test_client.post('/tasks/new', data={
        'title': 'Task To Delete',
        'status': 'Pending'
    }, follow_redirects=True)

    task = db.session.scalar(db.select(Task).filter_by(title='Task To Delete'))
    assert task is not None

    delete_res = test_client.post(f'/tasks/{task.id}/delete', follow_redirects=True)
    assert delete_res.status_code == 200
    assert db.session.scalar(db.select(Task).filter_by(title='Task To Delete')) is None

def test_api_endpoint(test_client):
    """Verifies JSON REST API response."""
    response = test_client.get('/api/tasks')
    assert response.status_code == 200
    assert response.is_json
    data = response.get_json()
    assert data['status'] == 'success'
    assert isinstance(data['tasks'], list)

def test_export_csv(test_client):
    """Verifies CSV export endpoint."""
    response = test_client.get('/export/csv')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'text/csv; charset=utf-8'
    assert b'Title' in response.data

def test_404_error_page(test_client):
    """Verifies custom 404 error handling."""
    response = test_client.get('/nonexistent-page-url')
    assert response.status_code == 404
    assert b'Page Not Found' in response.data
