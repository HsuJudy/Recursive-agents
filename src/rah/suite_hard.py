# agent: claude-code  2026-10-17
"""12 harder invented tasks (families edge, errors, format), written because the builder may ace suite_data.

Per family: 2 train, 1 val, 1 test. Every requirement is stated once in the spec; each one is easy to miss.
Nothing here is copied from a public benchmark or from suite_data.
"""
from __future__ import annotations

from .suite import Task
from .suite_data import T, blk, eq, raises

HARD_TASKS: list[Task] = [
    # ---- edge ---------------------------------------------------------------------------------
    T("H1", "edge", "train",
      "Write `merge_intervals(intervals)`. intervals is a list of (start, end) tuples of ints. "
      "Return a new list of tuples where overlapping intervals are merged. "
      "Intervals that only touch (one ends exactly where the next starts) also count as overlapping and are merged. "
      "If an interval has start greater than end, treat it as (end, start). "
      "The result is sorted by start, and the input list may be unsorted and must not be modified.",
      "merge_intervals",
      [eq("merge_intervals([(1,3),(2,6),(8,10)])", "[(1,6),(8,10)]"),
       eq("merge_intervals([(1,2),(2,3)])", "[(1,3)]"),
       eq("merge_intervals([])", "[]"),
       eq("merge_intervals([(5,1)])", "[(1,5)]"),
       eq("merge_intervals([(1,10),(2,3)])", "[(1,10)]"),
       eq("merge_intervals([(8,9),(1,2),(2,4)])", "[(1,4),(8,9)]"),
       blk("xs = [(5,6),(1,2)]", "orig = list(xs)", "merge_intervals(xs)", "assert xs == orig")],
      """
def merge_intervals(intervals):
    items = sorted((min(a, b), max(a, b)) for a, b in intervals)
    out = []
    for s, e in items:
        if out and s <= out[-1][1]:
            if e > out[-1][1]:
                out[-1] = (out[-1][0], e)
        else:
            out.append((s, e))
    return out
"""),
    T("H2", "edge", "train",
      "Write `rotate_right(items, k)`. Return a new list with the items moved k places to the right, "
      "wrapping around, so rotate_right([1,2,3,4,5], 2) is [4,5,1,2,3]. "
      "k may be zero, negative (which rotates left) or larger than the length of the list. "
      "An empty list gives []. The result must always be a new list object, even when nothing moves, "
      "and the input must not be modified.",
      "rotate_right",
      [eq("rotate_right([1,2,3,4,5], 2)", "[4,5,1,2,3]"),
       eq("rotate_right([1,2,3,4,5], 7)", "[4,5,1,2,3]"),
       eq("rotate_right([1,2,3,4,5], -1)", "[2,3,4,5,1]"),
       eq("rotate_right([], 3)", "[]"),
       eq("rotate_right([1,2,3], 0)", "[1,2,3]"),
       eq("rotate_right([1,2,3], -4)", "[2,3,1]"),
       blk("xs = [1,2,3]", "r = rotate_right(xs, 3)", "assert r == [1,2,3] and r is not xs"),
       blk("xs = [1,2,3]", "rotate_right(xs, 1)", "assert xs == [1,2,3]")],
      """
def rotate_right(items, k):
    n = len(items)
    if n == 0:
        return []
    k %= n
    return items[n - k:] + items[:n - k]
"""),
    T("H3", "edge", "val",
      "Write `trim_mean(nums, pct)`. Sort a copy of nums, then drop the lowest and the highest "
      "k values each, where k = len(nums) * pct // 100 (integer division). "
      "Return the mean of the remaining values as a float. "
      "pct is an int from 0 to 49. An empty list gives 0.0. The input must not be modified.",
      "trim_mean",
      [eq("trim_mean([1,2,3,4,100], 20)", "3.0"),
       eq("trim_mean([], 10)", "0.0"),
       eq("trim_mean([4,2,6], 0)", "4.0"),
       eq("trim_mean([1,2,3], 10)", "2.0"),
       eq("trim_mean([5], 49)", "5.0"),
       eq("trim_mean([9,1,5,3,7,100,0,2,4,6], 10)", "4.625"),
       eq("trim_mean([1,2,3,4], 25)", "2.5"),
       blk("xs = [3,1,2]", "trim_mean(xs, 40)", "assert xs == [3,1,2]")],
      """
def trim_mean(nums, pct):
    if not nums:
        return 0.0
    s = sorted(nums)
    k = len(s) * pct // 100
    kept = s[k:len(s) - k]
    return sum(kept) / len(kept)
"""),
    T("H4", "edge", "test",
      "Write `split_evenly(items, parts)`. Split the list into exactly `parts` consecutive lists, keeping order. "
      "The sizes may differ by at most 1, and the larger lists come first, so splitting 7 items into 3 parts "
      "gives sizes 3, 2, 2. If there are fewer items than parts, the extra lists at the end are empty. "
      "If parts is less than 1 return []. The input must not be modified.",
      "split_evenly",
      [eq("split_evenly([1,2,3,4,5,6,7], 3)", "[[1,2,3],[4,5],[6,7]]"),
       eq("split_evenly([1,2], 4)", "[[1],[2],[],[]]"),
       eq("split_evenly([], 2)", "[[],[]]"),
       eq("split_evenly([1,2,3], 0)", "[]"),
       eq("split_evenly([1,2,3], -2)", "[]"),
       eq("split_evenly([1,2,3], 1)", "[[1,2,3]]"),
       eq("split_evenly([1,2,3,4], 2)", "[[1,2],[3,4]]"),
       blk("xs = [1,2,3]", "split_evenly(xs, 2)", "assert xs == [1,2,3]")],
      """
def split_evenly(items, parts):
    if parts < 1:
        return []
    q, r = divmod(len(items), parts)
    out = []
    i = 0
    for p in range(parts):
        size = q + (1 if p < r else 0)
        out.append(list(items[i:i + size]))
        i += size
    return out
"""),

    # ---- errors -------------------------------------------------------------------------------
    T("H5", "errors", "train",
      "Write `parse_port(value)`. value may be an int or a string. Check in this order: "
      "(1) if value is a bool or is neither an int nor a str, raise TypeError('port must be int or str'); "
      "(2) if value is a str, strip whitespace from it, and if what is left is not a non-empty run of the "
      "ASCII digits 0-9 raise ValueError('port must be digits'), otherwise convert it to an int; "
      "(3) if the number is below 1 or above 65535 raise ValueError('port out of range'). "
      "Otherwise return the int.",
      "parse_port",
      [eq("parse_port(' 8080 ')", "8080"), eq("parse_port(443)", "443"), eq("parse_port('08')", "8"),
       raises("parse_port(True)", "TypeError", "port must be int or str"),
       raises("parse_port(3.5)", "TypeError", "port must be int or str"),
       raises("parse_port('http')", "ValueError", "port must be digits"),
       raises("parse_port('')", "ValueError", "port must be digits"),
       raises("parse_port('-5')", "ValueError", "port must be digits"),
       raises("parse_port('0')", "ValueError", "port out of range"),
       raises("parse_port(65536)", "ValueError", "port out of range"),
       eq("parse_port('65535')", "65535")],
      """
def parse_port(value):
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise TypeError("port must be int or str")
    if isinstance(value, str):
        s = value.strip()
        if not s or not all(c in "0123456789" for c in s):
            raise ValueError("port must be digits")
        value = int(s)
    if value < 1 or value > 65535:
        raise ValueError("port out of range")
    return value
"""),
    T("H6", "errors", "train",
      "Write `run_ops(start, ops)`. ops is a list of (name, number) tuples; name is one of 'add', 'sub', 'mul', "
      "'div'. Apply them one after another to start and return the final value; 'div' is true division. "
      "Before applying anything, check every name first: if any name is unknown raise "
      "ValueError('unknown op: NAME') using the first unknown name in list order. "
      "Then, while applying, if a 'div' has number 0 raise ZeroDivisionError('divide by zero at step I') "
      "where I is the 0-based position of that tuple in ops.",
      "run_ops",
      [eq("run_ops(10, [('add', 5), ('mul', 2)])", "30"),
       eq("run_ops(7, [('div', 2)])", "3.5"),
       eq("run_ops(5, [])", "5"),
       eq("run_ops(1, [('sub', 4)])", "-3"),
       raises("run_ops(1, [('pow', 2)])", "ValueError", "unknown op: pow"),
       raises("run_ops(1, [('add', 1), ('div', 0)])", "ZeroDivisionError", "divide by zero at step 1"),
       raises("run_ops(1, [('div', 0), ('pow', 1)])", "ValueError", "unknown op: pow"),
       raises("run_ops(1, [('mod', 1), ('pow', 1)])", "ValueError", "unknown op: mod"),
       raises("run_ops(9, [('mul', 0), ('add', 1), ('div', 0)])", "ZeroDivisionError", "divide by zero at step 2")],
      """
def run_ops(start, ops):
    known = ("add", "sub", "mul", "div")
    for name, _ in ops:
        if name not in known:
            raise ValueError("unknown op: " + name)
    value = start
    for i, (name, n) in enumerate(ops):
        if name == "add":
            value += n
        elif name == "sub":
            value -= n
        elif name == "mul":
            value *= n
        else:
            if n == 0:
                raise ZeroDivisionError("divide by zero at step " + str(i))
            value /= n
    return value
"""),
    T("H7", "errors", "val",
      "Write `checked_get(d, key, expected_type)`. Check in this order: "
      "(1) if d is not a dict raise TypeError('d must be a dict'); "
      "(2) if key is not in d raise KeyError(key), with the key itself as the only argument; "
      "(3) if the value is not an instance of expected_type raise TypeError('KEY must be TYPE') where KEY is the "
      "key and TYPE is expected_type.__name__, for example 'age must be int'. "
      "A bool does not count as an int, so True fails when expected_type is int, but it passes when "
      "expected_type is bool. Otherwise return the value. Do not convert values: 1 fails when expected_type is float.",
      "checked_get",
      [eq("checked_get({'a': 3}, 'a', int)", "3"),
       raises("checked_get([('a', 1)], 'a', int)", "TypeError", "d must be a dict"),
       raises("checked_get({'a': 1}, 'b', int)", "KeyError", "b"),
       raises("checked_get({'age': 'x'}, 'age', int)", "TypeError", "age must be int"),
       raises("checked_get({'a': True}, 'a', int)", "TypeError", "a must be int"),
       eq("checked_get({'a': True}, 'a', bool)", "True"),
       raises("checked_get({'a': 1}, 'a', float)", "TypeError", "a must be float"),
       raises("checked_get(None, 'a', int)", "TypeError", "d must be a dict"),
       eq("checked_get({'s': 'hi'}, 's', str)", "'hi'")],
      """
def checked_get(d, key, expected_type):
    if not isinstance(d, dict):
        raise TypeError("d must be a dict")
    if key not in d:
        raise KeyError(key)
    v = d[key]
    if not isinstance(v, expected_type) or (isinstance(v, bool) and expected_type is not bool):
        raise TypeError(f"{key} must be {expected_type.__name__}")
    return v
"""),
    T("H8", "errors", "test",
      "Write `register_user(users, name, age)`. users is a dict mapping names to ages. Check in this order: "
      "(1) if name is not a str raise TypeError('name must be a string'); "
      "(2) if name is empty after stripping whitespace raise ValueError('empty name'); "
      "(3) if age is a bool or not an int raise TypeError('age must be an int'); "
      "(4) if age is below 0 or above 150 raise ValueError('invalid age'); "
      "(5) if the stripped name already exists in users, ignoring upper/lower case, raise "
      "ValueError('duplicate user'). "
      "If all checks pass, set users[stripped_name] = age and return the stripped name. "
      "When any error is raised, users must be left unchanged.",
      "register_user",
      [blk("u = {}", "assert register_user(u, '  Bo ', 30) == 'Bo'", "assert u == {'Bo': 30}"),
       raises("register_user({}, 5, 'x')", "TypeError", "name must be a string"),
       raises("register_user({}, '   ', 'x')", "ValueError", "empty name"),
       raises("register_user({}, 'a', True)", "TypeError", "age must be an int"),
       raises("register_user({}, 'a', 1.5)", "TypeError", "age must be an int"),
       raises("register_user({}, 'a', 151)", "ValueError", "invalid age"),
       raises("register_user({}, 'a', -1)", "ValueError", "invalid age"),
       raises("register_user({'Bo': 1}, ' bo', 5)", "ValueError", "duplicate user"),
       raises("register_user({'Bo': 1}, ' bo', 500)", "ValueError", "invalid age"),
       blk("u = {'Bo': 1}", "try:", "    register_user(u, 'BO', 2)", "except ValueError:", "    pass",
           "assert u == {'Bo': 1}"),
       blk("u = {}", "register_user(u, 'x', 0)", "register_user(u, 'y', 150)", "assert u == {'x': 0, 'y': 150}")],
      """
def register_user(users, name, age):
    if not isinstance(name, str):
        raise TypeError("name must be a string")
    clean = name.strip()
    if not clean:
        raise ValueError("empty name")
    if isinstance(age, bool) or not isinstance(age, int):
        raise TypeError("age must be an int")
    if age < 0 or age > 150:
        raise ValueError("invalid age")
    if any(k.lower() == clean.lower() for k in users):
        raise ValueError("duplicate user")
    users[clean] = age
    return clean
"""),

    # ---- format -------------------------------------------------------------------------------
    T("H9", "format", "train",
      "Write `format_bytes(n)`. n is an int number of bytes. Use units B, KB, MB, GB, TB with 1024 per step. "
      "If abs(n) is below 1024 return the plain integer and ' B', such as '512 B'. "
      "Otherwise use the largest unit for which the value is at least 1 and return the value divided by that "
      "unit with exactly one decimal place (f'{x:.1f}'), a space, and the unit, such as '1.5 KB'. "
      "TB is the largest unit, so huge values stay in TB. A negative n keeps its minus sign in front. "
      "Do not move to a bigger unit because of rounding.",
      "format_bytes",
      [eq("format_bytes(0)", "'0 B'"), eq("format_bytes(1023)", "'1023 B'"),
       eq("format_bytes(1024)", "'1.0 KB'"), eq("format_bytes(1536)", "'1.5 KB'"),
       eq("format_bytes(1048576)", "'1.0 MB'"), eq("format_bytes(5 * 1024**5)", "'5120.0 TB'"),
       eq("format_bytes(-2048)", "'-2.0 KB'"), eq("format_bytes(-5)", "'-5 B'"),
       eq("format_bytes(1048575)", "'1024.0 KB'")],
      """
def format_bytes(n):
    a = abs(n)
    if a < 1024:
        return f"{n} B"
    units = ["KB", "MB", "GB", "TB"]
    i = 0
    while i < len(units) - 1 and a >= 1024 ** (i + 2):
        i += 1
    value = a / 1024 ** (i + 1)
    sign = "-" if n < 0 else ""
    return f"{sign}{value:.1f} {units[i]}"
"""),
    T("H10", "format", "train",
      "Write `render_ranges(nums)`. nums is a list of ints in any order, possibly with duplicates. "
      "Ignore duplicates and sort. Group consecutive integers (each one more than the last) into runs. "
      "A run of 3 or more is written 'first-last'; a run of 1 or 2 is written as its numbers on their own. "
      "Join all pieces with a comma and no spaces. An empty list gives ''. "
      "The input must not be modified.",
      "render_ranges",
      [eq("render_ranges([1,2,3,5,7,8,9,10])", "'1-3,5,7-10'"),
       eq("render_ranges([1,2])", "'1,2'"),
       eq("render_ranges([])", "''"),
       eq("render_ranges([4])", "'4'"),
       eq("render_ranges([9,1,2,2,3,3])", "'1-3,9'"),
       eq("render_ranges([-3,-2,-1,0])", "'-3-0'"),
       eq("render_ranges([5,3,4,10,11])", "'3-5,10,11'"),
       blk("xs = [3,2,1]", "render_ranges(xs)", "assert xs == [3,2,1]")],
      """
def render_ranges(nums):
    s = sorted(set(nums))
    runs = []
    for x in s:
        if runs and x == runs[-1][-1] + 1:
            runs[-1].append(x)
        else:
            runs.append([x])
    parts = []
    for r in runs:
        if len(r) >= 3:
            parts.append(f"{r[0]}-{r[-1]}")
        else:
            parts.extend(str(x) for x in r)
    return ",".join(parts)
"""),
    T("H11", "format", "val",
      "Write `format_phone(s)`. Take only the digits 0-9 from the string s, ignoring every other character. "
      "If there are exactly 11 digits and the first is '1', drop that leading 1. "
      "If exactly 10 digits are left, return them formatted as '(AAA) BBB-CCCC', for example "
      "'(555) 123-4567'. In every other case return the string 'invalid'.",
      "format_phone",
      [eq("format_phone('555-123-4567')", "'(555) 123-4567'"),
       eq("format_phone('+1 (555) 123 4567')", "'(555) 123-4567'"),
       eq("format_phone('15551234567')", "'(555) 123-4567'"),
       eq("format_phone('5551234567')", "'(555) 123-4567'"),
       eq("format_phone('12345')", "'invalid'"),
       eq("format_phone('25551234567')", "'invalid'"),
       eq("format_phone('')", "'invalid'"),
       eq("format_phone('1-555-123-45678')", "'invalid'"),
       eq("format_phone('call 555.123.4567 now')", "'(555) 123-4567'")],
      """
def format_phone(s):
    d = "".join(c for c in s if c in "0123456789")
    if len(d) == 11 and d[0] == "1":
        d = d[1:]
    if len(d) != 10:
        return "invalid"
    return f"({d[:3]}) {d[3:6]}-{d[6:]}"
"""),
    T("H12", "format", "test",
      "Write `wrap_text(text, width)`. Split text on any whitespace into words and lay them out greedily: "
      "put each word on the current line if the line stays at most `width` characters long with one single "
      "space between words, otherwise start a new line. "
      "A word longer than width is not broken; it sits alone on its own line. "
      "Return the lines joined with '\\n', with no trailing newline and no trailing or doubled spaces. "
      "Text with no words gives ''.",
      "wrap_text",
      [eq("wrap_text('the quick brown fox', 9)", "'the quick\\nbrown fox'"),
       eq("wrap_text('', 5)", "''"),
       eq("wrap_text('   ', 5)", "''"),
       eq("wrap_text('  a   b  ', 5)", "'a b'"),
       eq("wrap_text('a bc d', 1)", "'a\\nbc\\nd'"),
       eq("wrap_text('hi extraordinary yo', 5)", "'hi\\nextraordinary\\nyo'"),
       eq("wrap_text('ab cd', 5)", "'ab cd'"),
       eq("wrap_text('one\\ntwo\\tthree', 7)", "'one two\\nthree'")],
      """
def wrap_text(text, width):
    lines = []
    cur = ""
    for w in text.split():
        if not cur:
            cur = w
        elif len(cur) + 1 + len(w) <= width:
            cur += " " + w
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return "\\n".join(lines)
"""),
]
