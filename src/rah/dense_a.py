# agent: claude-code  2026-10-17
"""8 dense invented tasks (families edge, mutation). Each spec packs 8-10 requirements, each stated once.

Written because strong models score 85-100% on suite_data / suite_hard. Every requirement is fully specified
and covered by at least one hidden test, so a careful reader can pass all of them; most models miss one.
Splits: DA1-3 train, DA4-5 val, DA6-8 test. Nothing here is copied from a public benchmark.
"""
from __future__ import annotations

from .suite import Task
from .suite_data import T, blk, eq, raises

DENSE_A: list[Task] = [
    T("DA1", "edge", "train",
      "Write `dedupe_tags(tags, limit=None)` which cleans a list of tag strings. "
      "If tags is None return []. "
      "Items that are not str are skipped silently. "
      "Every kept tag has its leading and trailing whitespace removed and each internal run of whitespace "
      "(spaces, tabs, newlines) collapsed to one single space. "
      "Tags that are empty after that cleaning are dropped. "
      "Two tags count as duplicates when their cleaned forms are equal ignoring case (compare lowercased), "
      "and the first occurrence wins, keeping its own original capitalisation (in cleaned form). "
      "The order of first occurrences is preserved. "
      "If limit is not None, only the first `limit` tags of the deduplicated result are returned, "
      "applied after deduplication, and a limit of zero or less gives []. "
      "The result is always a new list and the input list is never modified.",
      "dedupe_tags",
      [eq("dedupe_tags(['a','b'])", "['a','b']"),
       eq("dedupe_tags(None)", "[]"),
       eq("dedupe_tags([])", "[]"),
       eq("dedupe_tags([' a ', '', '   ', 'b'])", "['a','b']"),
       eq("dedupe_tags(['Foo','foo','FOO','bar'])", "['Foo','bar']"),
       eq("dedupe_tags(['a   b','A b','a\\tb'])", "['a b']"),
       eq("dedupe_tags(['x',5,None,'y',b'z'])", "['x','y']"),
       eq("dedupe_tags(['a','b','c'], 2)", "['a','b']"),
       eq("dedupe_tags(['a','a','b'], 2)", "['a','b']"),
       eq("dedupe_tags(['a','b'], 0)", "[]"),
       eq("dedupe_tags(['a','b'], -3)", "[]"),
       eq("dedupe_tags(['a','b'], 10)", "['a','b']"),
       blk("xs = [' A ', 'a']", "orig = list(xs)", "r = dedupe_tags(xs)",
           "assert xs == orig and r == ['A'] and r is not xs")],
      """
def dedupe_tags(tags, limit=None):
    if tags is None:
        return []
    seen = set()
    out = []
    for t in tags:
        if not isinstance(t, str):
            continue
        c = " ".join(t.split())
        if not c or c.lower() in seen:
            continue
        seen.add(c.lower())
        out.append(c)
    if limit is not None:
        if limit <= 0:
            return []
        out = out[:limit]
    return out
"""),

    T("DA2", "edge", "train",
      "Write `bucket_readings(readings, width, start=0)` which counts sensor readings in equal-width buckets. "
      "If width is not greater than zero raise ValueError with the message 'width must be positive', "
      "and do this check first, even when readings is empty or None. "
      "Bucket i covers the half-open range from start + i*width up to but not including start + (i+1)*width. "
      "Only real finite numbers are counted: ints and floats count, while None, strings, bools, NaN and "
      "infinities are ignored. "
      "Readings below start are ignored. "
      "Return a list of (lo, hi, count) tuples where lo = start + i*width and hi = start + (i+1)*width, "
      "beginning with bucket 0 and ending with the bucket that holds the largest counted reading. "
      "Buckets in between that received nothing are still included with count 0. "
      "If readings is None, empty, or nothing is counted, return [].",
      "bucket_readings",
      [eq("bucket_readings([1,2,5,11], 5)", "[(0,5,2),(5,10,1),(10,15,1)]"),
       eq("bucket_readings([5], 5)", "[(0,5,0),(5,10,1)]"),
       eq("bucket_readings([0,20], 10)", "[(0,10,1),(10,20,0),(20,30,1)]"),
       eq("bucket_readings([-1,3], 5)", "[(0,5,1)]"),
       eq("bucket_readings([3,12,25], 5, 10)", "[(10,15,1),(15,20,0),(20,25,0),(25,30,1)]"),
       eq("bucket_readings([-5], 5)", "[]"),
       eq("bucket_readings([], 5)", "[]"),
       eq("bucket_readings(None, 5)", "[]"),
       eq("bucket_readings([None, float('nan'), True, float('inf'), 'a', 3], 5)", "[(0,5,1)]"),
       eq("bucket_readings([-3,-1,2], 2, -4)", "[(-4,-2,1),(-2,0,1),(0,2,0),(2,4,1)]"),
       eq("bucket_readings([4.999, 5.0], 5)", "[(0,5,1),(5,10,1)]"),
       eq("bucket_readings([0.5, 1.2], 1.0)", "[(0,1.0,1),(1.0,2.0,1)]"),
       raises("bucket_readings([1], 0)", "ValueError", "width must be positive"),
       raises("bucket_readings([], -1)", "ValueError", "width must be positive"),
],
      """
import math


def bucket_readings(readings, width, start=0):
    if not width > 0:
        raise ValueError("width must be positive")
    counts = {}
    for v in readings or []:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            continue
        if v < start:
            continue
        i = int((v - start) // width)
        counts[i] = counts.get(i, 0) + 1
    if not counts:
        return []
    return [(start + i * width, start + (i + 1) * width, counts.get(i, 0)) for i in range(max(counts) + 1)]
"""),

    T("DA3", "mutation", "train",
      "Write `apply_patch(doc, patch)` which applies a patch dict to a settings dict and returns the result. "
      "doc must be a dict or None (None is treated as {}); any other type raises TypeError with the message "
      "'doc must be a dict'. "
      "patch must be a dict or None (None means no changes); any other type raises TypeError with the message "
      "'patch must be a dict'. "
      "The result is a brand-new dict and neither doc nor patch may be modified, at any depth. "
      "The result must also share no nested dict or list objects with doc or with patch, "
      "so mutating the result later never changes either input. "
      "A patch value of None deletes that key from the result, and deleting a key that is absent is not an error. "
      "When the patch value is a dict and the doc value for that key is also a dict, merge them recursively "
      "using these same rules. "
      "When the patch value is a dict but the doc has no such key or a non-dict value, the result gets a copy "
      "of that patch dict in which every key whose value is None is dropped at every dict depth (an empty "
      "dict stays as {}). "
      "Any other patch value, including a list, replaces the doc value wholesale (a list is copied, not merged). "
      "Keys in doc that the patch does not mention are kept unchanged.",
      "apply_patch",
      [eq("apply_patch({'a':1,'b':2},{'a':5,'c':3})", "{'a':5,'b':2,'c':3}"),
       eq("apply_patch({'a':1,'b':2},{'a':None,'zz':None})", "{'b':2}"),
       eq("apply_patch({'a':{'b':1,'c':2}},{'a':{'b':None,'d':3}})", "{'a':{'c':2,'d':3}}"),
       eq("apply_patch({'a':1},{'a':{'x':1,'y':None,'z':{'q':None,'r':2}}})", "{'a':{'x':1,'z':{'r':2}}}"),
       eq("apply_patch({'a':{'x':1}},{'a':5})", "{'a':5}"),
       eq("apply_patch({},{'a':{}})", "{'a':{}}"),
       eq("apply_patch({'a':[1,2]},{'a':[3]})", "{'a':[3]}"),
       blk("doc = {'a':{'b':[1]}, 'k':1}", "patch = {'a':{'b':[2], 'n':None}, 'k':None}",
           "r = apply_patch(doc, patch)",
           "assert r == {'a':{'b':[2]}}",
           "assert doc == {'a':{'b':[1]}, 'k':1}",
           "assert patch == {'a':{'b':[2], 'n':None}, 'k':None}"),
       blk("patch = {'a':{'b':[1]}}", "r = apply_patch({}, patch)",
           "assert r['a'] is not patch['a'] and r['a']['b'] is not patch['a']['b']",
           "r['a']['b'].append(2)", "assert patch == {'a':{'b':[1]}}"),
       blk("doc = {'a':{'b':1}}", "r = apply_patch(doc, {'c':1})",
           "assert r['a'] is not doc['a']", "r['a']['b'] = 9", "assert doc == {'a':{'b':1}}"),
       blk("doc = {'a':1}", "r = apply_patch(doc, None)", "assert r == {'a':1} and r is not doc"),
       eq("apply_patch(None, {'a':1})", "{'a':1}"),
       raises("apply_patch([1], {})", "TypeError", "doc must be a dict"),
       raises("apply_patch({}, [('a', 1)])", "TypeError", "patch must be a dict")],
      """
import copy


def _clean(v):
    if isinstance(v, dict):
        return {k: _clean(x) for k, x in v.items() if x is not None}
    return copy.deepcopy(v)


def apply_patch(doc, patch):
    if doc is None:
        doc = {}
    if not isinstance(doc, dict):
        raise TypeError("doc must be a dict")
    if patch is None:
        patch = {}
    if not isinstance(patch, dict):
        raise TypeError("patch must be a dict")
    out = copy.deepcopy(doc)
    for k, v in patch.items():
        if v is None:
            out.pop(k, None)
        elif isinstance(v, dict):
            if isinstance(out.get(k), dict):
                out[k] = apply_patch(out[k], v)
            else:
                out[k] = _clean(v)
        else:
            out[k] = copy.deepcopy(v)
    return out
"""),

    T("DA4", "edge", "val",
      "Write `next_slot(booked, duration, day_start, day_end)` which finds the earliest free meeting slot. "
      "All times are integer minutes. "
      "If duration is not greater than zero raise ValueError with the message 'duration must be positive', "
      "and do this check before anything else. "
      "booked is a list of (start, end) tuples that may be unsorted and may overlap each other; "
      "None means no bookings. "
      "A booking whose start is not less than its end is invalid and is ignored (it is not swapped). "
      "Bookings may lie partly or wholly outside the day; they only matter where they overlap the free time. "
      "Return the smallest start t with t >= day_start such that the slot from t up to t + duration lies "
      "entirely within the day (t + duration <= day_end) and does not overlap any valid booking. "
      "A slot that only touches a booking, ending exactly where one starts or starting exactly where one ends, "
      "does not overlap it. "
      "If no such slot exists, including when day_end is not after day_start, return None. "
      "The booked list must not be modified.",
      "next_slot",
      [eq("next_slot([], 30, 540, 1020)", "540"),
       eq("next_slot([(540,570),(600,660)], 30, 540, 1020)", "570"),
       eq("next_slot([(540,580),(600,660)], 30, 540, 1020)", "660"),
       eq("next_slot([(600,700),(540,620)], 30, 540, 1020)", "700"),
       eq("next_slot([(540,990)], 30, 540, 1020)", "990"),
       eq("next_slot([(540,991)], 30, 540, 1020)", "None"),
       eq("next_slot([(0,500)], 30, 540, 1020)", "540"),
       eq("next_slot([(500,560)], 30, 540, 1020)", "560"),
       eq("next_slot([(600,600),(700,650)], 30, 540, 1020)", "540"),
       eq("next_slot([], 480, 540, 1020)", "540"),
       eq("next_slot([], 480, 540, 1000)", "None"),
       eq("next_slot([], 30, 600, 600)", "None"),
       raises("next_slot([], 0, 540, 1020)", "ValueError", "duration must be positive"),
       blk("b = [(700,720),(540,560)]", "orig = list(b)", "next_slot(b, 30, 540, 1020)", "assert b == orig")],
      """
def next_slot(booked, duration, day_start, day_end):
    if duration <= 0:
        raise ValueError("duration must be positive")
    items = sorted((s, e) for s, e in (booked or []) if s < e)
    t = day_start
    for s, e in items:
        if s - t >= duration:
            break
        t = max(t, e)
    if t + duration <= day_end:
        return t
    return None
"""),

    T("DA5", "mutation", "val",
      "Write `pop_expired(cache, now, max_keep=None)` which cleans a cache dict in place. "
      "cache maps keys (strings) to (value, expires_at) tuples where expires_at is a number or None. "
      "If cache is None return []. "
      "If max_keep is not None and is negative, raise ValueError with the message 'max_keep must be >= 0' "
      "before changing anything. "
      "An entry is expired when its expires_at is not None and is less than or equal to now "
      "(exactly equal counts as expired); entries with expires_at None never expire. "
      "Delete all expired entries from the very same dict object that was passed in (do not build a new dict "
      "or rebind anything), and leave the surviving (value, expires_at) tuples as the same objects. "
      "Then, if max_keep is not None and more than max_keep entries remain, also delete entries until exactly "
      "max_keep remain, evicting first the entries with the earliest expires_at, treating None as later than "
      "any number, and breaking ties by key in ascending order. "
      "Return a list of every removed key: the expired keys in ascending key order, followed by the evicted "
      "keys in the order they were evicted. "
      "If nothing is removed, return [] and leave the cache untouched.",
      "pop_expired",
      [blk("cache = {'a':(1,10),'b':(2,20)}", "r = pop_expired(cache, 15)", "assert r == ['a']",
           "assert cache == {'b':(2,20)}"),
       blk("cache = {'a':(1,10)}", "assert pop_expired(cache, 10) == ['a']", "assert cache == {}"),
       blk("cache = {'a':(1,None),'b':(2,5)}", "assert pop_expired(cache, 1000) == ['b']",
           "assert cache == {'a':(1,None)}"),
       blk("cache = {'z':(1,1),'b':(1,2),'m':(1,3)}", "assert pop_expired(cache, 5) == ['b','m','z']",
           "assert cache == {}"),
       blk("t = (2,20)", "cache = {'a':(1,1),'b':t}", "pop_expired(cache, 5)", "assert cache['b'] is t"),
       blk("cache = {'a':(1,10)}", "assert pop_expired(cache, 5) == []", "assert cache == {'a':(1,10)}"),
       eq("pop_expired(None, 5)", "[]"),
       blk("cache = {'a':(1,50),'b':(2,30),'c':(3,40)}", "assert pop_expired(cache, 0, 2) == ['b']",
           "assert sorted(cache) == ['a','c']"),
       blk("cache = {'x':(1,5),'y':(1,5),'z':(1,9)}", "assert pop_expired(cache, 0, 1) == ['x','y']",
           "assert cache == {'z':(1,9)}"),
       blk("cache = {'p':(1,None),'q':(1,100)}", "assert pop_expired(cache, 0, 1) == ['q']",
           "assert cache == {'p':(1,None)}"),
       blk("cache = {'z':(1,5),'a':(1,50),'m':(1,60)}", "assert pop_expired(cache, 10, 1) == ['z','a']",
           "assert cache == {'m':(1,60)}"),
       blk("cache = {'a':(1,5),'b':(1,50),'c':(1,None)}", "assert pop_expired(cache, 10, 0) == ['a','b','c']",
           "assert cache == {}"),
       blk("cache = {'a':(1,5),'b':(1,50)}", "assert pop_expired(cache, 10, 5) == ['a']",
           "assert cache == {'b':(1,50)}"),
       blk("cache = {'a':(1,5),'b':(1,50)}",
           raises("pop_expired(cache, 10, -1)", "ValueError", "max_keep must be >= 0"),
           "assert cache == {'a':(1,5),'b':(1,50)}")],
      """
def pop_expired(cache, now, max_keep=None):
    if cache is None:
        return []
    if max_keep is not None and max_keep < 0:
        raise ValueError("max_keep must be >= 0")
    expired = sorted(k for k, (v, e) in cache.items() if e is not None and e <= now)
    for k in expired:
        del cache[k]
    evicted = []
    if max_keep is not None and len(cache) > max_keep:
        order = sorted(cache, key=lambda k: (cache[k][1] is None, cache[k][1] or 0, k))
        evicted = order[:len(cache) - max_keep]
        for k in evicted:
            del cache[k]
    return expired + evicted
"""),

    T("DA6", "edge", "test",
      "Write `chunk_by_budget(words, budget)` which greedily packs words into text lines. "
      "If budget is less than 1 raise ValueError with the message 'budget must be at least 1', "
      "and do this check first, even when words is empty or None. "
      "words may be a list or a tuple, or None (which gives []). "
      "Items that are not str are skipped silently. "
      "Each word has leading and trailing whitespace removed (anything inside it is left exactly as is), "
      "and words that are empty after that are skipped. "
      "Words are placed in order; a word joins the current line, separated by exactly one space, "
      "only if the resulting line length is at most budget, otherwise it starts a new line. "
      "A word longer than budget is first handled by finishing the current line, if any is open, "
      "then it is cut into consecutive pieces of budget characters, the last piece possibly shorter, "
      "and every piece becomes its own line. "
      "The next word after such a long word always starts a fresh line and never joins its last piece. "
      "Return the list of lines with no empty strings, and [] when there are no lines.",
      "chunk_by_budget",
      [eq("chunk_by_budget(['aa','bb','cc'], 5)", "['aa bb','cc']"),
       eq("chunk_by_budget(['aa','bbb'], 6)", "['aa bbb']"),
       eq("chunk_by_budget(['aa','bbb'], 4)", "['aa','bbb']"),
       eq("chunk_by_budget(['abcdefg'], 3)", "['abc','def','g']"),
       eq("chunk_by_budget(['hi','abcdefg','yo'], 3)", "['hi','abc','def','g','yo']"),
       eq("chunk_by_budget(['abcdefg','x'], 5)", "['abcde','fg','x']"),
       eq("chunk_by_budget(['abc','d'], 3)", "['abc','d']"),
       eq("chunk_by_budget([' a ', '', '  ', 'b'], 5)", "['a b']"),
       eq("chunk_by_budget(['a', None, 3, 'b'], 5)", "['a b']"),
       eq("chunk_by_budget(None, 5)", "[]"),
       eq("chunk_by_budget(('a','b'), 3)", "['a b']"),
       eq("chunk_by_budget(['a  b'], 10)", "['a  b']"),
       raises("chunk_by_budget(['a'], 0)", "ValueError", "budget must be at least 1")],
      """
def chunk_by_budget(words, budget):
    if budget < 1:
        raise ValueError("budget must be at least 1")
    lines = []
    cur = ""
    for w in words or []:
        if not isinstance(w, str):
            continue
        w = w.strip()
        if not w:
            continue
        if len(w) > budget:
            if cur:
                lines.append(cur)
                cur = ""
            lines.extend(w[i:i + budget] for i in range(0, len(w), budget))
            continue
        if not cur:
            cur = w
        elif len(cur) + 1 + len(w) <= budget:
            cur += " " + w
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines
"""),

    T("DA7", "mutation", "test",
      "Write `squeeze_runs(items, max_run)` which shortens runs of repeated elements inside a list, in place. "
      "If items is not a list raise TypeError with the message 'items must be a list'; this check comes first. "
      "If max_run is less than 1 raise ValueError with the message 'max_run must be at least 1', "
      "before the list is changed in any way. "
      "A run is a stretch of consecutive elements that are equal to each other under ==; "
      "elements may be unhashable, such as lists. "
      "Modify the very same list object that was passed in (do not rebind or return a new list), "
      "so that no run is longer than max_run, keeping the first max_run elements of each run "
      "and dropping the rest, so the kept elements are the original objects and the order is unchanged. "
      "Equal elements that are separated by a different element belong to different runs and are not merged. "
      "Return the number of elements removed as an int, which is 0 for an empty list "
      "or when nothing needed removing, and in that case the list is left as it was.",
      "squeeze_runs",
      [blk("xs = [1,1,1,2,2,1]", "n = squeeze_runs(xs, 2)", "assert n == 1 and xs == [1,1,2,2,1]"),
       blk("xs = [1,1,2,2,2,3]", "assert squeeze_runs(xs, 1) == 3", "assert xs == [1,2,3]"),
       blk("xs = [1,2,3]", "n = squeeze_runs(xs, 2)", "assert n == 0 and type(n) is int and xs == [1,2,3]"),
       blk("xs = []", "assert squeeze_runs(xs, 3) == 0 and xs == []"),
       blk("xs = [1,1,1,1]", "ys = xs", "squeeze_runs(xs, 2)", "assert ys is xs and ys == [1,1]"),
       blk("xs = ['a','b','a','a']", "assert squeeze_runs(xs, 1) == 1", "assert xs == ['a','b','a']"),
       blk("xs = [[1],[1],[1],[2]]", "assert squeeze_runs(xs, 2) == 1", "assert xs == [[1],[1],[2]]"),
       blk("a = [1]", "b = [1]", "c = [1]", "xs = [a,b,c]", "squeeze_runs(xs, 2)",
           "assert len(xs) == 2 and xs[0] is a and xs[1] is b"),
       blk("xs = [0]*100", "assert squeeze_runs(xs, 3) == 97", "assert xs == [0,0,0]"),
       blk("xs = [1, 1.0, True, 2]", "assert squeeze_runs(xs, 1) == 2", "assert xs == [1, 2]"),
       blk("xs = [1,1,1]",
           raises("squeeze_runs(xs, 0)", "ValueError", "max_run must be at least 1"),
           "assert xs == [1,1,1]"),
       raises("squeeze_runs((1,1,1), 2)", "TypeError", "items must be a list"),
       raises("squeeze_runs(None, 2)", "TypeError", "items must be a list"),
       raises("squeeze_runs((1,1), 0)", "TypeError", "items must be a list")],
      """
def squeeze_runs(items, max_run):
    if not isinstance(items, list):
        raise TypeError("items must be a list")
    if max_run < 1:
        raise ValueError("max_run must be at least 1")
    out = []
    run = 0
    prev = None
    for i, x in enumerate(items):
        if i > 0 and x == prev:
            run += 1
        else:
            run = 1
        prev = x
        if run <= max_run:
            out.append(x)
    removed = len(items) - len(out)
    if removed:
        items[:] = out
    return removed
"""),

    T("DA8", "mutation", "test",
      "Write `merge_inventory(base, delta)` which applies stock changes to an inventory dict in place. "
      "base maps item names (strings) to int quantities and delta maps item names to int changes (may be negative). "
      "If delta is None return []. "
      "Every value in delta must be a real int; a float or a bool anywhere in delta raises TypeError with the "
      "message 'quantities must be int', and this check happens before any other check or change. "
      "Item names missing from base count as quantity 0. "
      "Examine the delta names in ascending order; if any resulting quantity would be below zero, raise "
      "ValueError with the message 'insufficient stock: NAME' for the first such name in that order, "
      "and in that case base must be left completely unchanged (all or nothing). "
      "Otherwise update the very same base dict that was passed in, and never modify delta. "
      "Names in delta whose resulting quantity is exactly 0 are removed from base (or simply not added). "
      "Names in base that delta does not mention are left alone, even if their quantity is 0. "
      "A name with a positive result is set in base, adding it if it was missing. "
      "Return a new list, in ascending order, of the names that were present in base before the call and "
      "were removed because they reached 0; names that were never in base are not listed.",
      "merge_inventory",
      [blk("base = {'a':2}", "r = merge_inventory(base, {'a':3,'b':1})", "assert r == [] and base == {'a':5,'b':1}"),
       blk("base = {'a':2,'b':1}", "r = merge_inventory(base, {'a':-2})", "assert r == ['a'] and base == {'b':1}"),
       blk("base = {'z':1,'c':1,'m':1}", "r = merge_inventory(base, {'z':-1,'c':-1})",
           "assert r == ['c','z'] and base == {'m':1}"),
       blk("base = {'a':1,'b':5}",
           raises("merge_inventory(base, {'b':-1,'a':-2})", "ValueError", "insufficient stock: a"),
           "assert base == {'a':1,'b':5}"),
       blk("base = {}",
           raises("merge_inventory(base, {'q':-1,'b':-1})", "ValueError", "insufficient stock: b"),
           "assert base == {}"),
       blk("base = {'a':1}", "d = {'a':2,'b':3}", "merge_inventory(base, d)", "assert d == {'a':2,'b':3}"),
       blk("base = {'a':1}", "assert merge_inventory(base, None) == [] and base == {'a':1}"),
       blk("base = {}", "assert merge_inventory(base, {'a':0}) == [] and base == {}"),
       blk("base = {'a':4}", "assert merge_inventory(base, {'a':0}) == [] and base == {'a':4}"),
       blk("base = {'a':0}", "assert merge_inventory(base, {'a':0}) == ['a'] and base == {}"),
       blk("base = {'a':0,'b':1}", "assert merge_inventory(base, {'b':1}) == [] and base == {'a':0,'b':2}"),
       blk("base = {'a':1}",
           raises("merge_inventory(base, {'a':1.5})", "TypeError", "quantities must be int"),
           "assert base == {'a':1}"),
       blk("base = {'a':0}",
           raises("merge_inventory(base, {'a':-1,'b':1.0})", "TypeError", "quantities must be int"),
           "assert base == {'a':0}"),
       blk("base = {'a':1}",
           raises("merge_inventory(base, {'a':-1,'b':-1})", "ValueError", "insufficient stock: b"),
           "assert base == {'a':1}")],
      """
def merge_inventory(base, delta):
    if delta is None:
        return []
    for v in delta.values():
        if type(v) is not int:
            raise TypeError("quantities must be int")
    new = {}
    for k in sorted(delta):
        r = base.get(k, 0) + delta[k]
        if r < 0:
            raise ValueError(f"insufficient stock: {k}")
        new[k] = r
    removed = []
    for k, r in new.items():
        if r == 0:
            if k in base:
                removed.append(k)
                del base[k]
        else:
            base[k] = r
    return removed
"""),
]
