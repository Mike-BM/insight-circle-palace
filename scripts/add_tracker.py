import os
import glob

html_files = glob.glob('static/*.html')
for f in html_files:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    if 'tracker.js' not in content:
        content = content.replace('</body>', '    <script src="/static/js/tracker.js"></script>\n</body>')
        with open(f, 'w', encoding='utf-8') as file:
            file.write(content)
        print(f"Added tracker to {f}")
