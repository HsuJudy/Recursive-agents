# agent: claude-code  2026-10-17
"""8 dense invented tasks (families ordering, dates): each spec packs 8-10 explicit requirements, so a strong model
usually misses at least one. Splits: DC1-3 train, DC4-5 val, DC6-8 test. Nothing here is copied from a public
benchmark or from suite_data / suite_hard. Dates use only the standard library, ISO 'YYYY-MM-DD' and 'HH:MM'.
"""
from __future__ import annotations

from .suite import Task
from .suite_data import T as _T
from .suite_data import blk, eq, raises


def _pack(tests, limit=14):
    """Keep at most `limit` hidden tests by joining neighbouring snippets (every requirement stays covered)."""
    tests = list(tests)
    if len(tests) <= limit:
        return tests
    extra = len(tests) - limit  # number of merges needed
    out, i = [], 0
    while i < len(tests):
        if extra > 0 and i + 1 < len(tests):
            out.append(tests[i] + "\n" + tests[i + 1])
            i += 2
            extra -= 1
        else:
            out.append(tests[i])
            i += 1
    return out


def T(id, family, split, spec, entry, tests, reference):
    return _T(id, family, split, spec, entry, _pack(tests), reference)

DENSE_C: list[Task] = [
    # ---- DC1 ordering / train ------------------------------------------------------------------
    T("DC1", "ordering", "train",
      "Write `rank_tickets(tickets)`. tickets is a list of dicts with an 'id' string and optional keys 'priority' (a string), "
      "'age_days' (an int) and 'tags' (a list of strings). Return a new list containing only the id strings, best first, "
      "and never modify the input. Any ticket whose tags contain 'spam' (compared case-insensitively) is dropped first, "
      "and only then are duplicate ids removed, keeping the first remaining ticket for each exact id. "
      "Priority order is urgent, then high, then normal, then low, matched case-insensitively after stripping surrounding "
      "whitespace; a missing, None or unrecognised priority counts as low. Within one priority the larger age_days comes first, "
      "and a missing or None age_days counts as 0. If priority and age are both equal, a ticket whose tags contain "
      "'escalated' (case-insensitive) comes before one without it; a missing or None tags value means no tags. "
      "Remaining ties are ordered by id ascending ignoring case, and when even that is equal the original input order is kept. "
      "An empty input gives [].",
      "rank_tickets",
      [eq("rank_tickets([{'id':'a','priority':'low'},{'id':'b','priority':'urgent'},{'id':'c','priority':'normal'},{'id':'d','priority':'high'}])", "['b','d','c','a']"),
       eq("rank_tickets([{'id':'x','priority':'Normal'},{'id':'y','priority':' HIGH '}])", "['y','x']"),
       eq("rank_tickets([{'id':'u','priority':'wat'},{'id':'m'},{'id':'n','priority':'normal'},{'id':'q','priority':None}])", "['n','m','q','u']"),
       eq("rank_tickets([{'id':'a','priority':'high','age_days':2},{'id':'b','priority':'high','age_days':9}])", "['b','a']"),
       eq("rank_tickets([{'id':'a','priority':'low','age_days':None},{'id':'b','priority':'low','age_days':1},{'id':'c','priority':'low'}])", "['b','a','c']"),
       eq("rank_tickets([{'id':'a','priority':'low','tags':['x']},{'id':'z','priority':'low','tags':['Escalated']},{'id':'m','priority':'low','tags':None}])", "['z','a','m']"),
       eq("rank_tickets([{'id':'e','priority':'low','age_days':1,'tags':['escalated']},{'id':'f','priority':'low','age_days':2}])", "['f','e']"),
       eq("rank_tickets([{'id':'b'},{'id':'A'},{'id':'c'}])", "['A','b','c']"),
       eq("rank_tickets([{'id':'a'},{'id':'A'}])", "['a','A']"),
       eq("rank_tickets([{'id':'A'},{'id':'a'}])", "['A','a']"),
       eq("rank_tickets([{'id':'s','tags':['SPAM']},{'id':'k'}])", "['k']"),
       eq("rank_tickets([{'id':'d','priority':'low'},{'id':'d','priority':'urgent'},{'id':'e','priority':'normal'}])", "['e','d']"),
       eq("rank_tickets([{'id':'d','priority':'low','tags':['spam']},{'id':'d','priority':'high'},{'id':'e','priority':'normal'}])", "['d','e']"),
       blk("xs = [{'id':'b','tags':['x']},{'id':'a'}]", "import copy", "orig = copy.deepcopy(xs)",
           "r = rank_tickets(xs)", "assert r == ['a','b'] and isinstance(r, list) and xs == orig",
           "assert rank_tickets([]) == []")],
      """
def rank_tickets(tickets):
    order = {'urgent': 0, 'high': 1, 'normal': 2, 'low': 3}
    seen = set()
    items = []
    for pos, t in enumerate(tickets):
        tags = [str(x).lower() for x in (t.get('tags') or [])]
        if 'spam' in tags:
            continue
        if t['id'] in seen:
            continue
        seen.add(t['id'])
        pr = order.get(str(t.get('priority') or '').strip().lower(), 3)
        age = t.get('age_days')
        age = 0 if age is None else age
        items.append(((pr, -age, 0 if 'escalated' in tags else 1, t['id'].casefold(), pos), t['id']))
    items.sort(key=lambda x: x[0])
    return [i for _, i in items]
"""),
    # ---- DC2 dates / train ---------------------------------------------------------------------
    T("DC2", "dates", "train",
      "Write `monthly_due_dates(first, count, holidays=())`. first is an ISO 'YYYY-MM-DD' string and the function returns a list "
      "of `count` ISO date strings, one per month starting with first's own month. "
      "The date for month n nominally uses first's day-of-month in the month n months after first's month; if that month is "
      "too short, use its last day (leap years matter), and always derive each month from first rather than from the "
      "previous result, so a start of Jan 31 gives Jan 31, Feb 28 or 29, then Mar 31 again. "
      "Each nominal date is then moved forward day by day until it is neither a Saturday, a Sunday, nor one of the ISO date "
      "strings in holidays; this applies to the first date too, and a moved date may land in the next month or year. "
      "Moving one date never affects any other date. Dates roll over from December into January of the next year. "
      "If count is zero or negative return []. If first is not exactly a zero-padded 'YYYY-MM-DD' for a real calendar date "
      "(no spaces, no missing zeros, no impossible days such as Feb 30) raise ValueError with the message 'invalid date'.",
      "monthly_due_dates",
      [eq("monthly_due_dates('2024-01-31', 4)", "['2024-01-31','2024-02-29','2024-04-01','2024-04-30']"),
       eq("monthly_due_dates('2023-01-31', 3)", "['2023-01-31','2023-02-28','2023-03-31']"),
       eq("monthly_due_dates('2024-06-01', 2)", "['2024-06-03','2024-07-01']"),
       eq("monthly_due_dates('2023-12-15', 3)", "['2023-12-15','2024-01-15','2024-02-15']"),
       eq("monthly_due_dates('2022-12-31', 1)", "['2023-01-02']"),
       blk("r = monthly_due_dates('2024-02-29', 13)", "assert len(r) == 13 and r[1] == '2024-03-29' and r[-1] == '2025-02-28', r"),
       eq("monthly_due_dates('2028-02-29', 13)[-1]", "'2029-02-28'"),
       eq("monthly_due_dates('2024-01-31', 1, holidays={'2024-01-31'})", "['2024-02-01']"),
       eq("monthly_due_dates('2024-03-31', 1, ['2024-04-01'])", "['2024-04-02']"),
       eq("monthly_due_dates('2024-01-31', 2, holidays=['2024-01-31'])", "['2024-02-01','2024-02-29']"),
       eq("monthly_due_dates('2024-01-15', 0)", "[]"),
       eq("monthly_due_dates('2024-01-15', -3)", "[]"),
       raises("monthly_due_dates('2024-02-30', 2)", "ValueError", "invalid date"),
       raises("monthly_due_dates('2024-2-03', 2)", "ValueError", "invalid date"),
       raises("monthly_due_dates(' 2024-02-03', 2)", "ValueError", "invalid date")],
      """
import calendar
import datetime
import re


def monthly_due_dates(first, count, holidays=()):
    if not isinstance(first, str) or not re.fullmatch(r'\\d{4}-\\d{2}-\\d{2}', first):
        raise ValueError('invalid date')
    try:
        d0 = datetime.date(int(first[:4]), int(first[5:7]), int(first[8:]))
    except ValueError:
        raise ValueError('invalid date') from None
    hol = set(holidays)
    out = []
    for n in range(max(count, 0)):
        m = d0.month - 1 + n
        y = d0.year + m // 12
        mo = m % 12 + 1
        d = datetime.date(y, mo, min(d0.day, calendar.monthrange(y, mo)[1]))
        while d.weekday() >= 5 or d.isoformat() in hol:
            d += datetime.timedelta(days=1)
        out.append(d.isoformat())
    return out
"""),
    # ---- DC3 ordering / train ------------------------------------------------------------------
    T("DC3", "ordering", "train",
      "Write `shelve_titles(titles)`. titles is a list of strings; return a new list of the original strings (unchanged, "
      "whitespace included) in library order, and do not modify the input. If any element is not a str raise TypeError "
      "with the message 'title must be a string'. Titles that are empty or only whitespace are dropped, and after that "
      "exact duplicate strings (identical including whitespace and case) are removed keeping the first. "
      "The sort key of a title is: strip it, lowercase it, then remove one leading article ('the ', 'a ' or 'an ') only if "
      "something other than whitespace remains after it, and strip leading whitespace from what is left, so 'The' alone stays 'the'. "
      "Keys are compared naturally: split into runs of digits and runs of other characters, compare digit runs by integer "
      "value (leading zeros ignored), and a digit run sorts before a text run at the same position. Other characters, "
      "punctuation included, compare by plain code point. "
      "When two keys are equal, the title that had no leading article comes first, and any remaining tie keeps the original input order. "
      "An empty input gives [].",
      "shelve_titles",
      [eq("shelve_titles(['Beta','alpha','Gamma'])", "['alpha','Beta','Gamma']"),
       eq("shelve_titles(['The Hobbit','Dune','A Wrinkle in Time','An Echo'])", "['Dune','An Echo','The Hobbit','A Wrinkle in Time']"),
       eq("shelve_titles(['Apple','The A Team'])", "['The A Team','Apple']"),
       eq("shelve_titles(['The','Ant','Zoo','A '])", "['A ','Ant','The','Zoo']"),
       eq("shelve_titles(['  Zed ','Yak'])", "['Yak','  Zed ']"),
       eq("shelve_titles(['Book 10','Book 2','Book 1'])", "['Book 1','Book 2','Book 10']"),
       eq("shelve_titles(['Apple','1984','Zoo','10 Things'])", "['10 Things','1984','Apple','Zoo']"),
       eq("shelve_titles(['Vol 007','Vol 7','Vol 06'])", "['Vol 06','Vol 007','Vol 7']"),
       eq("shelve_titles(['b','A','a'])", "['A','a','b']"),
       eq("shelve_titles(['The Hobbit','A Hobbit','Hobbit'])", "['Hobbit','The Hobbit','A Hobbit']"),
       eq("shelve_titles(['Dune','Dune','dune',' Dune'])", "['Dune','dune',' Dune']"),
       eq("shelve_titles(['', '  ', 'X'])", "['X']"),
       eq("shelve_titles(['\"Quote\"','Apple'])", "['\"Quote\"','Apple']"),
       raises("shelve_titles(['a', 3])", "TypeError", "title must be a string"),
       blk("xs = ['b','a']", "r = shelve_titles(xs)", "assert r == ['a','b'] and xs == ['b','a'] and r is not xs",
           "assert shelve_titles([]) == []")],
      """
import re


def shelve_titles(titles):
    for t in titles:
        if not isinstance(t, str):
            raise TypeError('title must be a string')
    seen = set()
    items = []
    for pos, t in enumerate(titles):
        if not t.strip() or t in seen:
            continue
        seen.add(t)
        key = t.strip().lower()
        had = 0
        for art in ('the ', 'a ', 'an '):
            if key.startswith(art) and key[len(art):].strip():
                key = key[len(art):].lstrip()
                had = 1
                break
        parts = [(0, int(p)) if p.isdigit() else (1, p) for p in re.split(r'(\\d+)', key) if p]
        items.append(((parts, had, pos), t))
    items.sort(key=lambda x: x[0])
    return [t for _, t in items]
"""),
    # ---- DC4 dates / val -----------------------------------------------------------------------
    T("DC4", "dates", "val",
      "Write `free_windows(busy, start, end, min_len)`. All times are zero-padded 24-hour 'HH:MM' strings; busy is a list of "
      "(begin, finish) pairs and the function returns a list of (begin, finish) tuples of 'HH:MM' strings for the free gaps "
      "between start and end, in time order, without modifying busy. "
      "A time that is not exactly two digits, a colon and two digits, or has hours above 24 or minutes above 59, "
      "raises ValueError('bad time'); '24:00' is valid only as an end time (the end argument or a busy finish), and anywhere "
      "else raises the same error. A busy pair whose begin is later than its finish raises ValueError('bad interval'); "
      "a pair with begin equal to finish is ignored. "
      "Busy intervals are half-open, so one that finishes at 10:00 and one that begins at 10:00 leave no gap, and "
      "overlapping or touching intervals count as one. Busy intervals are clipped to the start-end window, and ones entirely "
      "outside it are ignored. A gap is reported only if its length in minutes is at least min_len, so a gap of exactly min_len "
      "is kept; a min_len below 1 is treated as 1 so zero-length gaps are never reported. "
      "If start is not earlier than end return [], and with no busy time the whole window is one gap if it is long enough.",
      "free_windows",
      [eq("free_windows([], '09:00', '17:00', 30)", "[('09:00','17:00')]"),
       eq("free_windows([('10:00','11:00'),('13:00','14:30')], '09:00', '17:00', 30)", "[('09:00','10:00'),('11:00','13:00'),('14:30','17:00')]"),
       eq("free_windows([('10:00','11:00'),('11:00','12:00')], '09:00', '17:00', 15)", "[('09:00','10:00'),('12:00','17:00')]"),
       eq("free_windows([('12:00','13:30'),('09:30','12:30')], '09:00', '14:00', 30)", "[('09:00','09:30'),('13:30','14:00')]"),
       eq("free_windows([('12:00','13:30'),('09:30','12:30')], '09:00', '14:00', 31)", "[]"),
       eq("free_windows([('07:00','09:30'),('16:00','20:00')], '09:00', '17:00', 30)", "[('09:30','16:00')]"),
       eq("free_windows([('05:00','08:00'),('08:00','09:00'),('18:00','19:00')], '09:00', '17:00', 60)", "[('09:00','17:00')]"),
       eq("free_windows([('10:00','10:00')], '09:00', '10:00', 5)", "[('09:00','10:00')]"),
       eq("free_windows([('09:00','09:30')], '09:00', '10:00', 0)", "[('09:30','10:00')]"),
       eq("free_windows([('09:00','10:00')], '09:00', '10:00', -5)", "[]"),
       eq("free_windows([], '10:00', '10:00', 5)", "[]"),
       eq("free_windows([], '11:00', '10:00', 5)", "[]"),
       eq("free_windows([('22:00','24:00')], '20:00', '24:00', 60)", "[('20:00','22:00')]"),
       raises("free_windows([('10:00','09:00')], '08:00', '12:00', 5)", "ValueError", "bad interval"),
       raises("free_windows([], '9:00', '12:00', 5)", "ValueError", "bad time"),
       raises("free_windows([], '24:00', '24:00', 5)", "ValueError", "bad time"),
       raises("free_windows([('12:60','13:00')], '08:00', '12:00', 5)", "ValueError", "bad time"),
       blk("b = [('12:00','13:00'),('09:00','10:00')]", "r = free_windows(b, '08:00', '14:00', 30)",
           "assert b == [('12:00','13:00'),('09:00','10:00')]", "assert r == [('08:00','09:00'),('10:00','12:00'),('13:00','14:00')]",
           "assert all(isinstance(x, tuple) for x in r)")],
      """
import re


def _parse(t, allow24):
    if not isinstance(t, str) or not re.fullmatch(r'\\d\\d:\\d\\d', t):
        raise ValueError('bad time')
    h, m = int(t[:2]), int(t[3:])
    if m > 59 or h > 24 or (h == 24 and (m != 0 or not allow24)):
        raise ValueError('bad time')
    return h * 60 + m


def _fmt(x):
    return f'{x // 60:02d}:{x % 60:02d}'


def free_windows(busy, start, end, min_len):
    s0 = _parse(start, False)
    e0 = _parse(end, True)
    ivs = []
    for a, b in busy:
        s = _parse(a, False)
        e = _parse(b, True)
        if s > e:
            raise ValueError('bad interval')
        if s == e:
            continue
        s, e = max(s, s0), min(e, e0)
        if s < e:
            ivs.append((s, e))
    if s0 >= e0:
        return []
    ivs.sort()
    need = max(min_len, 1)
    out = []
    cur = s0
    for s, e in ivs:
        if s - cur >= need:
            out.append((_fmt(cur), _fmt(s)))
        cur = max(cur, e)
    if e0 - cur >= need:
        out.append((_fmt(cur), _fmt(e0)))
    return out
"""),
    # ---- DC5 ordering / val --------------------------------------------------------------------
    T("DC5", "ordering", "val",
      "Write `merge_runs(a, b, descending=False, unique=False)`. a and b are sequences that should already be sorted "
      "(ascending, or descending when descending is True); return a new list holding their merge in that same direction, "
      "and never modify the inputs. A None argument counts as an empty sequence, and any None element inside a or b is "
      "discarded before anything else is checked or merged. After that, if a is not sorted in the requested direction raise "
      "ValueError('a is not sorted'), else if b is not sorted raise ValueError('b is not sorted'); equal neighbours are "
      "allowed, and a is always checked before b. The merge is stable: when an element of a equals an element of b, "
      "the one from a comes first, and equality is ordinary == so 1 and 1.0 are equal, ints and floats compare by value, and strings "
      "compare by plain code point. Equal elements are all kept unless unique is True, in which case only the first of each "
      "run of equal neighbours in the merged result is kept. The result is always a list, even if the inputs are tuples, "
      "and it is a new list even when one side is empty.",
      "merge_runs",
      [eq("merge_runs([1,3,5],[2,4,6])", "[1,2,3,4,5,6]"),
       eq("merge_runs([5,3,1],[6,4,2], descending=True)", "[6,5,4,3,2,1]"),
       blk("r = merge_runs([1],[1.0])", "assert type(r[0]) is int and type(r[1]) is float"),
       blk("r = merge_runs([2.0],[2], descending=True)", "assert type(r[0]) is float and type(r[1]) is int"),
       eq("merge_runs([1,1],[1])", "[1,1,1]"),
       eq("merge_runs([1,1,2],[1,3,3], unique=True)", "[1,2,3]"),
       blk("r = merge_runs([1],[1.0], unique=True)", "assert r == [1] and type(r[0]) is int"),
       eq("merge_runs([None,1,None],[2,None])", "[1,2]"),
       eq("merge_runs(None,[1])", "[1]"),
       eq("merge_runs((1,2),(3,))", "[1,2,3]"),
       eq("merge_runs([1,2.5],[2,3])", "[1,2,2.5,3]"),
       eq("merge_runs(['B','a'],['C'])", "['B','C','a']"),
       raises("merge_runs([2,1],[1])", "ValueError", "a is not sorted"),
       raises("merge_runs([1],[3,2])", "ValueError", "b is not sorted"),
       raises("merge_runs([2,1],[3,2])", "ValueError", "a is not sorted"),
       raises("merge_runs([1,2],[], descending=True)", "ValueError", "a is not sorted"),
       blk("b = [1,2]", "r = merge_runs([], b)", "assert r == [1,2] and r is not b", "assert merge_runs([], []) == []",
           "a = [3,1]", "try:", "    merge_runs(a, [])", "except ValueError:", "    pass", "assert a == [3,1]")],
      """
def merge_runs(a, b, descending=False, unique=False):
    def prep(x, name):
        xs = [v for v in (x or []) if v is not None]
        for p, q in zip(xs, xs[1:]):
            if (p < q) if descending else (p > q):
                raise ValueError(f'{name} is not sorted')
        return xs

    xs = prep(a, 'a')
    ys = prep(b, 'b')
    out = []
    i = j = 0
    while i < len(xs) and j < len(ys):
        take_b = (ys[j] > xs[i]) if descending else (ys[j] < xs[i])
        if take_b:
            out.append(ys[j])
            j += 1
        else:
            out.append(xs[i])
            i += 1
    out.extend(xs[i:])
    out.extend(ys[j:])
    if unique:
        ded = []
        for v in out:
            if not ded or not (ded[-1] == v):
                ded.append(v)
        out = ded
    return out
"""),
    # ---- DC6 dates / test ----------------------------------------------------------------------
    T("DC6", "dates", "test",
      "Write `next_anniversary(born, today, include_today=True)`. born and today are ISO 'YYYY-MM-DD' strings and the function "
      "returns the ISO string of the next anniversary of born on or after today, or strictly after today when include_today is False. "
      "An anniversary is the same month and day as born in a later year; the birth date itself never counts, so the earliest possible "
      "anniversary is in the year after born's year, even if today is before born or equal to it. "
      "If born is February 29, the anniversary falls on Feb 29 in leap years and on Feb 28 in other years (century years such as "
      "2100 are not leap years unless divisible by 400). "
      "When today is itself an anniversary, the answer is today if include_today is True and the following year's anniversary otherwise. "
      "If this year's anniversary has already passed, the answer is in the next year, including across a December to January boundary. "
      "Both arguments must be exactly zero-padded 'YYYY-MM-DD' real calendar dates, with no spaces, otherwise raise "
      "ValueError with the message 'invalid date'; born is checked first. The return value is always a str.",
      "next_anniversary",
      [eq("next_anniversary('1990-05-17', '2024-05-16')", "'2024-05-17'"),
       eq("next_anniversary('1990-05-17', '2024-05-17')", "'2024-05-17'"),
       eq("next_anniversary('1990-05-17', '2024-05-17', include_today=False)", "'2025-05-17'"),
       eq("next_anniversary('1990-05-17', '2024-05-18')", "'2025-05-17'"),
       eq("next_anniversary('2000-01-01', '2024-12-31')", "'2025-01-01'"),
       eq("next_anniversary('1999-12-31', '2024-12-31', False)", "'2025-12-31'"),
       eq("next_anniversary('2030-03-03', '2024-01-01')", "'2031-03-03'"),
       eq("next_anniversary('2024-03-03', '2024-03-03')", "'2025-03-03'"),
       eq("next_anniversary('2024-03-03', '2024-03-02', include_today=False)", "'2025-03-03'"),
       eq("next_anniversary('2000-02-29', '2023-03-01')", "'2024-02-29'"),
       eq("next_anniversary('2000-02-29', '2023-02-27')", "'2023-02-28'"),
       eq("next_anniversary('2000-02-29', '2023-02-28')", "'2023-02-28'"),
       eq("next_anniversary('2000-02-29', '2023-02-28', False)", "'2024-02-29'"),
       eq("next_anniversary('2000-02-29', '2024-02-29', False)", "'2025-02-28'"),
       eq("next_anniversary('2000-02-29', '2000-02-29')", "'2001-02-28'"),
       eq("next_anniversary('2000-02-29', '2100-01-01')", "'2100-02-28'"),
       eq("next_anniversary('1990-05-17', '2024-05-16').__class__.__name__", "'str'"),
       raises("next_anniversary('2023-02-29', '2024-01-01')", "ValueError", "invalid date"),
       raises("next_anniversary('1990-5-17', '2024-01-01')", "ValueError", "invalid date"),
       raises("next_anniversary(' 1990-05-17', '2024-01-01')", "ValueError", "invalid date"),
       raises("next_anniversary('1990-05-17', '2024-13-01')", "ValueError", "invalid date"),
       raises("next_anniversary('1990-05-17', '2024/01/01')", "ValueError", "invalid date")],
      """
import datetime
import re


def _p(s):
    if not isinstance(s, str) or not re.fullmatch(r'\\d{4}-\\d{2}-\\d{2}', s):
        raise ValueError('invalid date')
    try:
        return datetime.date(int(s[:4]), int(s[5:7]), int(s[8:]))
    except ValueError:
        raise ValueError('invalid date') from None


def next_anniversary(born, today, include_today=True):
    b = _p(born)
    t = _p(today)
    y = max(t.year, b.year + 1)
    while True:
        try:
            cand = datetime.date(y, b.month, b.day)
        except ValueError:
            cand = datetime.date(y, 2, 28)
        if cand > t or (cand == t and include_today):
            return cand.isoformat()
        y += 1
"""),
    # ---- DC7 ordering / test -------------------------------------------------------------------
    T("DC7", "ordering", "test",
      "Write `sort_files(names)`. names is a list of path-like strings; return a new list of the original strings in listing "
      "order without modifying the input. A name ending in '/' is a directory and all directories come before all files. "
      "Names that are empty, or are nothing but slashes, are dropped, and exact duplicate strings are removed keeping the first "
      "('a' and 'a/' are different names). "
      "Within directories and within files separately, names that do not start with '.' come before names that do (hidden). "
      "To build the sort key, remove trailing slashes, then remove one leading '.' from hidden names, giving the core. "
      "For a file, the extension is the text after the last '.' of the core, but only when that dot is not the first or the last "
      "character of the core, otherwise there is no extension; the stem is the core without '.' and extension, so "
      "'archive.tar.gz' has stem 'archive.tar' and extension 'gz'. A directory never has an extension and its stem is its whole core. "
      "Order by stem ignoring case, then by extension ignoring case (no extension first), and if still tied by the exact original "
      "string by plain code point. An empty input gives [].",
      "sort_files",
      [eq("sort_files(['b.txt','a/','c/','a.txt'])", "['a/','c/','a.txt','b.txt']"),
       eq("sort_files(['.git/','src/','.env','app.py'])", "['src/','.git/','app.py','.env']"),
       eq("sort_files(['b.txt','A.txt','c.txt'])", "['A.txt','b.txt','c.txt']"),
       eq("sort_files(['file.txt','file.md','file2.md','file'])", "['file','file.md','file.txt','file2.md']"),
       eq("sort_files(['file-x.txt','file.txt'])", "['file.txt','file-x.txt']"),
       eq("sort_files(['archive.zip','archive.tar.gz'])", "['archive.zip','archive.tar.gz']"),
       eq("sort_files(['name.','name'])", "['name','name.']"),
       eq("sort_files(['.bashrc','.Alpha','.config.json'])", "['.Alpha','.bashrc','.config.json']"),
       eq("sort_files(['.zdir/','a.txt','.adir/'])", "['.adir/','.zdir/','a.txt']"),
       eq("sort_files(['.a/','b/'])", "['b/','.a/']"),
       eq("sort_files(['a.TXT','a.txt','A.txt'])", "['A.txt','a.TXT','a.txt']"),
       eq("sort_files(['a','a','a/','a/'])", "['a/','a']"),
       eq("sort_files(['', '/', '//', 'x'])", "['x']"),
       eq("sort_files(['v1.2/','v1/'])", "['v1/','v1.2/']"),
       eq("sort_files(['.env.local','.env'])", "['.env','.env.local']"),
       blk("xs = ['b','a/']", "r = sort_files(xs)", "assert r == ['a/','b'] and xs == ['b','a/'] and r is not xs",
           "assert sort_files([]) == []")],
      """
def sort_files(names):
    seen = set()
    items = []
    for n in names:
        if n in seen:
            continue
        seen.add(n)
        base = n.rstrip('/')
        if not base:
            continue
        is_dir = n.endswith('/')
        hidden = base.startswith('.')
        core = base[1:] if hidden else base
        stem, ext = core, ''
        if not is_dir:
            dot = core.rfind('.')
            if 0 < dot < len(core) - 1:
                stem, ext = core[:dot], core[dot + 1:]
        items.append(((0 if is_dir else 1, 1 if hidden else 0, stem.casefold(), ext.casefold(), n), n))
    items.sort(key=lambda x: x[0])
    return [n for _, n in items]
"""),
    # ---- DC8 dates / test ----------------------------------------------------------------------
    T("DC8", "dates", "test",
      "Write `longest_streak(dates, gap_ok=0)`. dates is a list of ISO 'YYYY-MM-DD' strings in any order, possibly with repeats, "
      "and the function never modifies it. First check gap_ok: a negative value raises ValueError('gap_ok must be >= 0'). "
      "Then every element must be exactly a zero-padded 'YYYY-MM-DD' string for a real calendar date (no spaces, impossible days "
      "such as Feb 30, or non-strings), otherwise raise ValueError('invalid date'); every element is checked, even ones that would not matter. "
      "Repeated dates count once. Sort the distinct dates; a streak is a maximal run in which each date is at most gap_ok + 1 calendar "
      "days after the previous one, so with gap_ok=0 only consecutive days count, and month ends, year ends and leap days are handled by "
      "the real calendar. The streak length is the number of distinct dates in the run, not the days it spans. "
      "Return a tuple (first_date, last_date, length) of the longest streak, with the dates as ISO strings. "
      "If several streaks share the longest length, return the one that starts earliest. Empty input returns None.",
      "longest_streak",
      [eq("longest_streak(['2024-02-27','2024-02-28','2024-02-29','2024-03-01'])", "('2024-02-27','2024-03-01',4)"),
       eq("longest_streak(['2023-02-28','2023-03-01'])", "('2023-02-28','2023-03-01',2)"),
       eq("longest_streak(['2023-02-27','2023-03-01'])", "('2023-02-27','2023-02-27',1)"),
       eq("longest_streak(['2024-05-03','2024-05-01','2024-05-02','2024-05-02'])", "('2024-05-01','2024-05-03',3)"),
       eq("longest_streak(['2024-01-21','2024-01-20','2024-01-11','2024-01-10'])", "('2024-01-10','2024-01-11',2)"),
       eq("longest_streak(['2023-12-31','2024-01-01'])", "('2023-12-31','2024-01-01',2)"),
       eq("longest_streak([])", "None"),
       eq("longest_streak(['2024-07-04','2024-07-04'])", "('2024-07-04','2024-07-04',1)"),
       eq("longest_streak(['2024-01-01','2024-01-03','2024-01-04','2024-01-07'])", "('2024-01-03','2024-01-04',2)"),
       eq("longest_streak(['2024-01-01','2024-01-03','2024-01-04','2024-01-07'], gap_ok=1)", "('2024-01-01','2024-01-04',3)"),
       eq("longest_streak(['2024-01-01','2024-01-03','2024-01-04','2024-01-07'], 2)", "('2024-01-01','2024-01-07',4)"),
       raises("longest_streak([], -1)", "ValueError", "gap_ok must be >= 0"),
       raises("longest_streak(['2024-01-01','bad'])", "ValueError", "invalid date"),
       raises("longest_streak(['2024-02-30'])", "ValueError", "invalid date"),
       raises("longest_streak(['2024-1-05'])", "ValueError", "invalid date"),
       raises("longest_streak([' 2024-01-01'])", "ValueError", "invalid date"),
       raises("longest_streak(['2024-01-01', 5])", "ValueError", "invalid date"),
       blk("xs = ['2024-01-02','2024-01-01']", "r = longest_streak(xs)", "assert xs == ['2024-01-02','2024-01-01']",
           "assert isinstance(r, tuple) and r == ('2024-01-01','2024-01-02',2)")],
      """
import datetime
import re


def longest_streak(dates, gap_ok=0):
    if gap_ok < 0:
        raise ValueError('gap_ok must be >= 0')
    parsed = set()
    for s in dates:
        if not isinstance(s, str) or not re.fullmatch(r'\\d{4}-\\d{2}-\\d{2}', s):
            raise ValueError('invalid date')
        try:
            parsed.add(datetime.date(int(s[:4]), int(s[5:7]), int(s[8:])))
        except ValueError:
            raise ValueError('invalid date') from None
    ds = sorted(parsed)
    if not ds:
        return None
    best = None
    start = 0
    for i in range(1, len(ds) + 1):
        if i == len(ds) or (ds[i] - ds[i - 1]).days > gap_ok + 1:
            run = (ds[start].isoformat(), ds[i - 1].isoformat(), i - start)
            if best is None or run[2] > best[2]:
                best = run
            start = i
    return best
"""),
]
