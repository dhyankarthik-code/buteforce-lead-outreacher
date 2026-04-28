"""
Buteforce HTML email template.
Converts plain-text body → branded HTML multipart email.
"""

import html
import re


def _text_to_html(text: str) -> str:
    """Convert plain text body to HTML paragraphs, preserving structure."""
    # Escape HTML entities
    escaped = html.escape(text)

    # Split on blank lines → paragraphs
    blocks = re.split(r"\n\s*\n", escaped.strip())

    parts = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue

        lines = block.split("\n")

        # Numbered list block (1. ... 2. ... )
        if re.match(r"^\d+\.", lines[0]):
            items = []
            current = ""
            for line in lines:
                if re.match(r"^\d+\.", line.strip()):
                    if current:
                        items.append(current.strip())
                    current = re.sub(r"^\d+\.\s*", "", line.strip())
                else:
                    current += " " + line.strip()
            if current:
                items.append(current.strip())

            li_html = "".join(
                f'<li style="margin-bottom:6px;color:#1a1a1a;">{_linkify(it)}</li>'
                for it in items
            )
            parts.append(
                f'<ol style="margin:0 0 16px 0;padding-left:20px;font-size:14px;line-height:1.75;">'
                f"{li_html}</ol>"
            )
        else:
            # Regular paragraph — join lines, convert inline newlines to <br>
            inner = "<br>".join(_linkify(ln) for ln in lines)
            parts.append(
                f'<p style="margin:0 0 16px 0;font-size:14px;line-height:1.75;color:#1a1a1a;">'
                f"{inner}</p>"
            )

    return "\n".join(parts)


def _linkify(text: str) -> str:
    """Turn bare URLs into clickable links (already HTML-escaped input)."""
    # Match http(s):// URLs that aren't already inside an href
    return re.sub(
        r'(https?://[^\s&lt;&gt;"]+)',
        r'<a href="\1" style="color:#0a0a0a;font-weight:600;">\1</a>',
        text,
    )


_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<meta name="color-scheme" content="light">
<!--[if mso]><xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml><![endif]-->
</head>
<body style="margin:0;padding:0;background:#f5f6f8;-webkit-text-size-adjust:100%;mso-line-height-rule:exactly;">
<table width="100%" cellpadding="0" cellspacing="0" role="presentation"
       style="background:#f5f6f8;padding:36px 16px;">
  <tr>
    <td align="center">

      <table width="600" cellpadding="0" cellspacing="0" role="presentation"
             style="max-width:600px;width:100%;background:#ffffff;border-radius:8px;
                    border:1px solid #e5e7eb;overflow:hidden;">

        <!-- Yellow accent bar -->
        <tr>
          <td style="background:#FFFC01;height:3px;font-size:0;line-height:3px;">&nbsp;</td>
        </tr>

        <!-- Brand header -->
        <tr>
          <td style="padding:18px 32px;border-bottom:1px solid #f0f1f3;">
            <span style="font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;
                         font-size:16px;font-weight:800;color:#0a0a0a;letter-spacing:-0.02em;">
              Buteforce
            </span>
            <span style="font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;
                         font-size:11px;color:#9ca3af;font-weight:500;margin-left:8px;
                         letter-spacing:0.02em;">
              Precision AI Systems
            </span>
          </td>
        </tr>

        <!-- Email body -->
        <tr>
          <td style="padding:28px 32px 8px;
                     font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
            {BODY_HTML}
          </td>
        </tr>

        <!-- Signature -->
        <tr>
          <td style="padding:0 32px 28px;
                     font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
            <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
              <tr>
                <td style="border-top:1px solid #e5e7eb;padding-top:18px;">
                  <div style="font-size:13px;font-weight:700;color:#0a0a0a;
                               margin-bottom:3px;letter-spacing:-0.01em;">
                    Dhyaneshwaran Karthikeyan
                  </div>
                  <div style="font-size:12px;color:#6b7280;margin-bottom:10px;">
                    Founder &nbsp;·&nbsp;
                    <span style="color:#0a0a0a;font-weight:600;">
                      Buteforce Precision AI Systems
                    </span>
                  </div>
                  <div style="font-size:11px;color:#9ca3af;line-height:1.6;">
                    <a href="https://buteforce.com"
                       style="color:#0a0a0a;text-decoration:none;font-weight:700;">
                      buteforce.com
                    </a>
                    &nbsp;&middot;&nbsp;
                    <a href="https://youtube.com/@Shree_Dhyan"
                       style="color:#6b7280;text-decoration:none;">
                      youtube.com/@Shree_Dhyan
                    </a>
                    &nbsp;&middot;&nbsp;
                    <a href="mailto:admin@buteforce.com"
                       style="color:#6b7280;text-decoration:none;">
                      admin@buteforce.com
                    </a>
                  </div>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#f9fafb;padding:12px 32px;border-top:1px solid #f0f1f3;
                     border-radius:0 0 8px 8px;">
            <p style="margin:0;font-size:10px;color:#9ca3af;line-height:1.5;
                      font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;
                      font-style:italic;">
              No consultants. No pilot projects. Working systems.
            </p>
          </td>
        </tr>

      </table>
    </td>
  </tr>
</table>
</body>
</html>
"""


def build_html_email(body: str) -> str:
    """Wrap plain-text body in the Buteforce HTML email template."""
    body_html = _text_to_html(body)
    return _TEMPLATE.replace("{BODY_HTML}", body_html)
