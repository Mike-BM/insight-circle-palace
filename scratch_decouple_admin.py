import os
import shutil
import re

def main():
    # 1. Create admin_app directory structure
    os.makedirs('admin_app/js', exist_ok=True)
    os.makedirs('admin_app/css', exist_ok=True)
    
    # 2. Move files
    if os.path.exists('secure_html/admin.html'):
        shutil.move('secure_html/admin.html', 'admin_app/index.html')
    if os.path.exists('static/js/admin.js'):
        shutil.move('static/js/admin.js', 'admin_app/js/admin.js')
        
    # 3. Create a basic CSS file for admin_app/css/admin.css by extracting core elements from style.css
    # We will just copy style.css as the base so the admin app looks the same
    if os.path.exists('static/css/style.css'):
        shutil.copy('static/css/style.css', 'admin_app/css/style.css')
    
    # 4. Update admin_app/index.html to use relative paths for its own assets, and absolute for API
    if os.path.exists('admin_app/index.html'):
        with open('admin_app/index.html', 'r', encoding='utf-8') as f:
            html = f.read()
        
        # Fix paths in html
        html = html.replace('/static/css/style.css', 'css/style.css')
        html = html.replace('/static/js/admin.js', 'js/admin.js')
        
        # Add API_BASE_URL to admin script
        html = html.replace('<script src="js/admin.js"></script>', '<script>const API_BASE_URL = "https://insight-circle-palace.vercel.app";</script>\n    <script src="js/admin.js"></script>')
        
        # Fontawesome is remote anyway
        html = html.replace('/static/assets/logo.jpg', 'https://insight-circle-palace.vercel.app/static/assets/logo.jpg')
        
        with open('admin_app/index.html', 'w', encoding='utf-8') as f:
            f.write(html)
        
    # 5. Update admin_app/js/admin.js to use API_BASE_URL
    if os.path.exists('admin_app/js/admin.js'):
        with open('admin_app/js/admin.js', 'r', encoding='utf-8') as f:
            js = f.read()
        
        # Replace fetch('/... with fetch(API_BASE_URL + '/...
        js = re.sub(r"fetch\('(/[^']+)'", r"fetch(API_BASE_URL + '\1'", js)
        js = re.sub(r'fetch\("(/[^"]+)"', r'fetch(API_BASE_URL + "\1"', js)
        js = re.sub(r'fetch\(`(/[^`]+)`', r'fetch(API_BASE_URL + `\1`', js)
        
        # Add credentials to all fetch calls in admin.js
        js = js.replace("method: 'GET'", "method: 'GET', credentials: 'include'")
        js = js.replace("method: 'POST',", "method: 'POST', credentials: 'include',")
        js = js.replace("method: 'PUT',", "method: 'PUT', credentials: 'include',")
        js = js.replace("method: 'DELETE'", "method: 'DELETE', credentials: 'include'")
        
        js = re.sub(r"fetch\((API_BASE_URL \+ '[^']+')\)", r"fetch(\1, {credentials: 'include'})", js)
        js = re.sub(r"fetch\((API_BASE_URL \+ `[^`]+`)\)", r"fetch(\1, {credentials: 'include'})", js)
        
        with open('admin_app/js/admin.js', 'w', encoding='utf-8') as f:
            f.write(js)
        
    # 6. Update main.py CORS to allow credentials and wildcard / specific origins
    if os.path.exists('main.py'):
        with open('main.py', 'r', encoding='utf-8') as f:
            main_py = f.read()
            
        cors_replacement = """app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "https://admin-insight-circle.vercel.app", "https://insight-circle-admin.vercel.app", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)"""
        # wait, allow_origins=["*"] with allow_credentials=True is invalid in FastAPI.
        # So we MUST specify explicit origins.
        cors_replacement = """app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "https://admin.insight-circle-palace.vercel.app", "https://insight-circle-admin.vercel.app", "https://insight-circle-palace.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)"""
        main_py = re.sub(r'app\.add_middleware\(\s*CORSMiddleware,.*?allow_headers=\["\*"\],\s*\)', cors_replacement, main_py, flags=re.DOTALL)
        main_py = re.sub(r'@app\.get\("/admin", include_in_schema=False\).*?return FileResponse\("secure_html/admin\.html"\)', '', main_py, flags=re.DOTALL)
        
        with open('main.py', 'w', encoding='utf-8') as f:
            f.write(main_py)
        
    # 7. Update auth.py to set SameSite='none', Secure=True for cross-origin cookies
    auth_file = 'app/routers/auth.py'
    if os.path.exists(auth_file):
        with open(auth_file, 'r', encoding='utf-8') as f:
            auth_py = f.read()
        auth_py = auth_py.replace('response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)',
                                  'response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True, samesite="none", secure=True)')
        with open(auth_file, 'w', encoding='utf-8') as f:
            f.write(auth_py)

if __name__ == '__main__':
    main()
    print("Decoupling complete")
