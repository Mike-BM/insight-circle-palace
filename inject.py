import os
import glob

html_files = glob.glob('c:/Users/brian/Desktop/Brian/static/*.html')
script_tag = '<script src="/static/js/gatekeeper.js"></script>'

for file in html_files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if script_tag not in content:
        # replace the last occurrence of </body>
        if '</body>' in content:
            idx = content.rfind('</body>')
            new_content = content[:idx] + f'    {script_tag}\n</body>' + content[idx+7:]
            with open(file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Added to {file}")
