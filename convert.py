#!/usr/bin/env python
import datetime
import dateutil.parser
import re

header = r"""\documentclass[twocolumn]{book}

\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[bitstream-charter]{mathdesign}
\usepackage{color}

\setlength{\columnsep}{1in}
\flushbottom
\newcommand{\onleft}[1]{\makebox[0em][r]{{#1}\hspace*{0.1in}}}
\setlength{\oddsidemargin}{2em}
\setlength{\parindent}{0em}

% from http://www.wilmott.com/messageview.cfm?catid=10&threadid=58335
\usepackage[hang, splitrule]{footmisc}
\addtolength{\footskip}{0.5cm}
\setlength{\footnotemargin}{0.3cm}
\setlength{\footnotesep}{0.4cm}
\makeatletter
\let\splitfootnotrule=\pagefootnoterule
\makeatother

% from http://stackoverflow.com/questions/256457/how-does-one-insert-a-backslash-or-a-tilde-into-latex
\newcommand{\mytilde}{{\raise.17ex\hbox{$\scriptstyle\mathtt{\sim}$}}}

\definecolor{grey}{gray}{0.75}
\newcommand{\grey}[1]{\textcolor{grey}{#1}}
\newcommand{\name}[1]{\textsf{\small{#1}}}
\newcommand{\actstar}{*\hspace*{-0.15em}}
\newcommand{\metabullet}{\grey{$\triangleright$}}
\newcommand{\degrees}{$^\circ$}
\newcommand{\urlind}{\textsc{{\scriptsize[}url{\scriptsize]}}}

\begin{document}

"""

footer = r"""

\end{document}
"""

escapes = dict(line.strip().split(' ', 1) for line in r"""
    $ \$
    _ \_
    # \#
    ^ \symbol{94}
    & \&
    { \{
    } \}
    [ {[}
    ] {]}
    < \textless{}
    > \textgreater{}
    \ \symbol{92}
    ~ $\mytilde$
    - -{}
    / /\linebreak[3]
    ` \`{}
""".split(u'\n') if line.strip())

escapes['\x02'] = u'\\bf'

url_re = r'''(http://\S+(?<![,.;:\]*!'"<>]))'''

simple_replacements = {
    "i'm": "I'm", "i'd": "I'd", "i've": "I've", "i'll": "I'll",
}

regexp_replacements = [(re.compile(k), v) for k, v in {
    url_re: u'\\urlind\\footnote{%s}',
    '<3': ur'$\heartsuit$',
    r'(?<!\.)(\.{3,5})(?!\.)': ur'\ldots{}',
    r'(?<!\S)(-?[1-4]?\d(?:\.\d)?\*[cC]?)(?!\S)':
        lambda s: s.replace('*', '\\degrees{}'),
    r'(\^-?\d+(?:\.\d+)?)': lambda n: '$^{%s}$' % n.replace(escapes['^'], ''),
}.iteritems()]

def escape_fragment(frag):
    frag = u''.join(escapes.get(c, c) for c in frag)
    return frag

def escape_line(line, multis=None):
    if multis is None:
        for k, v in simple_replacements.iteritems():
            line = line.replace(k, v)
        multis = regexp_replacements
    if not multis:
        return escape_fragment(line)
    regexp, repl = multis[0]
    output = []
    mid = True
    for frag in regexp.split(line):
        frag = escape_line(frag, multis[1:])
        mid = not mid
        if not mid:
            output.append(frag)
        elif isinstance(repl, basestring):
            output.append(repl % frag if '%s' in repl else repl)
        else:
            output.append(repl(frag))
    return ''.join(output)

def comma_join(list):
    if len(list) == 0: return ''
    elif len(list) == 1: return list[0]
    elif len(list) == 2: return '%s and %s' % tuple(list)
    return '%s, and %s' % (', '.join(list[:-1]), list[-1])


def prettify_line(line, wrap):
    if len(line) > 1 and line.startswith('"') and line.endswith('"'):
        wrap = u"``{}%s{}''" % wrap
        line = line[1:-1]
        if line.startswith("'"):
            wrap = wrap.replace('%s', '`%s')
            line = line[1:]
    if line.startswith('^') and line.count('^') == 1:
        line = u'$\\uparrow$%s' % escape_line(line[1:])
    elif re.match(url_re + '$', line):
        line = r'\small{http{}://%s}' % escape_line(line[7:])
    else:
        line = escape_line(line)
    return line, wrap

class Meta:
    __slots__ = ['name', 'msgs']
    def __init__(self, name, msgs):
        self.name = name
        self.msgs = msgs

def extract_meta(line):
    nick, msg = line[3:].strip().lower().split(None, 1)
    if msg == 'has quit irc' or msg == 'has left #uweng':
        msg = 'left'
    elif msg == 'has joined #uweng':
        msg = 'joined'
    else: # TODO: chanserv, kicks, bans, modes, leaves
        pass
    return Meta(nick, [msg])

def collapse_meta(meta):
    collapsed = []
    while meta:
        first = meta.pop(0)
        while meta and meta[0].name == first.name:
            first.msgs += meta.pop(0).msgs
        collapsed.append(u'%s %s' % (escape_line(first.name),
                escape_line(comma_join(first.msgs))))
    return collapsed

number_re = re.compile('(\d+)')
def small_caps(text):
    return ur'\textsc{%s}' % number_re.sub(
            lambda m: ur'{\scriptsize{}%s}' % m.group(1), text)

def format_time(hour, minute):
    if hour == 0:
        return (12, minute, 'a.m.')
    elif hour < 12:
        return (hour, minute, 'a.m.')
    elif hour == 12:
        return (12, minute, 'p.m.')
    else:
        return (hour - 12, minute, 'p.m.')

class State:
    __slots__ = ['last_time', 'converted', 'cantide_lst']
    def __init__(self):
        self.last_time = tuple()
        self.converted = []
        self.cantide_lst = False

def convert(log_filename):
    last_name = None
    converted = []
    meta_time = tuple()
    meta_queue = []
    state = State()

    def output(line='', wrap_line='%s', left='', right='', this_time=0,
            state=state, **k):

        if this_time[:3] != state.last_time[:3]: # new day
            state.last_time = tuple()
            date = datetime.date(*this_time[:3])
            state.converted.append(ur'\chapter*{%s}' % date.strftime(
                    '%A, %B %d').replace(' 0', ' '))
        if this_time[:4] != state.last_time[:4]: # new hour
            state.last_time = this_time
            h, m, ampm = format_time(*this_time[3:5])
            right = ur'\makebox[2em][r]{%d}:%02d %s' % (h, m, ampm)
        elif this_time[:5] != state.last_time[:5]: # new minute
            state.last_time = this_time
            right = ur'\hspace{2em}:%02d' % this_time[4]
        if right:
            right = ur'\grey{%s}' % right

        wrap_line = u'{%s}' % wrap_line
        if left or right:
            wrap_line = ur'\onleft{%s}{%s}' % (left, wrap_line)

        state.converted.append(wrap_line % line)

    for line in file(log_filename, 'r'):
        left = right = ''
        wrap_line = u'%s'
        timestamp, sp, line = line.partition('  ')

        line = line.strip().decode('utf-8')
        this_time = dateutil.parser.parse(timestamp).timetuple()[:5]

        if line.startswith('***'):
            # meta info
            last_name = None
            meta_queue.append(extract_meta(line))
            if not meta_time:
                meta_time = this_time
            continue
        elif meta_queue:
            output(line=small_caps('; '.join(collapse_meta(meta_queue))),
                   wrap_line=wrap_line,
                   left=r'\metabullet{}', right='',
                   this_time=meta_time)
            meta_queue = []
            meta_time = None

        if line.startswith('* '):
            # action
            line = escape_line(line)
            last_name = None
            left = r'\actstar'
            line = line[1:].strip()
            wrap_line = ur'\textit{%s}' % wrap_line
        else:
            # chat
            assert line.startswith('<')
            name, r, line = line.lstrip('<').partition('>')
            line = line.strip()
            if name == 'cantide' and state.cantide_lst and len(line) > 300:
                state.cantide_lst = False
                line = ur'\ldots'
            else:
                if line == '!lst':
                    state.cantide_lst = True
                line, wrap_line = prettify_line(line, wrap_line)
            left = ur'\name{%s}' % escape_fragment(name)
            if name != last_name:
                last_name = name
            else:
                left = ur'\grey{%s}' % left

        output(**locals())

    all = u'%s%s%s' % (header, '\n\n'.join(state.converted), footer)
    return all.encode('utf-8')

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print "Usage: %s [log file]" % sys.argv[0]
    out = convert(sys.argv[1])
    file(sys.argv[1] + '.tex', 'w').write(out)

# vi: set sw=4 ts=4 sts=4 tw=79 ai et nocindent:
