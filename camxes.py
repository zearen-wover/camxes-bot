# coding=UTF-8

from itertools import *
from subprocess import Popen, PIPE
import unicodedata

class ParsingError(ValueError):
    pass

class ParseUtil():
    def __init__(self, resp):
        self.resp = resp
        self.pos = 0

    def at(self):
        return self.resp[self.pos]
    
    def inc(self, delta=1):
        self.pos += delta

    def eof(self):
        return self.pos >= len(self.resp)

    def skip_whitespace(self):
        while not self.eof() and self.at().isspace():
            self.inc()

    def assert_at(self, ch):
        if self.eof():
            raise ParsingError('Expecting \'{0}\', got EOF at {1}'
                    .format(ch, self.pos))
        if self.at() != ch:
            raise ParsingError('Expecting \'{0}\', got \'{1}\' at {2}'
                    .format(ch, self.at(), self.pos))

class BuildTree(ParseUtil):
    def build(self):
        node = []
        self.skip_whitespace()
        while not self.eof() and not self.at() == ')':
            #Collect identifier
            id_start = self.pos
            while not self.eof() and self.at() != '=' and not self.at().isspace():
                self.inc()
            ident = self.resp[id_start:self.pos]
            if self.at() == '=':
                self.inc()
                self.assert_at('(')
                self.inc()
                inner = self.build()
                if ident == 'nonLojbanWord':
                    # Remove trailing commas
                    while type(inner) == list:
                        inner = inner[0]
                    pos = 0
                    while pos < len(inner) and inner[-(pos+1)] == ',':
                        pos += 1
                    if pos > 0:
                        inner = inner[:-pos]
                node.append(inner)
                self.assert_at(')')
                self.inc()
            else:
                node.append(ident)
            self.skip_whitespace()
        return node

def char_range(start, stop, step=1):
    return map(chr, range(ord(start), ord(stop)+1, step))
stressed = set(filter(lambda c: c != 'a', \
    unicodedata.normalize('NFD','áà')))
stripped = set(filter(lambda c: c != 'a', \
    unicodedata.normalize('NFD','äǎăâāȧạ')))
def accent_set(ch, accents):
    return filter(lambda c: c !=ch, unicodedata.normalize('NFC', 
        ''.join(map(lambda c: ch + c, accents))))
# Change accented chars -> cap chars and remove special symbols
valid_chars = \
    set(char_range('a', 'z')) |\
    set(char_range('A', 'z')) |\
    set(char_range('0', '9')) |\
    set("'`., \t")
replacement_table={}
for v_i in 'aeiouy':
    for v_j in accent_set(v_i, stressed):
        replacement_table[v_j] = v_i.upper()
    for v_j in accent_set(v_i, stripped):
        replacement_table[v_j] = v_i
    for v_j in accent_set(v_i.upper(), stressed | stripped):
        replacement_table[v_j] = v_i.upper()

def preprocess(text):
    text = ''.join(map(lambda c: replacement_table.get(c, c), text))
    text = ''.join(map(lambda c: c if c in valid_chars else ' ', text))
    return text


def trim_tree(tree):
    while type(tree) == list and len(tree) == 1:
        tree = tree[0]
    if type(tree) == list:
        return list(map(trim_tree, tree))
    else:
        return tree

parens = [['(',')'],['[',']'],['{','}'],['<','>']]

# paren order () [] {} <>
def get_paren(depth, oc):
    paren = parens[depth%4][oc]
    if depth >= 4:
        paren += str(depth // 4)
    return paren

def parenthize(tree, depth=0):
    ret = get_paren(depth, 0)
    if type(tree) == list:
        ret += ''.join(map(lambda t: parenthize(t,depth+1),tree))
    else:
        ret += ' ' + tree + ' '
    ret += get_paren(depth, 1)
    return ret

def call_jar(sentence):
    p = Popen(['java','-jar','camxes.jar','-f'], stdin=PIPE, stdout=PIPE)
    p.stdout.readline()
    p.stdin.write(bytes(sentence + '\n', 'UTF-8'))
    resp = p.stdout.readline()
    p.stdin.close()
    return str(resp, 'UTF-8')

def remove_track(text):
    ret = ''
    pos_t = 0
    pos_r = 0
    track = {}
    while pos_t < len(text):
        if text[pos_t] == ',':
            start = pos_t
            pos_t += 1
            while pos_t < len(text) and text[pos_t] == ',':
                pos_t += 1
            if pos_t >= len(text) or text[pos_t] in '. ':
                # skip, it's whitespace
                cur = track.get(pos_r, 0)
                track[pos_r] = cur + pos_t - start
            else:
                ret += text[start:pos_t]
                pos_r += pos_t - start
        elif text[pos_t] in '. ':
            cur = track.get(pos_r, 0)
            track[pos_r] = cur + 1
            pos_t += 1
        else:
            ret += text[pos_t]
            pos_t += 1
            pos_r += 1
    return (ret, track)
    
def flatten_tree(tree):
    if type(tree) == list:
        return ''.join(map(flatten_tree, tree))
    else:
        return tree

def orig_loc(loc, trace):
    return loc + sum(map(lambda s: s[1], 
        filter(lambda s: s[0] <= loc, trace.items())))

def handle_zoi(tree, text, rem, trace):
    if type(tree) != list:
        return tree
    elif len(tree) >= 3 and type(tree[0]) == str\
            and tree[0].lower() in ['zoi', 'la\'o', 'laho']:
        zoi = tree[0]
        delim = tree[1]
        inner = flatten_tree(tree[2:-1])
        flat = zoi + delim + inner + delim
        
        loc = rem.find(flat)
        if loc < 0 or inner == '':
            inner = ' '.join(tree[2:-1])
        else:
            start = orig_loc(rem[loc:loc+len(flat)].find(inner)-1, trace) + 1
            while text[start] in '. ':
                start += 1
            stop = orig_loc(loc + len(flat)-1, trace) - len(delim) - 1
            while stop > start and text[stop] in '. ':
                stop -= 1
            stop += 1
            inner = text[start:stop]
        return [zoi,delim,'"'+inner+'"',delim]
    else:
        return list(map(lambda t: handle_zoi(t, text, rem, trace), tree))
    
def camxes(text):
    text = unicodedata.normalize('NFC', text)
    pre = preprocess(text)
    tree = trim_tree(BuildTree(call_jar(pre)).build())
    flat = flatten_tree(tree)
    rem, trace = remove_track(pre)
    out = parenthize(handle_zoi(tree, text, rem, trace))
    if rem == flat:
        return out
    else:
        err_loc = orig_loc(len(flat), trace)
        return 'na gendra: ' + text[:err_loc] + '_\u26A0_ ' + text[err_loc:]

if __name__=='__main__':
    print(camxes(input()))
