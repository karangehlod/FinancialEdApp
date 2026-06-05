from typing import Optional
import bleach

ALLOWED_TAGS = ["b", "i", "u", "a", "p", "ul", "li", "strong", "em"]
ALLOWED_ATTRS = {
    'a': ['href', 'title', 'rel', 'target']
}


def clean_html(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    return bleach.clean(value, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)


def clean_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    return bleach.clean(value, tags=[], strip=True)
