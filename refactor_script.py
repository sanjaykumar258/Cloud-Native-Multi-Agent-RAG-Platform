import os
import glob

def refactor_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace root imports with backend imports
    content = content.replace('from agents', 'from backend.agents')
    content = content.replace('import agents', 'import backend.agents')
    
    content = content.replace('from brain', 'from backend.brain')
    content = content.replace('import brain', 'import backend.brain')
    
    content = content.replace('from tools.', 'from backend.tools.')
    content = content.replace('import tools.', 'import backend.tools.')
    
    content = content.replace('from config import', 'from backend.config import')
    content = content.replace('import config', 'import backend.config')
    
    content = content.replace('from llm_provider import', 'from backend.llm_provider import')
    content = content.replace('import llm_provider', 'import backend.llm_provider')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

# Refactor frontend
refactor_file('frontend/app.py')

# Add sys path to frontend/app.py
with open('frontend/app.py', 'r', encoding='utf-8') as f:
    app_code = f.read()
if "sys.path.insert" not in app_code:
    app_code = app_code.replace('import streamlit as st', "import os\nimport sys\nsys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))\nimport streamlit as st")
    with open('frontend/app.py', 'w', encoding='utf-8') as f:
        f.write(app_code)

# Refactor backend
for py_file in glob.glob('backend/**/*.py', recursive=True):
    refactor_file(py_file)

# Refactor tests
for py_file in glob.glob('tests/**/*.py', recursive=True):
    refactor_file(py_file)

# Fix config.py database path
config_path = 'backend/config.py'
with open(config_path, 'r', encoding='utf-8') as f:
    config_code = f.read()
config_code = config_code.replace('"./db/chroma"', '"./database/chroma_db"')
config_code = config_code.replace('"./chroma_db"', '"./database/chroma_db"')
with open(config_path, 'w', encoding='utf-8') as f:
    f.write(config_code)

# Fix cache.py paths
cache_path = 'backend/brain/cache.py'
with open(cache_path, 'r', encoding='utf-8') as f:
    cache_code = f.read()
cache_code = cache_code.replace('".brain_cache"', '"database/.brain_cache"')
with open(cache_path, 'w', encoding='utf-8') as f:
    f.write(cache_code)

print("Refactoring complete.")
