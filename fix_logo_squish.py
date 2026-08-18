import glob
import os

html_files = glob.glob(r'c:\Users\brian\Desktop\Brian\insight-circle-palace\static\*.html')

# We'll just replace the style tags to ensure flex-shrink: 0 and object-fit: contain are present.
for fpath in html_files:
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # login.html
    content = content.replace(
        'style="height: 52px; width: auto; border-radius: 50%;"',
        'style="height: 52px; width: 52px; object-fit: contain; flex-shrink: 0; border-radius: 50%;"'
    )
    
    # all other pages
    content = content.replace(
        'style="height: 40px; width: auto; vertical-align: middle;"',
        'style="height: 40px; width: 40px; object-fit: contain; flex-shrink: 0; vertical-align: middle; border-radius: 50%;"'
    )
    
    # register.html, join.html, onboard.html
    content = content.replace(
        'style="height: 40px; width: auto; border-radius: 50%;"',
        'style="height: 40px; width: 40px; object-fit: contain; flex-shrink: 0; border-radius: 50%;"'
    )

    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(content)
        
print("Logo squishing fixed in all HTML files.")
