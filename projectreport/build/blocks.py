"""Block constructors for the report content. Text may use **bold**, *italic* and `code`, and the
placeholders {fig:key}, {tab:key} and {ref:key1,key2}, which build_report.py resolves."""


def H1(label, title):
    return ("h1", label, title)


def H2(title):
    return ("h2", title)


def H3(title):
    return ("h3", title)


def P(text):
    return ("p", " ".join(text.split()))


def NOTE(text):
    return ("note", " ".join(text.split()))


def B(*items):
    return ("bul", [" ".join(i.split()) for i in items])


def N(*items):
    return ("num", [" ".join(i.split()) for i in items])


def F(key, file, caption, width=6.2):
    return ("fig", key, file, " ".join(caption.split()), width)


def T(key, caption, header, rows, widths):
    return ("tab", key, " ".join(caption.split()), header, rows, widths)


def CODE(title, text):
    return ("code", title, text)


def REFS():
    return ("refs",)
