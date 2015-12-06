#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" colr.__main__.py
    Provides a basic cmdline tool for color-formatted text.
    Example:
        python3 -m colr "Hello World" "green"
        # or:
        python3 -m colr "Hello World" -s "bright" -f "green"
    -Christopher Welborn 12-05-2015
"""
# TODO: rainbow().

import os
import sys

from .colr import (
    __version__,
    Colr as C,
    auto_disable,
    disabled,
    strip_codes,
)

from .trans import ColorCode

try:
    from docopt import docopt
except ImportError as eximp:
    print('\n'.join((
        'Import error: {}',
        '\nThe colr tool requires docopt to parse command line args.',
        'You can install it using pip:',
        '    pip install docopt'
    )).format(eximp))
    sys.exit(1)

NAME = 'Colr Tool'
VERSIONSTR = '{} v. {}'.format(NAME, __version__)
SCRIPT = os.path.split(os.path.abspath(sys.argv[0]))[1]
SCRIPTDIR = os.path.abspath(sys.path[0])

USAGESTR = """{versionstr}
    Usage:
        {script} -h | -v
        {script} [TEXT] [FORE] [BACK] [STYLE]
                 [-a] [-e] [-c num | -l num | -r num] [-n]
        {script} [TEXT] [-f fore] [-b back] [-s style]
                 [-a] [-e] [-c num | -l num | -r num] [-n]
        {script} [TEXT] [FORE] [BACK] [STYLE]
                 [-a] [-e] [-c num | -l num | -r num] [-n] -g num [-p num]
        {script} [TEXT] [-f fore] [-b back] [-s style ]
                 [-a] [-e] [-c num | -l num | -r num] [-n] -g num [-p num]
        {script} [TEXT] [FORE] [BACK] [STYLE]
                 [-a] [-e] [-c num | -l num | -r num] [-n] -R [-o num] [-q num] [-w num]
        {script} [TEXT] [-f fore] [-b back] [-s style]
                 [-a] [-e] [-c num | -l num | -r num] [-n] -R [-o num] [-q num] [-w num]
        {script} -x [TEXT] [-a] [-e] [-c num | -l num | -r num] [-n]
        {script} -t [CODE...]

    Options:
        CODE                      : One or more codes to translate.
        TEXT                      : Text to print. If not given, stdin is used.
        FORE                      : Name or number for fore color to use.
        BACK                      : Name or number for back color to use.
        STYLE                     : Name for style to use.
        -a,--auto-disable         : Automatically disable colors when output
                                    target is not a terminal.
        -b name,--back name       : Name or number for back color to use.
        -c num,--center num       : Center justify the text before coloring,
                                    using `num` as the overall width.
        -e,--err                  : Print to stderr instead of stdout.
        -f name,--fore name       : Name or number for fore color to use.
        -g num,--gradient num     : Use the gradient method starting at `num`.
                                    Default: 17
        -h,--help                 : Show this help message.
        -l num,--ljust num        : Left justify the text before coloring,
                                    using `num` as the overall width.
        -n,--newline              : Do not append a newline character (\\n).
        -o num,--offset           : Offset for start of rainbow.
                                    Default: 0
        -p num,--step num         : Number of characters per color step when
                                    using --gradient.
                                    Default: 1
        -q num,--frequency num    : Frequency of colors in the rainbow.
                                    Higher value means more colors.
                                    Best when in the range 0.0-1.0.
                                    Default: 0.1
        -r num,--rjust num        : Right justify the text before coloring,
                                    using `num` as the overall width.
        -R,--rainbow              : Use the rainbow method.
        -s name,--style name      : Name for style to use.
        -t,--translate            : Translate one or more term codes,
                                    hex values, or rgb values.
        -w num,--spread num       : Spread/width of each color in the rainbow.
                                    Default: 3.0
        -x,--stripcodes           : Strip all color codes from text.
        -v,--version              : Show version.

    Colors and style names can be given in any order when flags are used.
    Without using the flags, they must be given in order (fore, back, style).

""".format(script=SCRIPT, versionstr=VERSIONSTR)  # noqa


def main(argd):
    """ Main entry point, expects doctopt arg dict as argd. """
    if argd['--auto-disable']:
        auto_disable()

    if argd['--translate']:
        # Just translate a simple code and exit.
        print('\n'.join(translate(argd['CODE'] or read_stdin().split())))
        return 0

    txt = argd['TEXT'] or read_stdin()
    fd = sys.stderr if argd['--err'] else sys.stdout
    end = '' if argd['--newline'] else '\n'

    fore = get_name_arg(argd, '--fore', 'FORE', default=None)
    back = get_name_arg(argd, '--back', 'BACK', default=None)
    style = get_name_arg(argd, '--style', 'STYLE', default=None)

    if argd['--gradient']:
        # Build a gradient from user args.
        clr = C(txt).gradient(
            start=try_int(argd['--gradient'], 17, minimum=0),
            step=try_int(argd['--step'], 1, minimum=0),
            fore=fore,
            back=back,
            style=style
        )
    elif argd['--rainbow']:
        clr = C(txt).rainbow(
            fore=fore,
            back=back,
            style=style,
            freq=try_float(argd['--frequency'], 0.1, minimum=0),
            offset=try_int(argd['--offset'], 0, minimum=0),
            spread=try_float(argd['--spread'], 3.0, minimum=0)
        )
    elif argd['--stripcodes']:
        txt = justify(strip_codes(txt), argd)
        print(txt, file=fd, end=end)
        return 0

    else:
        # Normal colored output.
        clr = C(txt, fore=fore, back=back, style=style)

    # Justify options...
    clr = justify(clr, argd)

    print(str(clr), file=fd, end=end)
    return 0


def get_name_arg(argd, *argnames, default=None):
    """ Return the first argument value given.
        When not given, return default.
    """
    val = None
    for argname in argnames:
        if argd[argname]:
            val = argd[argname].lower().strip()
            break
    return val if val else default


def justify(clr, argd):
    """ Justify str/Colr based on user args. """
    if argd['--ljust']:
        return clr.ljust(try_int(argd['--ljust'], minimum=0))
    if argd['--rjust']:
        return clr.rjust(try_int(argd['--rjust'], minimum=0))
    if argd['--center']:
        return clr.center(try_int(argd['--center'], minimum=0))
    return clr


def read_stdin():
    """ Read text from stdin, and print a helpful message for ttys. """
    if sys.stdin.isatty() and sys.stdout.isatty():
        print('\nReading from stdin until end of file (Ctrl + D)...')

    return sys.stdin.read()


def translate(codes):
    """ Translate one or more hex, term, or rgb value into the others.
        Yields strings with the results for each code translated.
    """
    for code in codes:
        if ',' in code:
            try:
                r, g, b = (int(c.strip()) for c in code.split(','))
            except (TypeError, ValueError):
                raise InvalidNumber(code, label='Invalid rgb value:')
            code = (r, g, b)

        colorcode = ColorCode(code)
        if disabled():
            yield str(colorcode)

        yield colorcode.example()


def try_float(s, default=None, minimum=None):
    """ Try parsing a string into a float.
        If None is passed, default is returned.
        On failure, InvalidFloat is raised.
    """
    if not s:
        return default
    try:
        val = float(s)
    except (TypeError, ValueError):
        raise InvalidNumber(s, label='Invalid float value:')
    if (minimum is not None) and (val < minimum):
        val = minimum
    return val


def try_int(s, default=None, minimum=None):
    """ Try parsing a string into an integer.
        If None is passed, default is returned.
        On failure, InvalidNumber is raised.
    """
    if not s:
        return default
    try:
        val = int(s)
    except (TypeError, ValueError):
        raise InvalidNumber(s)
    if (minimum is not None) and (val < minimum):
        val = minimum
    return val


class InvalidNumber(ValueError):
    """ A ValueError for when parsing an int fails.
        Provides a better error message.
    """

    def __init__(self, string, label=None):
        self.string = string
        self.label = label or 'Invalid number:'

    def __str__(self):
        return '{s.label} {s.string}'.format(s=self)


if __name__ == '__main__':
    try:
        mainret = main(docopt(USAGESTR, version=VERSIONSTR))
    except (EOFError, KeyboardInterrupt):
        print('\nUser cancelled.\n', file=sys.stderr)
        mainret = 2
    except BrokenPipeError:
        print(
            '\nBroken pipe, input/output was interrupted.\n',
            file=sys.stderr)
        mainret = 3
    except InvalidNumber as exnum:
        print('\n{}'.format(exnum), file=sys.stderr)
        mainret = 4

    sys.exit(mainret)