# No sqlalchemy import: text is a local function, plus ui.text -> must NOT fire.
def text(s):
    return s


class ui:
    @staticmethod
    def text(s):
        return s


def probes(conn, name, x):
    # ok: backend-craft.python.sql-text-fstring
    text(f"Hello {name}")
    # ok: backend-craft.python.sql-text-fstring
    ui.text(f"Hello {name}")
    # ok: backend-craft.python.sql-text-fstring
    conn.execute(text(f"X {x}"))
