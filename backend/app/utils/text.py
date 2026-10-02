"""Small, dependency-free text helpers used by search, RAG and the evidence checker."""
import re
import unicodedata

STOPWORDS = set(
    """a about above after again against all also am an and any are aren't as at be because been before being
    below between both but by can could did do does doing down during each either few for from further had has
    have having he her here hers herself him himself his how i if in into is it its itself just let me more most
    my myself no nor not of off on once only or other our ours ourselves out over own same she should so some such
    than that the their theirs them themselves then there these they this those through to too under until up very
    was we were what when where which while who whom why will with would you your yours yourself yourselves
    tell explain describe show give list please summarize summarise what's whats does do say says said discuss
    discussed discusses mention mentioned key main major important factors factor resource resources document
    report paper study this these within across using used use based find found finds learn know
    information info""".split()
)

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:[-'][a-z0-9]+)*")
_SENT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(\[])")


def normalize(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()


def stem(word: str) -> str:
    """Very light suffix stripping — enough to match 'variability'/'variable', 'observations'/'observed'."""
    w = word
    for suf in ("ational", "ization", "ability", "ibility", "ations", "ation", "ments", "ment", "ness", "able", "ible",
                "ities", "ity", "ings", "ing", "ies", "ied", "ers", "er", "ed", "es", "ic", "al", "ly", "s"):
        if len(w) > len(suf) + 3 and w.endswith(suf):
            w = w[: -len(suf)]
            break
    if len(w) > 4 and w.endswith("e"):
        w = w[:-1]
    return w


def tokenize(text: str) -> list[str]:
    toks = []
    for t in _TOKEN_RE.findall(normalize(text)):
        toks.extend(p for p in t.split("-") if p)
    return toks


def content_terms(text: str) -> list[str]:
    """Meaningful terms (no stopwords, len>2), order-preserving and de-duplicated."""
    seen: set[str] = set()
    out: list[str] = []
    for t in tokenize(text):
        if t in STOPWORDS or (len(t) < 3 and not t.isdigit()):
            continue
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def stems(text: str) -> set[str]:
    return {stem(t) for t in content_terms(text)}


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    return [s.strip() for s in _SENT_RE.split(text) if len(s.strip()) > 1]


def numbers_in(text: str) -> set[str]:
    return set(re.findall(r"(?<![\w.])\d+(?:[.,]\d+)?%?", text))


def slugify(text: str, max_len: int = 80) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", normalize(text)).strip("-")
    return s[:max_len].strip("-") or "item"


def truncate_words(text: str, n: int) -> str:
    words = text.split()
    if len(words) <= n:
        return text
    return " ".join(words[:n]).rstrip(",;:") + "…"


def snippet_around(text: str, terms: list[str], width: int = 240) -> str:
    low = normalize(text)
    pos = -1
    for t in terms:
        pos = low.find(t)
        if pos >= 0:
            break
    if pos < 0:
        return truncate_words(text, 40)
    start = max(0, pos - width // 3)
    end = min(len(text), start + width)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    return prefix + text[start:end].strip() + suffix
