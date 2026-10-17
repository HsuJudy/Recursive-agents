# agent: claude-code  2026-10-17
"""34 invented tasks in 7 families. Written at the event; nothing here is copied from a public benchmark.

Per family A-F: 2 train, 1 val, 2 test. Family G (money and rounding) is test only, so it shows
whether a learned rule carries over to a kind of task the system never trained on.
"""
from __future__ import annotations

from .suite import Task


def eq(call: str, expected: str) -> str:
    return f"assert {call} == {expected}"


def blk(*lines: str) -> str:
    return "\n".join(lines)


def raises(call: str, exc: str, msg: str) -> str:
    return blk(
        "try:",
        f"    {call}",
        f"except {exc} as e:",
        f"    assert e.args and e.args[0] == {msg!r}, e.args",
        "else:",
        "    assert False, 'no error raised'",
    )


def T(id, family, split, spec, entry, tests, reference) -> Task:
    return Task(id, family, split, spec.strip(), entry, tuple(tests), reference.strip() + "\n")


TASKS: list[Task] = [
    # ---- A: empty, duplicate and boundary inputs ---------------------------------------------
    T("A1", "edge", "train",
      "Write `top_k_distinct(nums, k)`. Return the k largest distinct values of nums in descending order. "
      "If there are fewer than k distinct values return all of them. If k <= 0, or nums is empty, return [].",
      "top_k_distinct",
      [eq("top_k_distinct([5,1,5,3], 2)", "[5,3]"), eq("top_k_distinct([], 3)", "[]"),
       eq("top_k_distinct([1,1,1], 2)", "[1]"), eq("top_k_distinct([4,2], 0)", "[]"),
       eq("top_k_distinct([4,2], -1)", "[]"), eq("top_k_distinct([3,9,2], 10)", "[9,3,2]")],
      """
def top_k_distinct(nums, k):
    if k <= 0:
        return []
    return sorted(set(nums), reverse=True)[:k]
"""),
    T("A2", "edge", "train",
      "Write `moving_average(values, window)`. Return the list of averages (floats) of every run of `window` "
      "consecutive values, left to right. If window < 1 or window is larger than len(values), return [].",
      "moving_average",
      [eq("moving_average([1,2,3,4], 2)", "[1.5,2.5,3.5]"), eq("moving_average([1,2], 3)", "[]"),
       eq("moving_average([], 1)", "[]"), eq("moving_average([1,2,3], 0)", "[]"),
       eq("moving_average([5], 1)", "[5.0]"), eq("moving_average([2,4,6], 3)", "[4.0]")],
      """
def moving_average(values, window):
    if window < 1 or window > len(values):
        return []
    return [sum(values[i:i + window]) / window for i in range(len(values) - window + 1)]
"""),
    T("A3", "edge", "val",
      "Write `longest_run(s)`. Return the length of the longest run of identical consecutive characters in s. "
      "The empty string gives 0.",
      "longest_run",
      [eq("longest_run('aabbbc')", "3"), eq("longest_run('')", "0"), eq("longest_run('a')", "1"),
       eq("longest_run('abc')", "1"), eq("longest_run('zzzz')", "4"), eq("longest_run('abbbaaaa')", "4")],
      """
def longest_run(s):
    best = cur = 0
    prev = None
    for ch in s:
        cur = cur + 1 if ch == prev else 1
        prev = ch
        best = max(best, cur)
    return best
"""),
    T("A4", "edge", "test",
      "Write `second_largest(nums)`. Return the second largest distinct value in nums, "
      "or None if there are fewer than two distinct values.",
      "second_largest",
      [eq("second_largest([3,1,2])", "2"), eq("second_largest([5,5])", "None"), eq("second_largest([])", "None"),
       eq("second_largest([7])", "None"), eq("second_largest([4,4,3])", "3"), eq("second_largest([-1,-2])", "-2")],
      """
def second_largest(nums):
    d = sorted(set(nums), reverse=True)
    return d[1] if len(d) > 1 else None
"""),
    T("A5", "edge", "test",
      "Write `chunk(items, size)`. Split items into consecutive lists of length `size`; the last list may be "
      "shorter. An empty items list, or size < 1, gives [].",
      "chunk",
      [eq("chunk([1,2,3,4,5], 2)", "[[1,2],[3,4],[5]]"), eq("chunk([], 3)", "[]"), eq("chunk([1], 5)", "[[1]]"),
       eq("chunk([1,2], 0)", "[]"), eq("chunk([1,2,3], 3)", "[[1,2,3]]")],
      """
def chunk(items, size):
    if size < 1:
        return []
    return [items[i:i + size] for i in range(0, len(items), size)]
"""),

    # ---- B: do not modify the caller's data --------------------------------------------------
    T("B1", "mutation", "train",
      "Write `sorted_desc(items)`. Return a new list with the items in descending order. "
      "The input list must not be modified.",
      "sorted_desc",
      [blk("a=[1,3,2]", "r=sorted_desc(a)", "assert r==[3,2,1]", "assert a==[1,3,2]", "assert r is not a"),
       eq("sorted_desc([])", "[]"), eq("sorted_desc([2,2,1])", "[2,2,1]")],
      """
def sorted_desc(items):
    return sorted(items, reverse=True)
"""),
    T("B2", "mutation", "train",
      "Write `remove_negatives(nums)`. Return a new list without the negative numbers, keeping the order. "
      "Zero is kept. Do not modify nums.",
      "remove_negatives",
      [blk("a=[3,-1,0,-5,2]", "r=remove_negatives(a)", "assert r==[3,0,2]", "assert a==[3,-1,0,-5,2]"),
       eq("remove_negatives([])", "[]"), eq("remove_negatives([-1])", "[]")],
      """
def remove_negatives(nums):
    return [n for n in nums if n >= 0]
"""),
    T("B3", "mutation", "val",
      "Write `merge_dicts(a, b)`. Return a new dict with all keys of a and b. When a key is in both, the value "
      "from b wins. Neither input may be modified.",
      "merge_dicts",
      [blk("a={'x':1,'y':2}", "b={'y':3}", "r=merge_dicts(a,b)", "assert r=={'x':1,'y':3}",
           "assert a=={'x':1,'y':2}", "assert b=={'y':3}", "assert r is not a and r is not b"),
       eq("merge_dicts({}, {})", "{}"), eq("merge_dicts({'k':1}, {})", "{'k':1}")],
      """
def merge_dicts(a, b):
    return {**a, **b}
"""),
    T("B4", "mutation", "test",
      "Write `add_item(items, x)`. Return a new list equal to items with x added at the end. items must be left "
      "unchanged. items may be None, which counts as an empty list.",
      "add_item",
      [blk("a=[1]", "r=add_item(a,2)", "assert r==[1,2]", "assert a==[1]"),
       eq("add_item(None, 5)", "[5]"), eq("add_item([], 1)", "[1]"),
       blk("a=[]", "add_item(a,1)", "assert a==[]")],
      """
def add_item(items, x):
    return list(items or []) + [x]
"""),
    T("B5", "mutation", "test",
      "Write `normalize_scores(scores)`. scores is a dict of name to number. Return a new dict with the same keys "
      "where each value is divided by the largest value and rounded to 2 decimals. An empty dict gives {}. "
      "If the largest value is 0, every value is 0.0. Do not modify the input.",
      "normalize_scores",
      [eq("normalize_scores({'a':5,'b':10})", "{'a':0.5,'b':1.0}"), eq("normalize_scores({})", "{}"),
       eq("normalize_scores({'a':0,'b':0})", "{'a':0.0,'b':0.0}"),
       eq("normalize_scores({'a':1,'b':3})", "{'a':0.33,'b':1.0}"),
       blk("d={'a':2,'b':4}", "normalize_scores(d)", "assert d=={'a':2,'b':4}")],
      """
def normalize_scores(scores):
    if not scores:
        return {}
    m = max(scores.values())
    if m == 0:
        return {k: 0.0 for k in scores}
    return {k: round(v / m, 2) for k, v in scores.items()}
"""),

    # ---- C: exact output format --------------------------------------------------------------
    T("C1", "format", "train",
      "Write `format_duration(seconds)`. seconds is a non-negative int. Return 'H:MM:SS': hours with no zero "
      "padding, minutes and seconds always two digits. Example: 3661 gives '1:01:01'.",
      "format_duration",
      [eq("format_duration(0)", "'0:00:00'"), eq("format_duration(59)", "'0:00:59'"),
       eq("format_duration(3600)", "'1:00:00'"), eq("format_duration(3661)", "'1:01:01'"),
       eq("format_duration(86400)", "'24:00:00'")],
      """
def format_duration(seconds):
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}"
"""),
    T("C2", "format", "train",
      "Write `to_title(s)`. Return s with each word capitalised (first letter upper case, the rest lower case). "
      "Words are separated by any amount of whitespace in the input, and by exactly one space in the output, "
      "with no leading or trailing space.",
      "to_title",
      [eq("to_title('  hello   WORLD ')", "'Hello World'"), eq("to_title('')", "''"), eq("to_title('a')", "'A'"),
       eq("to_title('mIxEd cAsE')", "'Mixed Case'"), eq("to_title('tab\\tsep')", "'Tab Sep'")],
      """
def to_title(s):
    return " ".join(w.capitalize() for w in s.split())
"""),
    T("C3", "format", "val",
      "Write `csv_line(fields)`. fields is a list of strings. Return one CSV line (no trailing newline). A field is "
      "wrapped in double quotes if it contains a comma, a double quote or a newline; double quotes inside it are "
      "doubled. Other fields are written as they are, separated by commas.",
      "csv_line",
      [eq("csv_line(['a','b'])", "'a,b'"), eq("csv_line(['a,b','c'])", "'\"a,b\",c'"),
       eq("csv_line(['say \"hi\"'])", "'\"say \"\"hi\"\"\"'"), eq("csv_line([])", "''"),
       eq("csv_line(['x\\ny'])", "'\"x\\ny\"'")],
      """
def csv_line(fields):
    out = []
    for f in fields:
        if any(c in f for c in ',"\\n'):
            f = '"' + f.replace('"', '""') + '"'
        out.append(f)
    return ",".join(out)
"""),
    T("C4", "format", "test",
      "Write `ordinal(n)`. n is a positive int. Return n followed by its English ordinal suffix: 1 gives '1st', "
      "2 gives '2nd', 3 gives '3rd', 4 gives '4th', 11 gives '11th', 12 gives '12th', 13 gives '13th', "
      "21 gives '21st', 112 gives '112th'.",
      "ordinal",
      [eq("ordinal(1)", "'1st'"), eq("ordinal(2)", "'2nd'"), eq("ordinal(3)", "'3rd'"), eq("ordinal(4)", "'4th'"),
       eq("ordinal(11)", "'11th'"), eq("ordinal(12)", "'12th'"), eq("ordinal(13)", "'13th'"),
       eq("ordinal(21)", "'21st'"), eq("ordinal(112)", "'112th'"), eq("ordinal(103)", "'103rd'")],
      """
def ordinal(n):
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"
"""),
    T("C5", "format", "test",
      "Write `pad_table(rows)`. rows is a list of rows, each row a list of strings, all rows the same length. "
      "Return one string: rows joined by a newline (no trailing newline), cells in a row joined by ' | ', and every "
      "cell left-justified (padded with spaces on the right) to the width of the longest cell in its column. "
      "The last column is padded too. No rows gives ''.",
      "pad_table",
      [eq("pad_table([['a','bb'],['ccc','d']])", "'a   | bb\\nccc | d '"), eq("pad_table([])", "''"),
       eq("pad_table([['x']])", "'x'"), eq("pad_table([['ab','c'],['d','ef']])", "'ab | c \\nd  | ef'")],
      """
def pad_table(rows):
    if not rows:
        return ""
    widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
    return "\\n".join(" | ".join(c.ljust(widths[i]) for i, c in enumerate(r)) for r in rows)
"""),

    # ---- D: ordering and tie-breaking --------------------------------------------------------
    T("D1", "ordering", "train",
      "Write `rank_players(scores)`. scores is a list of (name, points) pairs. Return the names ordered by points, "
      "highest first. Players with equal points are ordered alphabetically by name.",
      "rank_players",
      [eq("rank_players([('bob',5),('amy',5),('cat',9)])", "['cat','amy','bob']"), eq("rank_players([])", "[]"),
       eq("rank_players([('z',1)])", "['z']"), eq("rank_players([('b',1),('a',2),('c',1)])", "['a','b','c']")],
      """
def rank_players(scores):
    return [n for n, _ in sorted(scores, key=lambda t: (-t[1], t[0]))]
"""),
    T("D2", "ordering", "train",
      "Write `dedupe_keep_first(items)`. Remove duplicates from the list, keeping the first occurrence of each "
      "item and the original order of what remains. Return a new list.",
      "dedupe_keep_first",
      [eq("dedupe_keep_first([3,1,3,2,1])", "[3,1,2]"), eq("dedupe_keep_first([])", "[]"),
       eq("dedupe_keep_first(['a','A','a'])", "['a','A']")],
      """
def dedupe_keep_first(items):
    return list(dict.fromkeys(items))
"""),
    T("D3", "ordering", "val",
      "Write `group_by_length(words)`. Return a dict that maps each word length to the list of words with that "
      "length, in the order they appear in words (duplicates are kept). The dict's keys must be in ascending order.",
      "group_by_length",
      [blk("r=group_by_length(['bb','a','cc','a','ddd'])", "assert r=={1:['a','a'],2:['bb','cc'],3:['ddd']}",
           "assert list(r)==[1,2,3]"),
       blk("r=group_by_length(['xyz','a'])", "assert list(r)==[1,3]"), eq("group_by_length([])", "{}")],
      """
def group_by_length(words):
    d = {}
    for w in words:
        d.setdefault(len(w), []).append(w)
    return {k: d[k] for k in sorted(d)}
"""),
    T("D4", "ordering", "test",
      "Write `sort_by_last_then_first(names)`. names are strings like 'Ada Lovelace'. Return a new list sorted by the "
      "last word (last name) ignoring case; names with the same last name are sorted by the first word ignoring "
      "case; names that are still equal keep their original order.",
      "sort_by_last_then_first",
      [eq("sort_by_last_then_first(['Ada Lovelace','Bob Lovelace','alan turing','Grace Hopper'])",
          "['Grace Hopper','Ada Lovelace','Bob Lovelace','alan turing']"),
       eq("sort_by_last_then_first(['zed Smith','Amy smith'])", "['Amy smith','zed Smith']"),
       eq("sort_by_last_then_first(['Ann Lee','ann lee'])", "['Ann Lee','ann lee']"),
       eq("sort_by_last_then_first([])", "[]")],
      """
def sort_by_last_then_first(names):
    def key(n):
        parts = n.split()
        return (parts[-1].lower(), parts[0].lower())
    return sorted(names, key=key)
"""),
    T("D5", "ordering", "test",
      "Write `top_words(text, n)`. Split text on whitespace, lower-case the words, and return the n most frequent "
      "as a list of (word, count) tuples, most frequent first. Words with equal counts are ordered alphabetically. "
      "If n is larger than the number of distinct words, return all of them.",
      "top_words",
      [eq("top_words('b a b a c', 2)", "[('a',2),('b',2)]"), eq("top_words('The the THE x', 1)", "[('the',3)]"),
       eq("top_words('', 3)", "[]"), eq("top_words('a b', 5)", "[('a',1),('b',1)]")],
      """
from collections import Counter

def top_words(text, n):
    c = Counter(text.lower().split())
    return sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[:max(n, 0)]
"""),

    # ---- E: the exact error the spec asks for ------------------------------------------------
    T("E1", "errors", "train",
      "Write `safe_divide(a, b)`. Return a / b. If b is 0, raise ValueError with the exact message "
      "'division by zero'.",
      "safe_divide",
      [eq("safe_divide(6, 3)", "2.0"), raises("safe_divide(1, 0)", "ValueError", "division by zero"),
       eq("safe_divide(0, 5)", "0.0"), eq("safe_divide(-4, 2)", "-2.0"),
       raises("safe_divide(1, 0.0)", "ValueError", "division by zero")],
      """
def safe_divide(a, b):
    if b == 0:
        raise ValueError("division by zero")
    return a / b
"""),
    T("E2", "errors", "train",
      "Write `parse_age(s)`. Strip whitespace from the string s and convert it to an int. If it is not a whole "
      "number raise ValueError('not a number'). If the number is below 0 or above 150 raise "
      "ValueError('out of range'). Otherwise return the int.",
      "parse_age",
      [eq("parse_age(' 42 ')", "42"), raises("parse_age('abc')", "ValueError", "not a number"),
       raises("parse_age('-1')", "ValueError", "out of range"), raises("parse_age('151')", "ValueError", "out of range"),
       eq("parse_age('150')", "150"), raises("parse_age('4.5')", "ValueError", "not a number"),
       raises("parse_age('')", "ValueError", "not a number")],
      """
def parse_age(s):
    try:
        n = int(s.strip())
    except ValueError:
        raise ValueError("not a number")
    if n < 0 or n > 150:
        raise ValueError("out of range")
    return n
"""),
    T("E3", "errors", "val",
      "Write `get_path(d, path)`. path is a dot-separated string like 'a.b.c'. Return the value found by following "
      "those keys through the nested dicts in d. If any key is missing, or a value on the way is not a dict, raise "
      "KeyError with the whole path string as its only argument, e.g. KeyError('a.b.c').",
      "get_path",
      [eq("get_path({'a':{'b':1}}, 'a.b')", "1"), raises("get_path({'a':{'b':1}}, 'a.c')", "KeyError", "a.c"),
       raises("get_path({'a':5}, 'a.b')", "KeyError", "a.b"),
       eq("get_path({'a':{'b':{'c':2}}}, 'a.b')", "{'c':2}")],
      """
def get_path(d, path):
    cur = d
    for k in path.split("."):
        if not isinstance(cur, dict) or k not in cur:
            raise KeyError(path)
        cur = cur[k]
    return cur
"""),
    T("E4", "errors", "test",
      "Write `withdraw(balance, amount)`. Return balance - amount. Check in this order: if amount is not an int or "
      "float (a bool does not count as a number) raise TypeError('amount must be a number'); if amount <= 0 raise "
      "ValueError('amount must be positive'); if amount > balance raise ValueError('insufficient funds').",
      "withdraw",
      [eq("withdraw(100, 30)", "70"), raises("withdraw(100, '5')", "TypeError", "amount must be a number"),
       raises("withdraw(100, True)", "TypeError", "amount must be a number"),
       raises("withdraw(100, 0)", "ValueError", "amount must be positive"),
       raises("withdraw(100, -5)", "ValueError", "amount must be positive"),
       raises("withdraw(100, 500)", "ValueError", "insufficient funds"), eq("withdraw(100, 100)", "0"),
       raises("withdraw(0, -1)", "ValueError", "amount must be positive")],
      """
def withdraw(balance, amount):
    if isinstance(amount, bool) or not isinstance(amount, (int, float)):
        raise TypeError("amount must be a number")
    if amount <= 0:
        raise ValueError("amount must be positive")
    if amount > balance:
        raise ValueError("insufficient funds")
    return balance - amount
"""),
    T("E5", "errors", "test",
      "Write `parse_kv(line)`. Parse 'key=value' into a tuple (key, value), both with surrounding whitespace "
      "removed. Only the first '=' splits, so 'a=b=c' gives ('a', 'b=c'). If there is no '=' raise "
      "ValueError('missing ='). If the key is empty after stripping raise ValueError('empty key').",
      "parse_kv",
      [eq("parse_kv(' a = b ')", "('a','b')"), eq("parse_kv('a=b=c')", "('a','b=c')"),
       raises("parse_kv('abc')", "ValueError", "missing ="), raises("parse_kv(' =x')", "ValueError", "empty key"),
       eq("parse_kv('k=')", "('k','')")],
      """
def parse_kv(line):
    if "=" not in line:
        raise ValueError("missing =")
    k, v = line.split("=", 1)
    k = k.strip()
    if not k:
        raise ValueError("empty key")
    return (k, v.strip())
"""),

    # ---- F: dates and times ------------------------------------------------------------------
    T("F1", "dates", "train",
      "Write `days_between(d1, d2)`. d1 and d2 are 'YYYY-MM-DD' strings. Return the number of days between them "
      "as a non-negative int (the order of the two dates does not matter).",
      "days_between",
      [eq("days_between('2024-03-01', '2024-02-28')", "2"), eq("days_between('2024-01-01', '2024-01-01')", "0"),
       eq("days_between('2023-12-31', '2024-01-01')", "1"), eq("days_between('2000-01-01', '2001-01-01')", "366")],
      """
import datetime

def days_between(d1, d2):
    return abs((datetime.date.fromisoformat(d2) - datetime.date.fromisoformat(d1)).days)
"""),
    T("F2", "dates", "train",
      "Write `is_leap(year)`. Return True if year is a leap year in the Gregorian calendar, else False.",
      "is_leap",
      [eq("is_leap(1900)", "False"), eq("is_leap(2000)", "True"), eq("is_leap(2024)", "True"),
       eq("is_leap(2023)", "False"), eq("is_leap(2100)", "False"), eq("is_leap(1996)", "True")],
      """
def is_leap(year):
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
"""),
    T("F3", "dates", "val",
      "Write `add_months(date_str, months)`. date_str is 'YYYY-MM-DD'. Return the date moved by `months` months "
      "(may be negative) as a 'YYYY-MM-DD' string. If the target month is shorter, use its last day: "
      "2024-01-31 plus 1 month is '2024-02-29'.",
      "add_months",
      [eq("add_months('2024-01-31', 1)", "'2024-02-29'"), eq("add_months('2023-01-31', 1)", "'2023-02-28'"),
       eq("add_months('2024-03-15', -3)", "'2023-12-15'"), eq("add_months('2024-11-30', 3)", "'2025-02-28'"),
       eq("add_months('2024-05-10', 0)", "'2024-05-10'"), eq("add_months('2024-12-31', 12)", "'2025-12-31'")],
      """
import calendar
import datetime

def add_months(date_str, months):
    d = datetime.date.fromisoformat(date_str)
    y, m = divmod(d.year * 12 + (d.month - 1) + months, 12)
    m += 1
    return datetime.date(y, m, min(d.day, calendar.monthrange(y, m)[1])).isoformat()
"""),
    T("F4", "dates", "test",
      "Write `weekday_name(date_str)`. date_str is 'YYYY-MM-DD'. Return the English name of the weekday, such as "
      "'Monday' or 'Saturday'.",
      "weekday_name",
      [eq("weekday_name('2026-10-17')", "'Saturday'"), eq("weekday_name('2000-01-01')", "'Saturday'"),
       eq("weekday_name('2024-02-29')", "'Thursday'"), eq("weekday_name('1970-01-01')", "'Thursday'"),
       eq("weekday_name('2023-12-25')", "'Monday'")],
      """
import calendar
import datetime

def weekday_name(date_str):
    return calendar.day_name[datetime.date.fromisoformat(date_str).weekday()]
"""),
    T("F5", "dates", "test",
      "Write `sum_hhmm(times)`. times is a list of 'HH:MM' strings, each a duration. Return the total as 'HH:MM'. "
      "Hours are not limited to 24, and both parts are zero-padded to at least two digits. An empty list gives "
      "'00:00'.",
      "sum_hhmm",
      [eq("sum_hhmm(['01:30','02:45'])", "'04:15'"), eq("sum_hhmm(['23:59','00:01'])", "'24:00'"),
       eq("sum_hhmm([])", "'00:00'"), eq("sum_hhmm(['100:00','00:30'])", "'100:30'")],
      """
def sum_hhmm(times):
    total = sum(int(h) * 60 + int(m) for h, m in (t.split(":") for t in times))
    return f"{total // 60:02d}:{total % 60:02d}"
"""),

    # ---- G: money and rounding (test only: a family the system never trains on) --------------
    T("G1", "money", "test",
      "Write `split_bill(total_cents, people)`. total_cents is a non-negative int and people is an int >= 1. Return "
      "a list of `people` ints (cents per person) that add up to exactly total_cents. The amounts differ by at most "
      "1 cent, and the first (total_cents % people) people pay the extra cent.",
      "split_bill",
      [eq("split_bill(100, 3)", "[34,33,33]"), eq("split_bill(99, 3)", "[33,33,33]"),
       eq("split_bill(1, 4)", "[1,0,0,0]"), eq("split_bill(0, 2)", "[0,0]"), eq("split_bill(10, 1)", "[10]")],
      """
def split_bill(total_cents, people):
    base, extra = divmod(total_cents, people)
    return [base + 1 if i < extra else base for i in range(people)]
"""),
    T("G2", "money", "test",
      "Write `round_half_up(x, places)`. Round the number x to `places` decimal places and return a float. Halves "
      "round away from zero, judged on the decimal digits you see when you print x: 2.5 gives 3.0, 0.125 at 2 "
      "places gives 0.13, 1.005 at 2 places gives 1.01, and -2.5 gives -3.0.",
      "round_half_up",
      [eq("round_half_up(2.5, 0)", "3.0"), eq("round_half_up(0.125, 2)", "0.13"),
       eq("round_half_up(1.005, 2)", "1.01"), eq("round_half_up(-2.5, 0)", "-3.0"),
       eq("round_half_up(2.675, 2)", "2.68"), eq("round_half_up(3.14159, 3)", "3.142")],
      """
from decimal import Decimal, ROUND_HALF_UP

def round_half_up(x, places):
    q = Decimal(1).scaleb(-places)
    return float(Decimal(str(x)).quantize(q, rounding=ROUND_HALF_UP))
"""),
    T("G3", "money", "test",
      "Write `apply_discount(price_cents, percent)`. price_cents is an int and percent is an int from 0 to 100. "
      "Return the price in whole cents after taking percent off, rounded to the nearest cent with exact halves "
      "rounding up. Use integer arithmetic only (no floats).",
      "apply_discount",
      [eq("apply_discount(999, 10)", "899"), eq("apply_discount(1005, 50)", "503"), eq("apply_discount(1, 50)", "1"),
       eq("apply_discount(0, 10)", "0"), eq("apply_discount(100, 100)", "0"), eq("apply_discount(333, 33)", "223")],
      """
def apply_discount(price_cents, percent):
    return (price_cents * (100 - percent) + 50) // 100
"""),
    T("G4", "money", "test",
      "Write `format_money(cents)`. cents is an int. Return it as dollars: 123456 gives '$1,234.56', 5 gives "
      "'$0.05', and negative amounts put the minus sign first: -150 gives '-$1.50'. Use commas as thousands "
      "separators and always two digits after the point.",
      "format_money",
      [eq("format_money(123456)", "'$1,234.56'"), eq("format_money(5)", "'$0.05'"), eq("format_money(0)", "'$0.00'"),
       eq("format_money(100000000)", "'$1,000,000.00'"), eq("format_money(-150)", "'-$1.50'"),
       eq("format_money(99)", "'$0.99'")],
      """
def format_money(cents):
    sign = "-" if cents < 0 else ""
    c = abs(cents)
    return f"{sign}${c // 100:,}.{c % 100:02d}"
"""),
]
