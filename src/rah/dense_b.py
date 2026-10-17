# agent: claude-code  2026-10-17
"""8 dense invented tasks (families errors, format). Each spec packs 8-10 explicit requirements, stated once;
a strong model typically misses at least one. Nothing here is copied from a public benchmark or other suites.

Splits: DB1-3 train, DB4-5 val, DB6-8 test.
"""
from __future__ import annotations

from .suite import Task
from .suite_data import T, blk, eq, raises

def _row(d: str, q: str, u: str, t: str) -> str:
    """Expected invoice line, as Python source for a string literal."""
    return repr(f"{d:<20} {q:>4} {u:>10} {t:>12}")


DENSE_B: list[Task] = [
    # ---- DB1 errors / train ---------------------------------------------------------------
    T("DB1", "errors", "train",
      "Write `apply_transfer(accounts, src, dst, amount)`. accounts is a dict mapping account name to an int balance in cents. "
      "Checks run in exactly this order and the first failure raises: amount that is not an int (a bool counts as not an int) "
      "raises TypeError('amount must be an int'); amount <= 0 raises ValueError('amount must be positive'); src == dst raises "
      "ValueError('cannot transfer to same account'); src not in accounts raises KeyError('unknown account: <name>'), and only "
      "after that is dst checked the same way; then an account whose name starts with '!' is frozen, and if src is frozen (checked "
      "first) or dst is frozen the call raises PermissionError('account frozen: <name>'); finally if accounts[src] < amount it raises "
      "ValueError('insufficient funds: need <amount>, have <balance>') using the plain integers. A transfer of exactly the whole "
      "balance is allowed. On success, modify the accounts dict in place (src decreases, dst increases) and return the tuple "
      "(new_src_balance, new_dst_balance). When any error is raised the dict must be left completely unchanged.",
      "apply_transfer",
      [blk("a = {'x': 100, 'y': 5}", "r = apply_transfer(a, 'x', 'y', 40)", "assert r == (60, 45), r", "assert a == {'x': 60, 'y': 45}, a"),
       blk("a = {'x': 100, 'y': 5}", "assert apply_transfer(a, 'x', 'y', 100) == (0, 105)"),
       raises("apply_transfer({'x': 9, 'y': 1}, 'x', 'y', True)", "TypeError", "amount must be an int"),
       raises("apply_transfer({'x': 9, 'y': 1}, 'x', 'y', 2.0)", "TypeError", "amount must be an int"),
       raises("apply_transfer({'x': 9, 'y': 1}, 'x', 'x', 0.0)", "TypeError", "amount must be an int"),
       raises("apply_transfer({'x': 9, 'y': 1}, 'x', 'x', 0)", "ValueError", "amount must be positive"),
       raises("apply_transfer({'x': 9, 'y': 1}, 'x', 'y', -3)", "ValueError", "amount must be positive"),
       raises("apply_transfer({}, 'q', 'q', 5)", "ValueError", "cannot transfer to same account"),
       raises("apply_transfer({'y': 1}, 'ghost', 'nobody', 5)", "KeyError", "unknown account: ghost"),
       raises("apply_transfer({'x': 9}, 'x', 'nobody', 5)", "KeyError", "unknown account: nobody"),
       raises("apply_transfer({'!x': 0, '!y': 50}, '!x', '!y', 5)", "PermissionError", "account frozen: !x"),
       raises("apply_transfer({'x': 50, '!y': 1}, 'x', '!y', 5)", "PermissionError", "account frozen: !y"),
       raises("apply_transfer({'x': 3, 'y': 1}, 'x', 'y', 5)", "ValueError", "insufficient funds: need 5, have 3"),
       blk("a = {'x': 3, 'y': 1}", "try:", "    apply_transfer(a, 'x', 'y', 5)", "except ValueError:", "    pass",
           "assert a == {'x': 3, 'y': 1}, a")],
      """
def apply_transfer(accounts, src, dst, amount):
    if type(amount) is not int:
        raise TypeError('amount must be an int')
    if amount <= 0:
        raise ValueError('amount must be positive')
    if src == dst:
        raise ValueError('cannot transfer to same account')
    for n in (src, dst):
        if n not in accounts:
            raise KeyError(f'unknown account: {n}')
    for n in (src, dst):
        if n.startswith('!'):
            raise PermissionError(f'account frozen: {n}')
    if accounts[src] < amount:
        raise ValueError(f'insufficient funds: need {amount}, have {accounts[src]}')
    accounts[src] -= amount
    accounts[dst] += amount
    return (accounts[src], accounts[dst])
"""),

    # ---- DB2 format / train ---------------------------------------------------------------
    T("DB2", "format", "train",
      "Write `invoice_line(desc, qty, unit_cents)` returning one string. First validate: qty must be an int (not a bool) from 1 to 999 "
      "inclusive, otherwise raise ValueError('qty must be 1-999'); only then check unit_cents, which must be an int (not a bool), "
      "otherwise raise TypeError('unit_cents must be an int'). The description is stripped of surrounding whitespace; if it is None or "
      "empty after stripping it becomes '(none)'. A description longer than 20 characters is cut to its first 19 characters followed by "
      "'~'; the result is left-justified and padded with spaces to 20 characters. Money is written as '$' followed by the whole amount "
      "with comma thousands separators, a '.', and exactly two cent digits, so 123456 cents is '$1,234.56'; a negative amount puts the "
      "minus sign first, as '-$1.50'. The line has four columns joined by a single space: the description column (20 wide), the quantity "
      "written as 'x' followed by the number and right-aligned in 4 characters, the unit price right-aligned in 10 characters, and the "
      "line total qty * unit_cents right-aligned in 12 characters. A value wider than its column is never truncated, and the line has no "
      "trailing whitespace.",
      "invoice_line",
      [eq("invoice_line('Widget', 3, 1250)", _row("Widget", "x3", "$12.50", "$37.50")),
       eq("invoice_line('  Bolt  ', 12, 5)", _row("Bolt", "x12", "$0.05", "$0.60")),
       eq("invoice_line(None, 1, 100)", _row("(none)", "x1", "$1.00", "$1.00")),
       eq("invoice_line('   ', 1, 100)", _row("(none)", "x1", "$1.00", "$1.00")),
       eq("invoice_line('A' * 20, 1, 100)", _row("A" * 20, "x1", "$1.00", "$1.00")),
       eq("invoice_line('B' * 21, 1, 100)", _row("B" * 19 + "~", "x1", "$1.00", "$1.00")),
       eq("invoice_line('  ' + 'C' * 20 + '  ', 1, 100)", _row("C" * 20, "x1", "$1.00", "$1.00")),
       eq("invoice_line('Gold', 999, 123456)", _row("Gold", "x999", "$1,234.56", "$1,233,325.44")),
       eq("invoice_line('Refund', 2, -150)", _row("Refund", "x2", "-$1.50", "-$3.00")),
       eq("invoice_line('Zero', 5, 0)", _row("Zero", "x5", "$0.00", "$0.00")),
       eq("invoice_line('Big', 1, 123456789)", _row("Big", "x1", "$1,234,567.89", "$1,234,567.89")),
       raises("invoice_line('x', 0, 100)", "ValueError", "qty must be 1-999"),
       raises("invoice_line('x', 1000, 100)", "ValueError", "qty must be 1-999"),
       raises("invoice_line('x', True, 100)", "ValueError", "qty must be 1-999"),
       raises("invoice_line('x', '2', 'bad')", "ValueError", "qty must be 1-999"),
       raises("invoice_line('x', 2, 1.5)", "TypeError", "unit_cents must be an int"),
       raises("invoice_line('x', 2, True)", "TypeError", "unit_cents must be an int")],
      """
def invoice_line(desc, qty, unit_cents):
    if type(qty) is not int or not 1 <= qty <= 999:
        raise ValueError('qty must be 1-999')
    if type(unit_cents) is not int:
        raise TypeError('unit_cents must be an int')
    d = (desc or '').strip() if desc is not None else ''
    if not d:
        d = '(none)'
    if len(d) > 20:
        d = d[:19] + '~'

    def money(c):
        s = f'{abs(c) // 100:,}.{abs(c) % 100:02d}'
        return ('-$' if c < 0 else '$') + s

    return f'{d:<20} {"x" + str(qty):>4} {money(unit_cents):>10} {money(qty * unit_cents):>12}'.rstrip()
"""),
    # ---- DB3 errors / train ---------------------------------------------------------------
    T("DB3", "errors", "train",
      "Write `parse_pages(spec, max_page)` that turns a page selection like '1-3,7,10-12' into a sorted list of unique ints. "
      "If spec is not a str raise TypeError('spec must be a string'); this is checked before max_page, which must be an int (not a bool) "
      "of at least 1, otherwise ValueError('max_page must be at least 1'). A spec that is empty or only whitespace returns []. Otherwise "
      "split on commas and process the items strictly left to right, raising for the first problem found; whitespace around an item and "
      "around its dash is ignored. An empty item (as in '1,,2' or a trailing comma) raises ValueError('empty item at position N') with N "
      "the 1-based position of the item. An item that is not either ASCII digits or ASCII digits, a dash and ASCII digits (so '-3', "
      "'1-2-3', '1.5' and 'x' are all bad) raises ValueError(\"bad item: 'ITEM'\") with the item stripped at both ends but otherwise as "
      "written. For a range whose start is greater than its end raise ValueError(\"descending range: 'ITEM'\"); this check comes before "
      "any bounds check. Finally any number that is 0 or greater than max_page raises ValueError('out of range: N'), testing the start "
      "of a range before its end. The result has each page once, in ascending order.",
      "parse_pages",
      [eq("parse_pages('1-3,7,10-12', 20)", "[1,2,3,7,10,11,12]"),
       eq("parse_pages(' 3 , 1 ,2,2, 4 - 5 ', 9)", "[1,2,3,4,5]"),
       eq("parse_pages('', 5)", "[]"), eq("parse_pages('   ', 5)", "[]"),
       eq("parse_pages('5-5', 5)", "[5]"),
       raises("parse_pages(None, 0)", "TypeError", "spec must be a string"),
       raises("parse_pages('1', 0)", "ValueError", "max_page must be at least 1"),
       raises("parse_pages('1', True)", "ValueError", "max_page must be at least 1"),
       raises("parse_pages('1,,2', 9)", "ValueError", "empty item at position 2"),
       raises("parse_pages(',', 9)", "ValueError", "empty item at position 1"),
       raises("parse_pages('1,2,', 9)", "ValueError", "empty item at position 3"),
       raises("parse_pages('1, -3 ,x', 9)", "ValueError", "bad item: '-3'"),
       raises("parse_pages('1-2-3', 9)", "ValueError", "bad item: '1-2-3'"),
       raises("parse_pages('1.5', 9)", "ValueError", "bad item: '1.5'"),
       raises("parse_pages('x,0', 9)", "ValueError", "bad item: 'x'"),
       raises("parse_pages('0,x', 9)", "ValueError", "out of range: 0"),
       raises("parse_pages('2- 9, 5 - 2', 5)", "ValueError", "out of range: 9"),
       raises("parse_pages(' 5 - 2 ', 3)", "ValueError", "descending range: '5 - 2'"),
       raises("parse_pages('0-3', 9)", "ValueError", "out of range: 0"),
       raises("parse_pages('4,\\u0663', 9)", "ValueError", "bad item: '\u0663'")],
      """
import re


def parse_pages(spec, max_page):
    if not isinstance(spec, str):
        raise TypeError('spec must be a string')
    if type(max_page) is not int or max_page < 1:
        raise ValueError('max_page must be at least 1')
    if not spec.strip():
        return []
    out = set()
    for pos, raw in enumerate(spec.split(','), 1):
        item = raw.strip()
        if not item:
            raise ValueError(f'empty item at position {pos}')
        m = re.fullmatch(r'([0-9]+)\\s*(?:-\\s*([0-9]+))?', item)
        if not m:
            raise ValueError(f"bad item: '{item}'")
        a = int(m.group(1))
        b = int(m.group(2)) if m.group(2) is not None else a
        if a > b:
            raise ValueError(f"descending range: '{item}'")
        for n in (a, b):
            if n < 1 or n > max_page:
                raise ValueError(f'out of range: {n}')
        out.update(range(a, b + 1))
    return sorted(out)
"""),

    # ---- DB4 format / val -----------------------------------------------------------------
    T("DB4", "format", "val",
      "Write `render_agenda(slots)` where slots is a list of (name, start, end) tuples with start and end in whole minutes after midnight. "
      "Clean each name first: strip it, collapse every run of internal whitespace to one space, and use '(untitled)' if it is None or empty. "
      "If any slot has start < 0 or end > 1440 raise ValueError('slot out of day: NAME') with the cleaned name, and do this check for all "
      "slots before anything else; after that silently drop slots with end <= start. If nothing remains return exactly 'No events'. "
      "Otherwise the first line is 'Agenda (N events)' where N counts the remaining slots, written 'Agenda (1 event)' when N is 1. "
      "Remaining slots follow one per line, sorted by start, then end, then cleaned name. A line is a prefix, then 'HH:MM - HH:MM', then two "
      "spaces, then the name, then a space and the duration in parentheses. Times are 24-hour with zero padding, and 1440 is written '24:00'. "
      "The duration is '1h30m' for 90 minutes, '45m' for 45 and '2h' for 120 (zero parts omitted). The prefix is '! ' when the slot starts "
      "strictly before the latest end among all slots sorted before it (slots that merely touch are fine), and two spaces otherwise. "
      "Lines are joined with newlines and there is no trailing newline.",
      "render_agenda",
      [eq("render_agenda([])", "'No events'"),
       eq("render_agenda([('x', 60, 60), ('y', 90, 80)])", "'No events'"),
       eq("render_agenda([('Standup', 540, 555)])", "'Agenda (1 event)\\n  09:00 - 09:15  Standup (15m)'"),
       eq("render_agenda([('B', 600, 720), ('A', 540, 630)])",
          "'Agenda (2 events)\\n  09:00 - 10:30  A (1h30m)\\n! 10:00 - 12:00  B (2h)'"),
       eq("render_agenda([('A', 540, 600), ('B', 600, 660)])",
          "'Agenda (2 events)\\n  09:00 - 10:00  A (1h)\\n  10:00 - 11:00  B (1h)'"),
       eq("render_agenda([('Late', 1380, 1440)])", "'Agenda (1 event)\\n  23:00 - 24:00  Late (1h)'"),
       eq("render_agenda([('  Team   sync \\n now ', 0, 5), (None, 0, 5), ('', 1, 3)])",
          "'Agenda (3 events)\\n  00:00 - 00:05  (untitled) (5m)\\n! 00:00 - 00:05  Team sync now (5m)\\n! 00:01 - 00:03  (untitled) (2m)'"),
       eq("render_agenda([('Z', 600, 600), ('A', 600, 601), ('B', 600, 601)])",
          "'Agenda (2 events)\\n  10:00 - 10:01  A (1m)\\n! 10:00 - 10:01  B (1m)'"),
       eq("render_agenda([('Long', 0, 600), ('Mid', 100, 200), ('After', 300, 400), ('Free', 600, 601)])",
          "'Agenda (4 events)\\n  00:00 - 10:00  Long (10h)\\n! 01:40 - 03:20  Mid (1h40m)\\n! 05:00 - 06:40  After (1h40m)\\n  10:00 - 10:01  Free (1m)'"),
       raises("render_agenda([('ok', 1, 2), ('  Over   night ', 1400, 1441)])", "ValueError", "slot out of day: Over night"),
       raises("render_agenda([('a', 5, 10), ('neg', -5, -10)])", "ValueError", "slot out of day: neg"),
       raises("render_agenda([('zero', 0, 0), (None, -1, 5)])", "ValueError", "slot out of day: (untitled)"),
       eq("render_agenda([('Ok', 0, 1440)])", "'Agenda (1 event)\\n  00:00 - 24:00  Ok (24h)'")],
      """
def render_agenda(slots):
    clean = []
    for name, s, e in slots:
        n = ' '.join(name.split()) if name else ''
        n = n or '(untitled)'
        clean.append((n, s, e))
    for n, s, e in clean:
        if s < 0 or e > 1440:
            raise ValueError(f'slot out of day: {n}')
    keep = sorted(((s, e, n) for n, s, e in clean if e > s))
    if not keep:
        return 'No events'

    def hm(m):
        return f'{m // 60:02d}:{m % 60:02d}'

    def dur(m):
        h, r = divmod(m, 60)
        return (f'{h}h' if h else '') + (f'{r}m' if r else '')

    lines = [f'Agenda ({len(keep)} event{"" if len(keep) == 1 else "s"})']
    latest = None
    for s, e, n in keep:
        prefix = '! ' if latest is not None and s < latest else '  '
        lines.append(f'{prefix}{hm(s)} - {hm(e)}  {n} ({dur(e - s)})')
        latest = e if latest is None else max(latest, e)
    return '\\n'.join(lines)
"""),
    # ---- DB5 errors / val -----------------------------------------------------------------
    T("DB5", "errors", "val",
      "Write `check_job(cfg)` that validates a job config and returns a new normalized dict, never changing the input. Checks run in this "
      "exact order and the first failure raises: cfg not a dict raises TypeError('config must be a dict'); a missing 'name' key raises "
      "KeyError('missing key: name'); any keys other than name, retries, timeout and mode raise ValueError('unknown keys: ' + the "
      "offending keys sorted alphabetically and joined with ', '); then the fields are checked in the order name, retries, timeout, mode. "
      "name must be a str, else TypeError('name must be a string'); after stripping it must be 1 to 30 characters, else "
      "ValueError('name must be 1-30 characters'), and the returned name is the stripped one. retries is optional, defaults to 3, must be "
      "an int and not a bool, else TypeError('retries must be an int'), and must be 0 to 10 inclusive, else ValueError('retries must be "
      "between 0 and 10'). timeout is optional, defaults to 30.0, must be an int or float and not a bool, else TypeError('timeout must be "
      "a number'), and must be greater than 0, else ValueError('timeout must be positive'); the returned timeout is always a float. mode "
      "is optional, defaults to 'safe', must be a str, else TypeError('mode must be a string'), and compared case-insensitively after "
      "stripping must be 'fast' or 'safe', else ValueError('mode must be one of: fast, safe'); the returned mode is lowercase. The "
      "returned dict has exactly the keys name, retries, timeout and mode.",
      "check_job",
      [eq("check_job({'name': ' etl '})", "{'name': 'etl', 'retries': 3, 'timeout': 30.0, 'mode': 'safe'}"),
       eq("check_job({'name': 'a', 'retries': 0, 'timeout': 5, 'mode': ' FAST '})",
          "{'name': 'a', 'retries': 0, 'timeout': 5.0, 'mode': 'fast'}"),
       blk("c = {'name': ' z ', 'timeout': 2}", "r = check_job(c)", "assert c == {'name': ' z ', 'timeout': 2}, c",
           "assert isinstance(r['timeout'], float) and r is not c"),
       eq("check_job({'name': 'x' * 30, 'retries': 10})['retries']", "10"),
       raises("check_job([('name', 'a')])", "TypeError", "config must be a dict"),
       raises("check_job({'retries': 'bad', 'zzz': 1})", "KeyError", "missing key: name"),
       raises("check_job({'name': 5, 'zeta': 1, 'alpha': 2})", "ValueError", "unknown keys: alpha, zeta"),
       raises("check_job({'name': 5})", "TypeError", "name must be a string"),
       raises("check_job({'name': '   ', 'retries': 'x'})", "ValueError", "name must be 1-30 characters"),
       raises("check_job({'name': 'x' * 31})", "ValueError", "name must be 1-30 characters"),
       raises("check_job({'name': 'a', 'retries': True})", "TypeError", "retries must be an int"),
       raises("check_job({'name': 'a', 'retries': 2.0, 'timeout': -1})", "TypeError", "retries must be an int"),
       raises("check_job({'name': 'a', 'retries': 11, 'timeout': 'x'})", "ValueError", "retries must be between 0 and 10"),
       raises("check_job({'name': 'a', 'retries': -1})", "ValueError", "retries must be between 0 and 10"),
       raises("check_job({'name': 'a', 'timeout': '5'})", "TypeError", "timeout must be a number"),
       raises("check_job({'name': 'a', 'timeout': False, 'mode': 3})", "TypeError", "timeout must be a number"),
       raises("check_job({'name': 'a', 'timeout': 0, 'mode': 3})", "ValueError", "timeout must be positive"),
       raises("check_job({'name': 'a', 'mode': 3})", "TypeError", "mode must be a string"),
       raises("check_job({'name': 'a', 'mode': 'turbo'})", "ValueError", "mode must be one of: fast, safe")],
      """
def check_job(cfg):
    if not isinstance(cfg, dict):
        raise TypeError('config must be a dict')
    if 'name' not in cfg:
        raise KeyError('missing key: name')
    extra = sorted(set(cfg) - {'name', 'retries', 'timeout', 'mode'}, key=str)
    if extra:
        raise ValueError('unknown keys: ' + ', '.join(str(k) for k in extra))
    name = cfg['name']
    if not isinstance(name, str):
        raise TypeError('name must be a string')
    name = name.strip()
    if not 1 <= len(name) <= 30:
        raise ValueError('name must be 1-30 characters')
    retries = cfg.get('retries', 3)
    if type(retries) is not int:
        raise TypeError('retries must be an int')
    if not 0 <= retries <= 10:
        raise ValueError('retries must be between 0 and 10')
    timeout = cfg.get('timeout', 30.0)
    if type(timeout) not in (int, float):
        raise TypeError('timeout must be a number')
    if timeout <= 0:
        raise ValueError('timeout must be positive')
    mode = cfg.get('mode', 'safe')
    if not isinstance(mode, str):
        raise TypeError('mode must be a string')
    mode = mode.strip().lower()
    if mode not in ('fast', 'safe'):
        raise ValueError('mode must be one of: fast, safe')
    return {'name': name, 'retries': retries, 'timeout': float(timeout), 'mode': mode}
"""),

    # ---- DB6 format / test ----------------------------------------------------------------
    T("DB6", "format", "test",
      "Write `render_table(headers, rows)` returning a Markdown table as a string. If headers is empty raise ValueError('headers required'); "
      "this comes before looking at rows. A row shorter than headers is padded with empty cells; a row longer than headers raises "
      "ValueError('row N has too many cells') with N the 1-based row number, for the first such row. Convert each cell to text: None "
      "becomes '', True and False become 'yes' and 'no', a float is written with exactly 2 decimals, and anything else uses str(). Then "
      "escape every '|' in the text as '\\|' and replace every newline with a single space. A column is numeric if it has at least one "
      "cell and every non-None cell in it is an int or float (a bool is not numeric); numeric columns are right-aligned, including the "
      "header, and all others left-aligned. Each column is as wide as its longest text (header included, measured after conversion and "
      "escaping) but at least 3. A line is '| ' + cells padded to width and joined by ' | ' + ' |'. The second line is the separator: "
      "'|' + the per-column pieces joined by '|' + '|', where a left-aligned column piece is width+2 dashes and a right-aligned column "
      "piece is width+1 dashes followed by ':'. Lines are joined with newlines with no trailing newline, and with no rows only the header "
      "and separator lines appear.",
      "render_table",
      [eq("render_table(['a', 'b'], [])", repr("| a   | b   |\n|-----|-----|")),
       eq("render_table(['Name', 'Qty'], [['pen', 3], ['notebook', 12]])",
          repr("| Name     | Qty |\n|----------|----:|\n| pen      |   3 |\n| notebook |  12 |")),
       eq("render_table(['x', 'y'], [[1.5, 'a'], [3, None]])",
          repr("|    x | y   |\n|-----:|-----|\n| 1.50 | a   |\n|    3 |     |")),
       eq("render_table(['k', 'ok'], [['a', True], ['b', False]])",
          repr("| k   | ok  |\n|-----|-----|\n| a   | yes |\n| b   | no  |")),
       eq("render_table(['a', 'b', 'c'], [[1], []])",
          repr("|   a | b   | c   |\n|----:|-----|-----|\n|   1 |     |     |\n|     |     |     |")),
       eq("render_table(['t'], [['x|y'], ['l1\\nl2']])",
          repr("| t     |\n|-------|\n| x\\|y  |\n| l1 l2 |")),
       eq("render_table(['n'], [[None], [None]])", repr("| n   |\n|-----|\n|     |\n|     |")),
       eq("render_table(['n'], [[True], [2]])", repr("| n   |\n|-----|\n| yes |\n| 2   |")),
       eq("render_table(['n'], [[2], [None], [-10.5]])", repr("|      n |\n|-------:|\n|      2 |\n|        |\n| -10.50 |")),
       raises("render_table([], [['a']])", "ValueError", "headers required"),
       raises("render_table([], 5)", "ValueError", "headers required"),
       raises("render_table(['a'], [['x'], ['y', 'z'], ['1', '2', '3']])", "ValueError", "row 2 has too many cells")],
      """
def render_table(headers, rows):
    if not headers:
        raise ValueError('headers required')
    n = len(headers)
    grid = []
    raw = []
    for i, row in enumerate(rows, 1):
        if len(row) > n:
            raise ValueError(f'row {i} has too many cells')
        row = list(row) + [None] * (n - len(row))
        raw.append(row)

    def text(c):
        if c is None:
            s = ''
        elif isinstance(c, bool):
            s = 'yes' if c else 'no'
        elif isinstance(c, float):
            s = f'{c:.2f}'
        else:
            s = str(c)
        return s.replace('|', '\\\\|').replace('\\n', ' ')

    grid = [[text(c) for c in row] for row in raw]
    head = [text(h) for h in headers]
    right = []
    for j in range(n):
        vals = [r[j] for r in raw if r[j] is not None]
        right.append(bool(vals) and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in vals))
    widths = [max(3, len(head[j]), *(len(g[j]) for g in grid)) for j in range(n)]

    def line(cells):
        return '| ' + ' | '.join(c.rjust(widths[j]) if right[j] else c.ljust(widths[j]) for j, c in enumerate(cells)) + ' |'

    sep = '|' + '|'.join(('-' * (widths[j] + 1) + ':') if right[j] else '-' * (widths[j] + 2) for j in range(n)) + '|'
    return '\\n'.join([line(head), sep] + [line(g) for g in grid])
"""),
    # ---- DB7 errors / test ----------------------------------------------------------------
    T("DB7", "errors", "test",
      "Write `fulfill_order(stock, order)` where stock is a dict of sku to int quantity and order is a list or tuple of (sku, qty) lines. "
      "Checks run in this exact order and the first failure raises: stock not a dict raises TypeError('stock must be a dict'); order not "
      "a list or tuple raises TypeError('order must be a list'); an empty order raises ValueError('order is empty'). Then every line is "
      "format-checked, left to right, before any stock is consulted: a line that is not a tuple or list of exactly 2 items raises "
      "ValueError('line N: malformed'), a sku that is not a non-empty str raises ValueError('line N: bad sku'), and a qty that is not an "
      "int (bool does not count) or is not positive raises ValueError('line N: bad quantity'), with N the 1-based line number and the "
      "checks for one line running in that order. After all lines pass, the first line (in order) whose sku is not in stock raises "
      "KeyError('unknown sku: SKU'). Then quantities of repeated skus are summed, and if any total exceeds its stock, raise one "
      "ValueError('insufficient stock: ' + entries joined with '; ') with one entry per short sku, sorted by sku, each written "
      "'SKU (need X, have Y)' using the summed need. Otherwise return a new dict with the same keys as stock and the ordered amounts "
      "subtracted (skus reaching zero stay with value 0); the stock argument itself is never modified.",
      "fulfill_order",
      [eq("fulfill_order({'a': 5, 'b': 2}, [('a', 2), ('a', 3)])", "{'a': 0, 'b': 2}"),
       blk("s = {'a': 5, 'b': 2}", "r = fulfill_order(s, ((('b', 1),)[0],))", "assert r == {'a': 5, 'b': 1}, r",
           "assert s == {'a': 5, 'b': 2} and r is not s"),
       eq("fulfill_order({'a': 5}, [['a', 5]])", "{'a': 0}"),
       raises("fulfill_order([('a', 1)], [('a', 1)])", "TypeError", "stock must be a dict"),
       raises("fulfill_order({'a': 1}, {'a': 1})", "TypeError", "order must be a list"),
       raises("fulfill_order('x', 'y')", "TypeError", "stock must be a dict"),
       raises("fulfill_order({'a': 1}, [])", "ValueError", "order is empty"),
       raises("fulfill_order({'a': 1}, [('a', 1), ('a',), ('', 1)])", "ValueError", "line 2: malformed"),
       raises("fulfill_order({'a': 1}, [('a', 1, 3)])", "ValueError", "line 1: malformed"),
       raises("fulfill_order({'a': 1}, ['ab'])", "ValueError", "line 1: malformed"),
       raises("fulfill_order({'a': 1}, [('a', 1), ('', 'x')])", "ValueError", "line 2: bad sku"),
       raises("fulfill_order({'a': 1}, [(7, 1)])", "ValueError", "line 1: bad sku"),
       raises("fulfill_order({'a': 1}, [('a', 0), ('zzz', 1)])", "ValueError", "line 1: bad quantity"),
       raises("fulfill_order({'a': 1}, [('a', True)])", "ValueError", "line 1: bad quantity"),
       raises("fulfill_order({'a': 1}, [('a', 1.0)])", "ValueError", "line 1: bad quantity"),
       raises("fulfill_order({'a': 1}, [('zzz', 50), ('yyy', 1), ('a', -1)])", "ValueError", "line 3: bad quantity"),
       raises("fulfill_order({'a': 1}, [('a', 99), ('zzz', 1), ('yyy', 1)])", "KeyError", "unknown sku: zzz"),
       raises("fulfill_order({'a': 1, 'b': 4, 'c': 9}, [('c', 2), ('b', 3), ('a', 1), ('b', 2), ('a', 5)])",
              "ValueError", "insufficient stock: a (need 6, have 1); b (need 5, have 4)")],
      """
def fulfill_order(stock, order):
    if not isinstance(stock, dict):
        raise TypeError('stock must be a dict')
    if not isinstance(order, (list, tuple)):
        raise TypeError('order must be a list')
    if not order:
        raise ValueError('order is empty')
    for i, line in enumerate(order, 1):
        if not isinstance(line, (list, tuple)) or len(line) != 2:
            raise ValueError(f'line {i}: malformed')
        sku, qty = line
        if not isinstance(sku, str) or not sku:
            raise ValueError(f'line {i}: bad sku')
        if type(qty) is not int or qty <= 0:
            raise ValueError(f'line {i}: bad quantity')
    for sku, _ in order:
        if sku not in stock:
            raise KeyError(f'unknown sku: {sku}')
    need = {}
    for sku, qty in order:
        need[sku] = need.get(sku, 0) + qty
    short = [f'{k} (need {need[k]}, have {stock[k]})' for k in sorted(need) if need[k] > stock[k]]
    if short:
        raise ValueError('insufficient stock: ' + '; '.join(short))
    out = dict(stock)
    for k, v in need.items():
        out[k] -= v
    return out
"""),

    # ---- DB8 format / test ----------------------------------------------------------------
    T("DB8", "format", "test",
      "Write `build_changelog(entries)` where entries is a list of dicts with optional keys 'type', 'scope', 'msg' and 'breaking' (a missing "
      "key counts as None or False). Return a Markdown string. Normalize the type by stripping and lowercasing; 'feat', 'fix', 'perf' and "
      "'docs' are known and any other value (or a missing one) is filed under 'other'. Groups appear in the order feat, fix, perf, docs, "
      "other, with headings '### Features', '### Fixes', '### Performance', '### Documentation' and '### Other'; a group with no entries "
      "is omitted. Clean the msg by stripping it, removing every trailing '.' and stripping again, then uppercasing only its first "
      "character; an entry whose msg is None or empty after cleaning is dropped. Strip the scope too. An entry renders as '- **SCOPE:** "
      "TEXT' when it has a non-empty scope and '- TEXT' otherwise, and if breaking is truthy the text is '**BREAKING** ' followed by the "
      "cleaned msg. Inside a group sort entries by scope case-insensitively (casefold) with scope-less entries last, keeping the input "
      "order among equals, and only then drop any later entry whose rendered line is identical to an earlier one. Each group is its "
      "heading line followed directly by its lines; groups are separated by one blank line and there is no trailing newline. If no "
      "entries survive return exactly '_No changes._'.",
      "build_changelog",
      [eq("build_changelog([])", "'_No changes._'"),
       eq("build_changelog([{'type': 'fix', 'msg': ' '}, {'msg': None}, {'msg': '...'}])", "'_No changes._'"),
       eq("build_changelog([{'type': 'feat', 'msg': 'add login'}])", "'### Features\\n- Add login'"),
       eq("build_changelog([{'type': 'docs', 'msg': 'x'}, {'type': 'fix', 'msg': 'y'}, {'type': 'feat', 'msg': 'z'}, {'type': 'perf', 'msg': 'w'}, {'msg': 'v'}])",
          "'### Features\\n- Z\\n\\n### Fixes\\n- Y\\n\\n### Performance\\n- W\\n\\n### Documentation\\n- X\\n\\n### Other\\n- V'"),
       eq("build_changelog([{'type': ' FEAT ', 'msg': 'a'}, {'type': 'chore', 'msg': 'b'}, {'type': 'Fix', 'msg': 'c'}])",
          "'### Features\\n- A\\n\\n### Fixes\\n- C\\n\\n### Other\\n- B'"),
       eq("build_changelog([{'type': 'fix', 'msg': '  handle eOF crash...  '}])", "'### Fixes\\n- Handle eOF crash'"),
       eq("build_changelog([{'type': 'fix', 'scope': ' api ', 'msg': 'a.b.'}])", "'### Fixes\\n- **api:** A.b'"),
       eq("build_changelog([{'type': 'feat', 'scope': '', 'msg': 'n'}, {'type': 'feat', 'scope': '  ', 'msg': 'm'}])",
          "'### Features\\n- N\\n- M'"),
       eq("build_changelog([{'type': 'feat', 'msg': 'nos'}, {'type': 'feat', 'scope': 'ui', 'msg': 'b'}, {'type': 'feat', 'scope': 'API', 'msg': 'c'}, {'type': 'feat', 'scope': 'api', 'msg': 'd'}, {'type': 'feat', 'scope': 'Zed', 'msg': 'e'}])",
          "'### Features\\n- **API:** C\\n- **api:** D\\n- **ui:** B\\n- **Zed:** E\\n- Nos'"),
       eq("build_changelog([{'type': 'feat', 'scope': 'db', 'msg': 'drop table', 'breaking': True}, {'type': 'feat', 'msg': 'rename', 'breaking': 1}])",
          "'### Features\\n- **db:** **BREAKING** Drop table\\n- **BREAKING** Rename'"),
       eq("build_changelog([{'type': 'fix', 'msg': 'same.'}, {'type': 'fix', 'msg': 'same'}, {'type': 'fix', 'scope': 'a', 'msg': 'same'}, {'type': 'fix', 'msg': 'same', 'breaking': True}])",
          "'### Fixes\\n- **a:** Same\\n- Same\\n- **BREAKING** Same'"),
       eq("build_changelog([{'type': 'fix', 'scope': 'b', 'msg': 'one'}, {'type': 'fix', 'scope': 'B', 'msg': 'one'}, {'type': 'fix', 'scope': 'b', 'msg': 'one'}])",
          "'### Fixes\\n- **b:** One\\n- **B:** One'")],
      """
def build_changelog(entries):
    titles = [('feat', 'Features'), ('fix', 'Fixes'), ('perf', 'Performance'), ('docs', 'Documentation'), ('other', 'Other')]
    known = {k for k, _ in titles}
    groups = {k: [] for k in known}
    for e in entries:
        t = (e.get('type') or '').strip().lower()
        t = t if t in known and t != 'other' else 'other'
        msg = (e.get('msg') or '').strip().rstrip('.').strip()
        if not msg:
            continue
        msg = msg[0].upper() + msg[1:]
        scope = (e.get('scope') or '').strip()
        if e.get('breaking'):
            msg = '**BREAKING** ' + msg
        groups[t].append((scope, msg))
    blocks = []
    for key, title in titles:
        items = sorted(groups[key], key=lambda x: (x[0] == '', x[0].casefold()))
        seen = set()
        lines = []
        for scope, msg in items:
            line = f'- **{scope}:** {msg}' if scope else f'- {msg}'
            if line not in seen:
                seen.add(line)
                lines.append(line)
        if lines:
            blocks.append('\\n'.join([f'### {title}'] + lines))
    return '\\n\\n'.join(blocks) if blocks else '_No changes._'
"""),
]
