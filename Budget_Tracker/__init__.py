"""
Alias module for deployment compatibility when platforms (like Render)
auto-infer wsgi path from repository name 'budget_tracker'.
"""
from config.wsgi import application  # noqa: F401
