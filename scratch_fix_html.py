import os
import re

static_dir = r"c:\Users\brian\Desktop\Brian\insight-circle-palace\static"

script_pattern = re.compile(r"<script>\s*if\s*\(localStorage\.getItem\('insightCircleMember'\)[^<]+</script>", re.DOTALL)

for filename in os.listdir(static_dir):
    if filename.endswith(".html"):
        filepath = os.path.join(static_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Remove the inline localStorage script
        new_content = script_pattern.sub("", content)
        
        # Replace href="/static/join.html" with href="/static/register.html" where appropriate.
        # But we don't want to replace if it's the actual intake form link, but the intake form link should only be seen if logged in anyway.
        # So we'll replace href="/static/join.html" with href="/static/register.html"
        # and href="join.html" with href="register.html"
        new_content = new_content.replace('href="/static/join.html"', 'href="/static/register.html"')
        new_content = new_content.replace('href="join.html"', 'href="register.html"')
        new_content = new_content.replace("href='/static/join.html", "href='/static/register.html")
        
        if content != new_content:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"Updated {filename}")
