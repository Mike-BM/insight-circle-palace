import glob

html_files = glob.glob(r'c:\Users\brian\Desktop\Brian\insight-circle-palace\static\*.html')

old_logo = '<i class="fa-solid fa-circle-nodes"></i> Insight Circle'
new_logo = '<img src="/static/assets/logo.jpg" alt="Insight Circle Logo" style="height: 40px; width: auto; vertical-align: middle;">'

for fpath in html_files:
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if old_logo in content:
        content = content.replace(old_logo, new_logo)
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {fpath}")
