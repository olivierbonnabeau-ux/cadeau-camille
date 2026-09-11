import os
from jinja2 import FileSystemLoader
from app import app

# Force Render/Gunicorn to resolve the template directory from the repository,
# independently of the process working directory.
app.template_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app.jinja_loader = FileSystemLoader(app.template_folder)
