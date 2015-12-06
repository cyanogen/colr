#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" colr.py
    A terminal color library for python, inspired by the javascript lib "clor".
    -Christopher Welborn 08-12-2015

    The MIT License (MIT)

    Copyright (c) 2015 Christopher Welborn

    Permission is hereby granted, free of charge, to any person obtaining a
    copy of this software and associated documentation files (the "Software"),
    to deal in the Software without restriction, including without limitation
    the rights to use, copy, modify, merge, publish, distribute, sublicense,
    and/or sell copies of the Software, and to permit persons to whom the
    Software is furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in
    all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
    FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
    DEALINGS IN THE SOFTWARE.

"""
from contextlib import suppress
from functools import partial, total_ordering
from types import GeneratorType

import math
import re
import sys

from .trans import hex2term

__version__ = '0.2.0'

__all__ = [
    '_disabled',
    'Colr',
    'auto_disable',
    'codes',
    'codeformat',
    'disable',
    'enable',
    'extbackformat',
    'extforeformat',
    'color',
    'strip_codes'
]

# Names and corresponding base code number
_namemap = (
    ('black', 0),
    ('red', 1),
    ('green', 2),
    ('yellow', 3),
    ('blue', 4),
    ('magenta', 5),
    ('cyan', 6),
    ('white', 7)
)

# Build a module-level map of fore, back, and style names to escape code.
codeformat = '\033[{}m'.format
extforeformat = '\033[38;5;{}m'.format
extbackformat = '\033[48;5;{}m'.format

# Used to strip codes from a string.
codepat = re.compile('\033\[([\d;]+)?m')


def _build_codes():
    """ Build code map, encapsulated to reduce module-level globals. """
    built = {
        'fore': {},
        'back': {},
        'style': {},
        'closing': '\033[m'
    }

    # Set codes for forecolors (30-37) and backcolors (40-47)
    # Names are given to some of the 256-color variants as 'light' colors.
    for name, number in _namemap:
        built['fore'][name] = codeformat(30 + number)
        built['back'][name] = codeformat(40 + number)
        litename = 'light{}'.format(name)
        built['fore'][litename] = codeformat(90 + number)
        built['back'][litename] = codeformat(100 + number)

    # Set reset codes for fore/back.
    built['fore']['reset'] = codeformat(39)
    built['back']['reset'] = codeformat(49)

    # Map of base code -> style name/alias.
    stylemap = (
        ('0', ('reset_all',)),
        ('1', ('b', 'bright', 'bold')),
        ('2', ('d', 'dim')),
        ('3', ('i', 'italic')),
        ('4', ('u', 'underline', 'underlined')),
        ('5', ('f', 'flash')),
        ('7', ('h', 'highlight', 'hilight', 'hilite', 'reverse')),
        ('22', ('n', 'normal', 'none'))
    )
    # Set style codes.
    for code, names in stylemap:
        for alias in names:
            built['style'][alias] = codeformat(code)

    # Extended (256 color codes)
    for i in range(256):
        built['fore'][str(i)] = extforeformat(i)
        built['back'][str(i)] = extbackformat(i)

    return built

# Raw code map, available to users.
codes = _build_codes()


# Set if disable() is called by the user, or automatically.
_disabled = False


def auto_disable(enabled=True, fds=(sys.stdout, sys.stderr)):
    """ Automatically decide whether to disable color codes if stdout or stderr
        are not ttys.

        Arguments:
            enabled  : Whether to automatically disable color codes.
                       When set to True, the fds will be checked for ttys.
                       When set to False, enable() is called.
            fds      : Open file descriptors to check for ttys.
                       If any non-ttys are found, colors will be disabled.
    """
    if enabled:
        if not all(getattr(f, 'isatty', lambda: False)() for f in fds):
            disable()
    else:
        enable()


def disable():
    """ Disable color codes for Colr and the convenience color() function.
        All output will be free of color codes by use of the Colr.color_dummy
        method where Colr.color would normally be called.
        Created to be used by auto_disable(), for piping output to file or
        other commands.
    """
    global _disabled
    _disabled = True


def disabled():
    """ Public access to _disabled. """
    return _disabled


def enable():
    """ Enable color codes for Colr and the convenience color() function.
        This only needs to be called if disable() was called previously.
    """
    global _disabled
    _disabled = False


def strip_codes(s):
    """ Strip all color codes from a string. """
    return codepat.sub('', str(s or ''))


@total_ordering
class Colr(object):

    """ This class colorizes text for an ansi terminal. """

    def __init__(self, text=None, fore=None, back=None, style=None):
        # Can be initialized with colored text, not required though.
        self.data = self.color(text or '', fore=fore, back=back, style=style)

    def __add__(self, other):
        """ Allow the old string concat methods through addition. """
        if isinstance(other, self.__class__):
            return self.__class__(''.join((self.data, other.data)))
        elif isinstance(other, str):
            return self.__class__(''.join((self.data, other)))

        raise TypeError('Colr cannot be added to non Colr/str type: {}'.format(
            getattr(other, '__class__', type(other)).__name__))

    def __bool__(self):
        """ A Colr is truthy if it has some .data. """
        return bool(self.data)

    def __call__(self, text=None, fore=None, back=None, style=None):
        """ Append text to this Colr object. """
        self.data = ''.join((
            self.data,
            self.color(text=text, fore=fore, back=back, style=style)
        ))
        return self

    def __dir__(self):
        """ Compute the fake method names, and include them in a listing
            of attributes for autocompletion/inspection.
        """

        def fmtcode(s):
            try:
                int(s)
                return 'f_{}'.format(s)
            except ValueError:
                return s

        def fmtbgcode(s):
            try:
                int(s)
                return 'b_{}'.format(s)
            except ValueError:
                return 'bg{}'.format(s)

        attrs = [fmtcode(k) for k in codes['fore']]
        attrs.extend(fmtbgcode(k) for k in codes['back'])
        attrs.extend(k for k in codes['style'])
        attrs.extend((
            'center',
            'chained',
            'color_code',
            'color',
            'data',
            'format',
            'gradient',
            'join',
            'ljust',
            'print',
            'rjust',
            'str'
        ))
        return attrs

    def __eq__(self, other):
        """ Colrs are equal if their .data is the same. """
        return isinstance(other, self.__class__) and other.data == self.data

    def __format__(self, fmt):
        """ Allow format specs to  apply to self.data """
        return str(self).__format__(fmt)

    def __getattr__(self, attr):
        """ If the attribute matches a fore, back, or style name,
            return the color() function. Otherwise, return known
            attributes and raise AttributeError for others.
        """
        knownmethod = self._attr_to_method(attr)
        if knownmethod is not None:
            return knownmethod

        try:
            val = self.__getattribute__(attr)
        except AttributeError as ex:
            try:
                val = self.data.__getattribute__(attr)
            except AttributeError:
                raise AttributeError(ex)
        return val

    def __getitem__(self, key):
        """ Allow subscripting self.data. This will ignore any escape codes,
            because otherwise it would be just about useless.
            Returns another Colr instance.
        """
        return self.__class__(strip_codes(self.data)[key])

    def __len__(self):
        """ Return len() for any built up string data. This will count color
            codes, so it's not that useful.
        """
        return len(self.data)

    def __lt__(self, other):
        """ Colr is less another color if self.data < other.data.
            Colr cannot be compared to any other type.
        """
        if not isinstance(other, self.__class__):
            raise TypeError('Cannot compare. Expected: {}, got: {}.'.format(
                self.__class__.__name__,
                getattr(other, '__class__', type(other)).__name__))
        return self.data < other.data

    def __mul__(self, n):
        """ Allow the same multiplication operator as str,
            except return a Colr.
        """
        if not isinstance(n, int):
            raise TypeError('Cannot multiply Colr by non-int type: {}'.format(
                getattr(n, '__class__', type(n)).__name__))

        return self.__class__(self.data * n)

    def __radd__(self, other):
        """ Allow a Colr to be added to a str. """
        if isinstance(other, self.__class__):
            return self.__class__(''.join((other.data, self.data)))
        elif isinstance(other, str):
            return self.__class__(''.join((other, self.data)))

        raise TypeError('Colr cannot be added to non Colr/str type: {}'.format(
            getattr(other, '__class__', type(other)).__name__))

    def __rmul__(self, n):
        return self * n

    def __repr__(self):
        return repr(self.data)

    def __str__(self):
        return self.data

    def _attr_to_method(self, attr):
        """ Return the correct color function by method name.
            Uses `partial` to build kwargs on the `color` func.
            On failure/unknown name, returns None.
        """

        if attr in codes['fore']:
            # Fore method
            return partial(self.chained, fore=attr)
        elif attr in codes['style']:
            # Style method
            return partial(self.chained, style=attr)
        elif attr.startswith('bg'):
            # Back method
            name = attr[2:]
            if name in codes['back']:
                return partial(self.chained, back=name)
        elif attr.startswith(('b256_', 'b_')):
            # Back 256 method
            # Remove the b256_ portion.
            name = attr.partition('_')[2]
            return partial(self.chained, back=name)
        elif attr.startswith(('f256_', 'f_')):
            # Fore 256 method
            name = attr.partition('_')[2]
            return partial(self.chained, fore=name)
        return None

    def _iter_gradient(
            self, text, start, step=1,
            fore=None, back=None, style=None, reverse=False):
        """ Yield colorized characters,
            using one of the 36-length gradients.
        """
        # Determine which 36-length gradient to start from.
        adj = divmod(start - 16, 36)[1]
        if adj > 0:
            start = start - adj

        # Build the color numbers needed to make a never-ending gradient.
        rows = []
        for c in range(0, 36, 6):
            rows.append([start + c + i for i in range(6)])
        numbers = []
        for i, r in enumerate(rows):
            if i % 2 != 0:
                numbers.extend(reversed(rows[i]))
            else:
                numbers.extend(rows[i])

        yield from self._iter_text_wave(
            text,
            numbers,
            step=step,
            fore=fore,
            back=back,
            style=style
        )

    def _iter_gradient_black(
            self, text, start, step=1,
            fore=None, back=None, style=None, reverse=False):
        """ Yield colorized characters,
            within the 24-length black gradient.
        """
        if start < 232:
            start = 232
        elif start > 255:
            start = 255

        yield from self._iter_text_wave(
            text,
            list(range(start, 256)),
            step=step,
            fore=fore,
            back=back,
            style=style)

    def _iter_text_wave(
            self, text, numbers, step=1,
            fore=None, back=None, style=None):
        """ Yield colorized characters from `text`, using a wave of `numbers`.
            Arguments:
                text     : String to be colorized.
                numbers  : A list/tuple of numbers (256 colors).
                step     : Number of characters to colorize per color.
                fore     : Fore color to use (name or number).
                           (Back will be gradient)
                back     : Background color to use (name or number).
                           (Fore will be gradient)
                style    : Style name to use.
        """
        if (fore is not None) and (back is not None):
            raise ValueError('Both fore and back colors cannot be specified.')

        pos = 0
        end = len(text)
        numbergen = self._iter_wave(numbers)
        for num in numbergen:
            lastchar = pos + step
            yield self.color(
                text[pos:lastchar],
                fore=num if fore is None else fore,
                back=num if fore is not None else back,
                style=style
            )
            if lastchar >= end:
                numbergen.send(True)
            pos = lastchar

    @staticmethod
    def _iter_wave(iterable, count=0):
        """ Move from beginning to end, and then end to beginning, a number of
            iterations through an iterable (must accept len(iterable)).
            Example:
                print(' -> '.join(_iter_wave('ABCD', count=8)))
                >> A -> B -> C -> D -> C -> B -> A -> B

            If `count` is less than 1, this will run forever.
            You can stop it by sending a Truthy value into the generator.
        """
        up = True
        pos = 0
        i = 0
        end = len(iterable)
        # Stop on count, or run forever.
        while (i < count) if count > 0 else True:
            try:
                stop = yield iterable[pos]
                # End of generator (user sent the stop signal)
                if stop:
                    break
            except IndexError:
                # End of iterable, when len(iterable) is < count.
                up = False

            # Change directions if needed, otherwise increment/decrement.
            if up:
                pos += 1
                if pos == end:
                    up = False
                    pos = end - 2
            else:
                pos -= 1
                if pos < 0:
                    up = True
                    pos = 1
            i += 1

    def _rainbow_color(self, freq, i):
        """ Calculate a single hexcode value for a piece of a rainbow.
            Arguments:
                freq  : "Tightness" of colors (see self.rainbow())
                i     : Index of character in string to colorize.
        """
        # Borrowed from lolcat, translated from ruby.
        red = math.sin(freq * i + 0) * 127 + 128
        green = math.sin(freq * i + 2 * math.pi / 3) * 127 + 128
        blue = math.sin(freq * i + 4 * math.pi / 3) * 127 + 128
        return '{:02x}{:02x}{:02x}'.format(int(red), int(green), int(blue))

    def _rainbow_hex(self, s, freq=0.1, spread=3.0, offset=0):
        """ Iterate over characters in a string to build data needed for a
            rainbow effect.
            Yields tuples of (char, hexcode).
            Arguments:
                s      : String to colorize.
                freq   : Frequency/"tightness" of colors in the rainbow.
                         Best results when in the range 0.0-1.0.
                         Default: 0.1
                spread : Spread/width of colors.
                         Default: 3.0
                offset : Offset for start of rainbow.
                         Default: 0
        """
        return (
            (c, self._rainbow_color(freq, offset + i / spread))
            for i, c in enumerate(s)
        )

    def _str_just(
            self, methodname, width, fillchar=' ', squeeze=False,
            **colorkwargs):
        """ Perform a str justify method on the text arg, or self.data, before
            applying color codes.
            Arguments:
                methodname  : Name of str method to apply.
                methodargs  : Arguments for the str method.

            Keyword Arguments:
                text, fore, back, style  : see color().
        """
        try:
            width = int(width)
        except ValueError as exint:
            raise ValueError('Expecting a number for width.') from exint

        newtext = ''
        with suppress(KeyError):
            # text argument overrides self.data
            newtext = str(colorkwargs.pop('text'))

        strfunc = getattr(str, methodname)
        if newtext:
            # Operating on text argument, self.data is left alone.
            strippedtxt = strip_codes(newtext)
            codelen = len(newtext) - len(strippedtxt)
            width = width + codelen
            if squeeze:
                realoldlen = len(strip_codes(self.data))
                width -= realoldlen
            return self.__class__().join(
                self,
                self.__class__(
                    strfunc(newtext, width, fillchar),
                    **colorkwargs
                )
            )

        # Operating on self.data.
        strippedtxt = strip_codes(self.data)
        codelen = len(self.data) - len(strippedtxt)
        width = width + codelen
        return self.__class__(
            strfunc(self.data, width, fillchar),
            **colorkwargs
        )

    def center(self, width, fillchar=' ', squeeze=False, **kwargs):
        """ s.center() doesn't work well on strings with color codes.
            This method will use .center() before colorizing the text.
            Returns a Colr() object.
            Arguments:
                width    : The width for the resulting string (before colors)
                fillchar : The character to pad with. Default: ' '
                squeeze  : Width applies to existing data and new data.
                           (self.data and the text arg)
            Keyword Arguments:
                text     : The string to center.
                fore, back, style : see color().
        """
        return self._str_just(
            'center',
            width,
            fillchar,
            squeeze=squeeze,
            **kwargs)

    def chained(self, text=None, fore=None, back=None, style=None):
        """ Called by the various 'color' methods to colorize a single string.
            The RESET_ALL code is appended to the string unless text is empty.
            Raises ValueError on invalid color names.

            Arguments:
                text  : String to colorize, or None for  BG/Style change.
                fore  : Name of fore color to use.
                back  : Name of back color to use.
                style : Name of style to use.
        """
        self.data = ''.join((
            self.data,
            self.color(text=text, fore=fore, back=back, style=style)
        ))
        return self

    def color(self, text=None, fore=None, back=None, style=None):
        """ A method that colorizes strings, not Colr objects.
            Raises ValueError for invalid color names.
            The 'reset_all' code is appended if text is given.
        """
        if _disabled:
            return str(text or '')
        return ''.join((
            self.color_code(fore=fore, back=back, style=style),
            str(text or ''),
            codes['closing'] if text else ''
        ))

    def color_code(self, fore=None, back=None, style=None):
        """ Return the codes for this style/colors. """

        colorcodes = []
        resetcodes = []
        userstyles = {'style': style, 'back': back, 'fore': fore}
        for stype in userstyles:
            style = userstyles.get(stype, None)
            if not style:
                continue
            stylename = str(style).lower()
            # Get escape code for this style.
            code = codes[stype].get(stylename, None)
            if not code:
                raise ValueError('Invalid color name/number: {}'.format(style))
            if stylename.startswith('reset'):
                resetcodes.append(code)
            else:
                colorcodes.append(code)
        # Reset codes come first, to not override colors.
        return ''.join((''.join(resetcodes), ''.join(colorcodes)))

    def color_dummy(self, text=None, **kwargs):
        """ A wrapper for str() that matches self.color().
            For overriding when _auto_disable is used.
        """
        return str(text or '')

    def format(self, *args, **kwargs):
        """ Like str.format, except it returns a Colr. """
        return self.__class__(self.data.format(*args, **kwargs))

    def gradient(
            self, text=None, fore=None, back=None, style=None,
            start=0, step=1, reverse=False):
        """ Colorize a string gradient style, using 256 colors.
            Arguments:
                text  : String to colorize.
                start : Starting 256-color number.
                        The `start` will be adjusted if it is not within
                        bounds.
                        This will always be > 15.
                        This will be adjusted to fit within a 6-length
                        gradient, or the 24-length black/white gradient.
                step  : Number of characters to colorize per color.
                        This allows a "wider" gradient.
                        This will always be greater than 0.
                fore  : Foreground color, background will be gradient.
                back  : Background color, foreground will be gradient.
                style : Name of style to use for the gradient.

            Returns a Colr object with gradient text.
        """
        # TODO: use rainbow() with preset names.
        # The first 16 colors (0->15) are not allowed.
        if start < 16:
            start = 16

        step = abs(int(step))
        if step < 1:
            step = 1

        if start > 231:
            # Black gradient.
            method = self._iter_gradient_black
        else:
            method = self._iter_gradient

        if text:
            return self.__class__(
                ''.join((
                    self.data or '',
                    ''.join(method(
                        text,
                        start,
                        step=step,
                        fore=fore,
                        back=back,
                        style=style,
                        reverse=reverse))
                ))
            )

        # Operating on self.data (may get messy).
        # The data must be unstyled to do this.
        return self.__class__(
            ''.join(method(
                strip_codes(self.data),
                start,
                step=step,
                fore=fore,
                back=back,
                style=style,
                reverse=reverse)))

    def join(self, *colrs, **colorkwargs):
        """ Like str.join, except it returns a Colr.
            Arguments:
                colrs  : One or more Colrs. If a list or tuple is passed as an
                         argument it will be flattened.
            Keyword Arguments:
                fore, back, style...
                see color().
        """
        flat = []
        for clr in colrs:
            if isinstance(clr, (list, tuple, GeneratorType)):
                # Flatten any lists, at least once.
                flat.extend(str(c) for c in clr)
            else:
                flat.append(str(clr))

        if colorkwargs:
            fore = colorkwargs.get('fore', None)
            back = colorkwargs.get('back', None)
            style = colorkwargs.get('style', None)
            flat = (
                self.color(s, fore=fore, back=back, style=style)
                for s in flat
            )
        return self.__class__(self.data.join(flat))

    def ljust(self, width, fillchar=' ', squeeze=False, **kwargs):
        """ s.ljust() doesn't work well on strings with color codes.
            This method will use .ljust() before colorizing the text.
            Returns a Colr() object.
            Arguments:
                width    : The width for the resulting string (before colors)
                fillchar : The character to pad with. Default: ' '
                squeeze  : Width applies to existing data and new data.
                           (self.data and the text arg)
            Keyword Arguments:
                text     : The string to left-justify.
                fore, back, style : see color().
        """
        return self._str_just(
            'ljust',
            width,
            fillchar,
            squeeze=squeeze,
            **kwargs)

    def print(self, *args, **kwargs):
        """ Chainable print method. Prints self.data and then clears it. """
        print(self, *args, **kwargs)
        self.data = ''
        return self

    def rainbow(
            self, text=None, fore=None, back=None, style=None,
            freq=0.1, offset=0, spread=3.0):
        """ Make rainbow gradient text.
            Arguments:
                text   : Text to make gradient.
                         Default: self.data
                fore   : Fore color to use (makes back the rainbow).
                         Default: None
                back   : Back color to use (makes fore the rainbow).
                         Default: None
                style  : Style for the rainbow.
                         Default: None
                freq   : Frequency of color change, a higher value means more
                         colors. Best results when in the range 0.0-1.0.
                         Default: 0.1
                offset : Offset for start of rainbow.
                         Default: 0
                spread : Spread/width of each color.
                         Default: 3.0
        """
        if fore and back:
            raise ValueError('Cannot use both fore and back with rainbow()')

        if fore:
            color_args = (lambda hexval: {
                'back': hex2term(hexval),
                'style': style,
                'fore': fore
            })
        else:
            color_args = (lambda hexval: {
                'fore': hex2term(hexval),
                'style': style,
                'back': back
            })

        if text:
            # Prepend existing self.data to the rainbow text.
            return self.__class__(
                ''.join((
                    self.data,
                    ''.join(
                        self.color(c, **color_args(hval))
                        for c, hval in self._rainbow_hex(
                            text, freq=freq,
                            spread=spread,
                            offset=offset)
                    )
                ))
            )

        # Operate on self.data.
        return self.__class__(
            ''.join(
                self.color(c, **color_args(hval))
                for c, hval in self._rainbow_hex(
                    strip_codes(self.data),
                    freq=freq,
                    spread=spread,
                    offset=offset)
            )
        )

    def rjust(self, width, fillchar=' ', squeeze=False, **kwargs):
        """ s.rjust() doesn't work well on strings with color codes.
            This method will use .rjust() before colorizing the text.
            Returns a Colr() object.
            Arguments:
                width    : The width for the resulting string (before colors)
                fillchar : The character to pad with. Default: ' '
                squeeze  : Width applies to existing data and new data.
                           (self.data and the text arg)
            Keyword Arguments:
                text     : The string to right-justify.
                fore, back, style : see color().
        """
        return self._str_just(
            'rjust',
            width,
            fillchar,
            squeeze=squeeze,
            **kwargs)

    def str(self):
        """ Alias for self.__str__ """
        return str(self)

# Shortcuts.
color = Colr().color

if __name__ == '__main__':
    if ('--auto-disable' in sys.argv) or ('-a' in sys.argv):
        auto_disable()

    print(
        Colr('warning', 'red')
        .join('[', ']', style='bright')(' ')
        .green('This module is meant to be ran with `python -m colr.`')
    )
