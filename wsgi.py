"""
WSGI entry point for production servers such as Gunicorn, uWSGI, or Render.
"""
from app import app

if __name__ == "__main__":
    app.run()
