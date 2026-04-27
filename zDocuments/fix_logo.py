import re, base64, os

base_dir = r'd:\Projects\Buteforce\Projects\Lead Outreacher'

# Read real icon (the angular F mark)
with open(os.path.join(base_dir, 'Untitled design (3).png'), 'rb') as f:
    icon_b64 = base64.b64encode(f.read()).decode('ascii')

# Read wordmark PNG (high-res 4x version)
with open(os.path.join(base_dir, 'ButeForce Word mark@4x.png'), 'rb') as f:
    wordmark_b64 = base64.b64encode(f.read()).decode('ascii')

print(f"Icon b64 length: {len(icon_b64)}")
print(f"Wordmark b64 length: {len(wordmark_b64)}")

# Read the HTML
with open(os.path.join(base_dir, 'buteforce_email_templates.html'), 'r', encoding='utf-8') as f:
    html = f.read()

# Count existing logo bars
found = html.count('<div class="email-logo-bar">')
print(f"Logo bars found: {found}")

def make_new_logo_bar():
    return (
        '<div class="email-logo-bar">\n'
        '              <div class="email-logo-mark">'
        f'<img src="data:image/png;base64,{icon_b64}" alt="Buteforce" '
        'style="width:36px;height:36px;object-fit:contain;display:block;border-radius:4px;">'
        '</div>\n'
        '              <div class="email-logo-text">'
        f'<img src="data:image/png;base64,{wordmark_b64}" alt="ButeForce" '
        'style="height:18px;object-fit:contain;display:block;">'
        '</div>\n'
        '            </div>'
    )

# Replace logo bar blocks using regex (greedy enough to capture both inner divs)
logo_bar_pattern = re.compile(
    r'<div class="email-logo-bar">.*?</div>\s*<div class="email-logo-text">.*?</div>\s*</div>',
    re.DOTALL
)

matches_found = logo_bar_pattern.findall(html)
print(f"Logo bar pattern matches: {len(matches_found)}")

new_html = logo_bar_pattern.sub(make_new_logo_bar(), html)

# Fix page header logo text -> wordmark image (inverted because header is dark)
old_header = '<div class="page-header-logo">BUTE<span>FORCE</span></div>'
new_header = (
    '<div class="page-header-logo" style="display:flex;align-items:center;">'
    f'<img src="data:image/png;base64,{wordmark_b64}" alt="ButeForce" '
    'style="height:22px;object-fit:contain;filter:invert(1);display:block;">'
    '</div>'
)
new_html = new_html.replace(old_header, new_header)

# Write back
with open(os.path.join(base_dir, 'buteforce_email_templates.html'), 'w', encoding='utf-8') as f:
    f.write(new_html)

print("Done! HTML updated with real ButeForce logos.")
