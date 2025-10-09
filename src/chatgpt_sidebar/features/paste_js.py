"""JavaScript code builders for paste functionality."""

import json


def build_paste_js(b64_image: str) -> str:
    """Build JavaScript to inject image via synthetic paste event.
    
    Args:
        b64_image: Base64-encoded image data
        
    Returns:
        str: JavaScript code to paste the image
    """
    b64q = json.dumps(b64_image)  # Safe string literal
    return f"""
    (function(){{
      const composer = document.querySelector(
        '[data-testid="composer"] textarea, [contenteditable="true"][data-testid="textbox"], div[contenteditable="true"]'
      );
      if (!composer) return false;
      
      function base64ToUint8Array(b64){{
        const binary = atob(b64);
        const len = binary.length;
        const bytes = new Uint8Array(len);
        for (let i = 0; i < len; i++) bytes[i] = binary.charCodeAt(i);
        return bytes;
      }}
      
      const bytes = base64ToUint8Array({b64q});
      const blob = new Blob([bytes], {{ type: 'image/png' }});
      const file = new File([blob], 'screenshot.png', {{ type: 'image/png' }});
      const dt = new DataTransfer();
      dt.items.add(file);
      
      let evt;
      try {{
        evt = new ClipboardEvent('paste', {{ 
          clipboardData: dt, 
          bubbles: true, 
          cancelable: true 
        }});
      }} catch (e) {{
        evt = new Event('paste', {{ bubbles: true, cancelable: true }});
        try {{ 
          Object.defineProperty(evt, 'clipboardData', {{ value: dt }}); 
        }} catch(e2) {{}}
      }}
      
      composer.focus();
      return composer.dispatchEvent(evt);
    }})();"""

