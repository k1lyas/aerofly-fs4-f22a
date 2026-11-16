"""Reader/writer for the Aerofly text configuration format (.tmd / .tmc).

    <[type][name][value]
        <[type][name][value]>     leaf
    >                             node with children

Values may contain nested brackets ([...]) and span several lines. Comments start with // .
"""
import re


class Node:
    __slots__ = ('type', 'name', 'value', 'children', 'leaf')

    def __init__(self, type_, name, value='', children=None, leaf=True):
        self.type, self.name, self.value = type_, name, value
        self.children = children if children is not None else []
        self.leaf = leaf

    # -- convenience -------------------------------------------------------
    def get(self, name, default=None):
        for c in self.children:
            if c.name == name:
                return c.value
        return default

    def set(self, name, value, type_='string8'):
        for c in self.children:
            if c.name == name:
                c.value = value
                return c
        c = Node(type_, name, value)
        self.children.append(c)
        return c

    def find(self, name):
        for c in self.children:
            if c.name == name:
                return c
        return None

    def walk(self):
        yield self
        for c in self.children:
            yield from c.walk()

    def clone(self):
        return Node(self.type, self.name, self.value, [c.clone() for c in self.children], self.leaf)

    def __repr__(self):
        return '<%s %s>' % (self.type, self.name)


def _strip_comments(text):
    out = []
    for line in text.splitlines():
        i = line.find('//')
        out.append(line if i < 0 else line[:i])
    return '\n'.join(out)


def _read_bracket(s, i):
    """s[i] == '['; return (content, index after the matching ']')."""
    depth, j = 0, i
    while j < len(s):
        ch = s[j]
        if ch == '[':
            depth += 1
        elif ch == ']':
            depth -= 1
            if depth == 0:
                return s[i + 1:j], j + 1
        j += 1
    raise ValueError('unbalanced [ at %d' % i)


def parse(text):
    s = _strip_comments(text.lstrip('﻿'))
    root = Node('root', '', leaf=False)
    stack = [root]
    i, n = 0, len(s)
    ws = re.compile(r'\s*')
    while i < n:
        i = ws.match(s, i).end()
        if i >= n:
            break
        ch = s[i]
        if ch == '<':
            i = ws.match(s, i + 1).end()
            t, i = _read_bracket(s, i)
            i = ws.match(s, i).end()
            nm, i = _read_bracket(s, i)
            i = ws.match(s, i).end()
            val = ''
            if i < n and s[i] == '[':
                val, i = _read_bracket(s, i)
            i = ws.match(s, i).end()
            node = Node(t.strip(), nm.strip(), val)
            stack[-1].children.append(node)
            if i < n and s[i] == '>':
                i += 1
            else:
                node.leaf = False
                stack.append(node)
        elif ch == '>':
            stack.pop()
            i += 1
        else:
            raise ValueError('unexpected %r at %d: %r' % (ch, i, s[i:i + 60]))
    return root


def dump(node, indent=0):
    lines = []
    pad = '    ' * indent
    for c in node.children:
        head = '%s<[%s][%s][%s]' % (pad, c.type, c.name, c.value)
        if c.leaf:
            lines.append(head + '>')
        else:
            lines.append(head)
            lines.append(dump(c, indent + 1))
            lines.append(pad + '>')
    return '\n'.join(l for l in lines if l != '')


def load(path):
    with open(path, encoding='utf-8', errors='replace') as fh:
        return parse(fh.read())


def save(root, path):
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:    # the same bytes on Windows (no CRLF)
        fh.write(dump(root) + '\n')
