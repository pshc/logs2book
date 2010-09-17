#!/usr/bin/env python
import datetime
import re
import settings

HEADER = r"""\documentclass[twocolumn]{book}

\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[bitstream-charter]{mathdesign}
\usepackage{color}

\usepackage{multicol}
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

\definecolor{grey}{gray}{0.5}
\newcommand{\grey}[1]{\textcolor{grey}{#1}}
\newcommand{\nick}[1]{\textsf{\small{#1}}}
\newcommand{\bracketnick}[1]{\nick{{\raise.30ex\hbox{\small$\langle\,$}}#1{\raise.30ex\hbox{\small$\,\rangle$}}}}
\newcommand{\act}[1]{\textit{#1}}
\newcommand{\actstar}{*\hspace*{-0.15em}}
\newcommand{\metabullet}{\grey{$\triangleright$}\hspace*{-0.15em}}
\newcommand{\degrees}{$^\circ$}
\newcommand{\urlind}{\textsc{{\scriptsize[}url{\scriptsize]}}}

\begin{document}
\begin{titlepage}
\begin{flushright}

{\LARGE $CHANNEL}

{\Large $TIMEFRAME}

\end{flushright}
\end{titlepage}

\onecolumn

% Meta
\thispagestyle{empty}
\begin{center}
\small

This book is not for consumption by non-humans.

No reproduction of any part may take place.

\vspace{1em}

\copyright $CHANNEL, $YEAR_PUBLISHED

\vspace{1em}

$URL

\end{center}
\newpage

\begin{center}
\thispagestyle{empty}
$DEDICATION
\end{center}
\newpage

\mbox{} % Blank page
\thispagestyle{empty}
\newpage

% Content
\twocolumn

"""

FOOTER = r"""

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
    @ @\linebreak[3]
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

nick_chars = r'[a-zA-Z_\[\]\\`^{|}][\w\[\]\\`^{|}\-]{0,12}'
nick_re = re.compile(r'(?:^|\s)(<NC>|\* NC)\s'.replace('NC', nick_chars))

more_re = re.compile('(\(\d\d? more messages?\))$')

vote_re = re.compile(r'Question: .* -- Results: Yes: (\d+) -- No: (\d+) --\s*$'
        .replace(' ', '\\s+'))

def prettify_line(nick, line, wrap):
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
    elif is_bot(nick) and nick_re.search(line): # format !rq
        pieces = nick_re.split(line)
        first_bit = escape_line(pieces.pop(0))
        first_bit += first_bit.strip() and ' '
        quotes = []
        while pieces:
            nick = pieces.pop(0)
            q = pieces.pop(0)
            if not q: # yes, twice
                q += ' ' + pieces.pop(0)
                q += ' ' + pieces.pop(0)
            q = escape_line(q)
            if nick.startswith('* '):
                q = r'* \act{%s %s}' % (escape_line(nick[2:]), q)
            else:
                q = r'\bracketnick{%s} %s' % (escape_line(nick[1:-1]), q)
            quotes.append(q)
        line = '%s%s' % (first_bit, '\n\n'.join(quotes))
    elif is_bot(nick) and vote_re.match(line):
        m = vote_re.match(line)
        line = '%s --- %s' % m.groups()
    else:
        line = escape_line(line)
    line = more_re.sub(lambda m: r'\textit{%s}' % m.group(1), line)
    return line, wrap

class Meta:
    __slots__ = ['name', 'msgs']
    def __init__(self, name, msgs):
        self.name = name
        self.msgs = msgs

mode_re = re.compile(r'sets mode:\s+([+\-][a-zA-Z+\-]+)\s+(.+)')

def extract_meta(line):
    nick, msg = line[3:].strip().lower().split(None, 1)
    if msg == 'has quit irc' or msg == 'has left #uweng':
        msg = 'left'
    elif msg == 'has joined #uweng':
        msg = 'joined'
    elif msg.startswith('sets mode:'):
        m = mode_re.match(msg)
        assert m, 'Unrecognized mode syntax: ' + msg
        def parse_modes(state, char):
            accum, pm = state
            return (accum, char) if char in '+-' else (accum + [pm+char], pm)
        modes, pm = reduce(parse_modes, m.group(1), ([], '+'))
        args = m.group(2).split()
        nm = args[0]
        if all(a == args[0] for a in args):
            credit = lambda s: (s if nick in ['chanserv', 'x']
                                  else s + ' by ' + nick)
            if '+o' in modes and '-o' not in modes:
                nick, msg = nm, credit('was opped')
            elif '-o' in modes and '+o' not in modes:
                nick, msg = nm, credit('was deopped')
            elif '+v' in modes and '-v' not in modes:
                nick, msg = nm, credit('was voiced')
            elif '-v' in modes and '+v' not in modes:
                nick, msg = nm, credit('was devoiced')
    else: # TODO: kicks, bans
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

def is_bot(nick):
    return nick.startswith('canti')

class State:
    __slots__ = ['last_time', 'converted', 'bot_lst']
    def __init__(self):
        self.last_time = tuple()
        self.converted = []
        self.bot_lst = False

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
        this_time = datetime.datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S'
                ).timetuple()[:5]
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
            wrap_line = ur'\act{%s}' % wrap_line
        else:
            # chat
            assert line.startswith('<')
            name, r, line = line.lstrip('<').partition('>')
            line = line.strip()
            if is_bot(name) and state.bot_lst and len(line) > 300:
                state.bot_lst = False
                line = ur'\ldots'
            else:
                if line == '!lst':
                    state.bot_lst = True
                line, wrap_line = prettify_line(name, line, wrap_line)
            left = ur'\nick{%s}' % escape_fragment(name)
            if name != last_name:
                last_name = name
            else:
                left = ur'\grey{%s}' % left

        output(**locals())

    header = reduce(lambda h, r: h.replace(r[0], r[1]),
            settings.SETTINGS.iteritems(), HEADER)
    all = u'%s%s%s' % (header, '\n\n'.join(state.converted), FOOTER)
    return all.encode('utf-8')

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print "Usage: %s [log file]" % sys.argv[0]
    out = convert(sys.argv[1])
    file(sys.argv[1] + '.tex', 'w').write(out)

# vi: set sw=4 ts=4 sts=4 tw=79 ai et nocindent:
