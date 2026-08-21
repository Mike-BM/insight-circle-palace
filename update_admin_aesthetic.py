import re

with open('secure_html/admin.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update CSS variables (premium dark mode)
content = re.sub(
    r':root \{.*?\n\s+\}', 
    ''':root {
            --bg-main: #050505;
            --bg-sidebar: rgba(15, 15, 20, 0.6);
            --bg-card: rgba(20, 20, 25, 0.4);
            --border: rgba(255, 255, 255, 0.08);
            --primary: #c084fc;
            --primary-glow: rgba(192, 132, 252, 0.4);
            --secondary: #ec4899;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --danger: #ef4444;
            --success: #10b981;
        }''', 
    content, 
    flags=re.DOTALL
)

# 2. Add body background glowing orbs
body_pattern = r'body \{ \n            display: flex; \n            min-height: 100vh; \n            margin: 0; \n            font-family: \'Inter\', sans-serif; \n            background-color: var\(--bg-main\); \n                        color: var\(--text-main\);\n        \}'
new_body = '''body { 
            display: flex; 
            min-height: 100vh; 
            margin: 0; 
            font-family: 'Inter', sans-serif; 
            background-color: var(--bg-main);
            background-image: radial-gradient(circle at 15% 50%, rgba(192, 132, 252, 0.15), transparent 25%), radial-gradient(circle at 85% 30%, rgba(236, 72, 153, 0.15), transparent 25%);
            color: var(--text-main);
        }'''
# use regex to replace body
content = re.sub(r'body\s*\{[^}]+\}', new_body, content, count=1)

# 3. Add glassmorphism (backdrop-filter)
# Sidebar
content = re.sub(r'\.sidebar\s*\{([^}]+)\}', r'.sidebar {\1    backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);\n}', content)
# Cards & Datatables
content = re.sub(r'\.stat-card\s*\{([^}]+)\}', r'.stat-card {\1    backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);\n}', content)
content = re.sub(r'\.datatable-wrapper\s*\{([^}]+)\}', r'.datatable-wrapper {\1    backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);\n}', content)
# Modals
content = re.sub(r'\.modal-content\s*\{([^}]+)\}', r'.modal-content {\1    backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);\n}', content)


# 4. Fix Sidebar active link gradient
content = content.replace('background: rgba(255, 215, 0, 0.1);', 'background: linear-gradient(135deg, rgba(192, 132, 252, 0.2), rgba(236, 72, 153, 0.1));')

# 5. Fix btn-primary gradient and color
content = re.sub(
    r'\.btn-primary\s*\{[^}]+\}',
    '''.btn-primary { 
            background: linear-gradient(135deg, var(--primary), var(--secondary)); 
            color: #fff; 
            box-shadow: 0 4px 15px var(--primary-glow); 
            border: 1px solid rgba(255,255,255,0.1);
        }''',
    content
)

content = re.sub(
    r'\.btn-primary:hover\s*\{[^}]+\}',
    '''.btn-primary:hover { 
            transform: translateY(-2px); 
            box-shadow: 0 6px 20px rgba(236, 72, 153, 0.4); 
            filter: brightness(1.1);
        }''',
    content
)

# 6. Fix stat-card header gradient line
content = content.replace('background: var(--primary);', 'background: linear-gradient(90deg, var(--primary), var(--secondary));')

# 7. Fix modal content background is already handled by root vars, but ensure no fixed dark colors
content = content.replace('background: #131e3d;', 'background: var(--bg-card);')

# 8. Fix stat-value gradient text
content = re.sub(
    r'\.stat-value\s*\{[^}]+\}',
    '''.stat-value { 
            font-size: 3rem; 
            font-weight: 700; 
            background: linear-gradient(135deg, #fff, #a5b4fc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-top: 1rem; 
            font-family: 'Outfit', sans-serif;
        }''',
    content
)

# 9. Fix sidebar header h3 gradient
content = re.sub(
    r'\.sidebar-header h3\s*\{[^}]+\}',
    '''.sidebar-header h3 { 
            font-family: 'Outfit', sans-serif; 
            margin: 0; 
            font-size: 1.2rem;
            font-weight: 600;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }''',
    content
)

# 10. Fix badge admin
content = content.replace('background: rgba(255, 215, 0, 0.15); color: var(--primary); border: 1px solid rgba(255, 215, 0, 0.3);', 'background: rgba(192, 132, 252, 0.2); color: #c4b5fd; border: 1px solid rgba(192, 132, 252, 0.3);')

with open('secure_html/admin.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated CSS in secure_html/admin.html")
