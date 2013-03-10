from subprocess import Popen, PIPE

class ParsingError(ValueError):
    pass

class ParseUtil():
    def __init__(self, resp):
        self.resp = resp
        self.pos = 0

    def at(self):
        return self.resp[self.pos]
    
    def inc(self, Δ=1):
        self.pos += Δ

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
                node.append(self.build())
                self.assert_at(')')
                self.inc()
            else:
                node.append(ident)
            self.skip_whitespace()
        return node

def trim_tree(tree):
    while type(tree) == list and len(tree) == 1:
        tree = tree[0]
    if type(tree) == list:
        return list(map(trim_tree, tree))
    else:
        return tree

def flatten_zoi(tree):
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

def camxes(sentence):
    return parenthize(flatten_zoi(trim_tree(
        BuildTree(call_jar(sentence)).build())))

if __name__=='__main__':
    print(camxes(input()))
