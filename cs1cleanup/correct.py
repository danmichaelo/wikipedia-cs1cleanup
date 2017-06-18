# encoding=utf8
# Based on <http://norvig.com/spell-correct.html>
from __future__ import unicode_literals

wordlist = ['januar', 'februar', 'mars', 'april', 'mai', 'juni', 'juli', 'august', 'september', 'oktober', 'november', 'desember', 'våren', 'sommeren', 'høsten', 'vinteren']

alphabet = 'abcdefghijklmnopqrstuvwxyzæøå'


def edits1(word):
    splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
    deletes = [a + b[1:] for a, b in splits if b]
    transposes = [a + b[1] + b[0] + b[2:] for a, b in splits if len(b) > 1]
    replaces = [a + c + b[1:] for a, b in splits for c in alphabet if b]
    inserts = [a + c + b for a, b in splits for c in alphabet]
    return set(deletes + transposes + replaces + inserts)


def known_edits2(word):
    return set(e2 for e1 in edits1(word) for e2 in edits1(e1) if e2 in wordlist)


def known(words):
    return set(w for w in words if w in wordlist)


def correct(word):
    if len(word) <= 5:
        candidates = known([word]) or known(edits1(word)) or [word]
    else:
        candidates = known([word]) or known(edits1(word)) or known_edits2(word) or [word]
    return candidates.pop()
