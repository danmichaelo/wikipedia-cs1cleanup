# encoding=utf8
from __future__ import unicode_literals

import os
import psutil
import sys
import string
import re
import sys
import time
import argparse
import codecs
import json
from datetime import datetime
from six.moves.urllib.parse import quote
from six.moves import input

from mwclient import Site
from mwtemplates import TemplateEditor

from .correct import correct

import logging


def memory_usage_psutil():
    # return the memory usage in MB
    process = psutil.Process(os.getpid())
    mem = process.memory_info()[0] / float(2 ** 20)
    return mem

logger = logging.getLogger('cs1cleanup')

checked_manually = {}

if os.path.exists('checked_manually.txt'):
    with codecs.open('checked_manually.txt', 'r', 'utf8') as f:
        for line in f.read().split('\n'):
            line = line.split('===')
            if len(line) == 2:
                checked_manually[line[0]] = line[1]

logger.debug('Read %d entries from checked_manually.txt', len(checked_manually))

months = ['januar', 'februar', 'mars', 'april', 'mai', 'juni', 'juli', 'august', 'september', 'oktober', 'november', 'desember']
seasons = ['våren', 'sommeren', 'høsten', 'vinteren', 'julen']
monthsdict = {
    'jan': 'januar',
    'feb': 'februar',
    'mar': 'mars',
    'apr': 'april',
    'jun': 'juni',
    'jul': 'juli',
    'aug': 'august',
    'sep': 'september',
    'sept': 'september',
    'oct': 'oktober',
    'okt': 'oktober',
    'nov': 'november',
    'dec': 'desember',
    'des': 'desember',
    'march': 'mars',
    'января': 'januar',
    'февраля': 'februar',
    'марта': 'mars',
    'апреля': 'april',
    'мая': 'mai',
    'июня': 'juni',
    'июля': 'juli',
    'августа': 'august',
    'сентября': 'september',
    'октября': 'oktober',
    'ноября': 'november',
    'декабря': 'desember',
}
seasonsdict = {
    'vår': 'våren',
    'sommer': 'sommeren',
    'høst': 'høsten',
    'vinter': 'vinteren',
    'spring': 'våren',
    'summer': 'sommeren',
    'autumn': 'høsten',
    'fall': 'høsten',
    'winter': 'vinteren',
    'christmas': 'julen',
}
current_year = time.localtime().tm_year


def get_month(val):
    val = val.lower()
    if NumericMonthValidator(val).valid:
        return val
    if MonthValidator(val).valid:
        return val
    elif val in monthsdict:
        return monthsdict[val]
    else:
        suggest = correct(val)
        if suggest != val:
            return suggest
    logger.debug('Could not match "%s" to month or season name', val)
    return None


def get_month_or_season(val):
    val = val.lower()
    if MonthValidator(val, True).valid:
        return val
    elif val in monthsdict:
        return monthsdict[val]
    elif val in seasonsdict:
        return seasonsdict[val]
    else:
        suggest = correct(val)
        if suggest != val:
            return suggest
    return None


class Validator(object):

    def __init__(self, value):
        self.problem = None
        self.value = value.strip()
        self.valid = True
        self.validate()

    def validate(self):
        pass

    def is_valid(self):
        return True

    def is_invalid(self, problem=None):
        self.valid = False
        self.problem = problem
        return False


class YearValidator(Validator):

    def not_future_year(self, value):
        if int(value) >= current_year + 2:
            return self.is_invalid('Publiseringsår mer enn ett år inn i fremtiden')

        return self.is_valid()

    def validate(self):
        if re.match('^$', self.value):
            return self.is_valid()  # It's empty, that's ok

        # 2014
        m = re.match('^(\d{4})$', self.value)
        if m:
            # Publication dates should normally not be in the future
            return self.not_future_year(m.group(1))

        m = re.match('^ca?\. (\d{4})$', self.value)
        if m:
            return self.not_future_year(m.group(1))

        return self.is_invalid()


class MonthValidator(Validator):

    def __init__(self, value, include_seasons=False):
        self.include_seasons = include_seasons
        super(MonthValidator, self).__init__(value)

    def validate(self):
        if len(self.value) < 2:
            return self.is_invalid('Ikke kjent navn på måned eller årstid')
        value = self.value[0].lower() + self.value[1:]  # ignore case on first character
        if value not in months and (not self.include_seasons or value not in seasons):
            return self.is_invalid('Ikke kjent navn på måned eller årstid')
        return self.is_valid()


class NumericMonthValidator(Validator):

    def validate(self):
        try:
            value = int(self.value)
            if value < 1 or value > 12:
                return self.is_invalid('Månedsnummer utenfor rekkevidde 1-12')
            return self.is_valid()

        except ValueError:
            return self.is_invalid('Ukjent månedsnummer')


class DateValidator(Validator):

    def check_year(self, value):
        validator = YearValidator(value)
        if not validator.valid:
            return self.is_invalid(validator.problem)
        return True

    def check_numeric_month(self, value):
        validator = NumericMonthValidator(value)
        if not validator.valid:
            return self.is_invalid(validator.problem)
        return True

    def check_month(self, value, include_seasons):
        validator = MonthValidator(value, include_seasons)
        if not validator.valid:
            return self.is_invalid(validator.problem)
        return True

    def check_day(self, value, allow_zero_prefix=True):
        try:
            ival = int(value)
            if ival < 1 or ival > 31:
                return self.is_invalid('Dag utenfor rekkevidde 1-31')
            if not allow_zero_prefix and str(ival) != value:
                return self.is_invalid('Dag har 0-prefiks')
            return self.is_valid()
        except ValueError:
            return self.is_invalid('Klarte ikke å tolke dagverdien')

    def validate(self):

        if re.match('^$', self.value):
            # print 'Warning: empty date found'
            return self.is_valid()  # empty

        if re.match('^udatert$', self.value):
            return self.is_valid()

        if re.match('^u\.d\.$', self.value):
            return self.is_valid()

        # 2014-01-01
        m = re.match('^(\d{4})-(\d{2})-(\d{2})$', self.value)
        if m:
            return self.check_year(m.group(1)) and self.check_numeric_month(m.group(2)) and self.check_day(m.group(3))

        # 2014, ca. 2014
        m = re.match('^(ca?\. )?(\d{4})$', self.value)
        if m:
            return self.check_year(m.group(2))

        # 2014–2015
        m = re.match('^(\d{4})–(\d{4})$', self.value)
        if m:
            return self.check_year(m.group(1)) and self.check_year(m.group(2))

        # 1.1.2001
        m = re.match('^(\d\d?)\.(\d\d?)\.(\d{4})$', self.value)
        if m:
            return self.check_day(m.group(1)) and self.check_numeric_month(m.group(2)) and self.check_year(m.group(3))

        # 1. januar 2014
        m = re.match('^(\d\d?)\. ([a-z]+) (\d{4})$', self.value)
        if m:
            q = self.check_day(m.group(1), False) and self.check_month(m.group(2), False) and self.check_year(m.group(3))
            return q

        # 1.–2. januar 2014
        m = re.match('^(\d\d?)\.–(\d\d?)\. ([a-z]+) (\d{4})$', self.value)
        if m:
            return self.check_day(m.group(2), False) and self.check_day(m.group(2), False) and self.check_month(m.group(3), False) and self.check_year(m.group(4))

        # 1. januar – 2. februar 2014
        m = re.match('^(\d\d?)\. ([a-z]+) – (\d\d?)\. ([a-z]+) (\d{4})$', self.value)
        if m:
            return self.check_day(m.group(1), False) and self.check_month(m.group(2), False) and self.check_day(m.group(3), False) and self.check_month(m.group(4), False) and self.check_year(m.group(5))

        # 1. januar 2014 – 1. februar 2015
        m = re.match('^(\d\d?)\. ([a-z]+) (\d{4}) – (\d\d?)\. ([a-z]+) (\d{4})$', self.value)
        if m:
            return self.check_day(m.group(1), False) and self.check_month(m.group(2), False) and self.check_year(m.group(3)) and self.check_day(m.group(4), False) and self.check_month(m.group(5), False) and self.check_year(m.group(6))

        # januar 2014
        m = re.match('^([A-Za-zøå]+) (\d{4})$', self.value)
        if m:
            return self.check_month(m.group(1), True) and self.check_year(m.group(2))

        # januar–februar 2014
        m = re.match('^([A-Za-zøå]+)–([a-z]+) (\d{4})$', self.value)
        if m:
            return self.check_month(m.group(1), True) and self.check_month(m.group(2), True) and self.check_year(m.group(3))

        # januar 2014 – februar 2015
        m = re.match('^([A-Za-zøå]+) (\d{4}) – ([a-zøå]+) (\d{4})$', self.value)
        if m:
            return self.check_month(m.group(1), True) and self.check_year(m.group(2)) and self.check_month(m.group(3), True) and self.check_year(m.group(4))

        return self.is_invalid()


class VisitDateValidator(DateValidator):
    # Should not be more than 10 years in the past
    pass


def get_year_suggestion(val):

    cleaned_val = pre_clean(val)

    # Ca. 2011 / c. 2011 / c2011
    m = re.match('^ca?.? ?(\d{4})$', val, flags=re.I)
    if m:
        cleaned_val = 'ca. %s' % m.group(1)

    # Pre-clean
    if YearValidator(cleaned_val).valid:
        return cleaned_val


def get_interactive_input(value):
    if value in checked_manually:
        return checked_manually[value]
    new_value = input('Correct date: ')
    checked_manually[value] = new_value
    with codecs.open('checked_manually.txt', 'a', 'utf8') as f:
        f.write(value + '===' + new_value + '\n')
    return new_value


def pre_clean(val):
    # Pre-clean
    orig_val = val
    val = val.strip('.,' + string.whitespace)
    val = re.sub('<!--.*?-->', '', val)  # strip comments
    val = re.sub('&ndash;', '–', val)    # bruk unicode
    val = re.sub('&nbsp;', ' ', val)     # bruk vanlig mellomrom
    val = re.sub(r'\[\[([^\]]+?)\|([^\]]+?)\]\]', r'\1', val)    # strip wikilinks
    val = re.sub(r'\[\[([^|]+?)\]\]', r'\1', val)    # strip wikilinks
    val = re.sub(r'\{\{([^|}]+)\|([^}]+)\}\}', r'\2', val)    # strip simple templates
    val = re.sub(r',? kl\.\s?\d\d?[:.]\d\d([:.]\d\d)?$', '', val)  # fjern klokkeslett
    val = re.sub(r',? \d\d?[:.]\d\d (?:[A-Z]{1,4})?$', '', val)  # fjern klokkeslett, evt. med tidssone
    val = re.sub('[()\[\]]', '', val)
    val = val.strip('.,' + string.whitespace)

    if val != orig_val:
        logger.debug('Pre-cleaned "%s" as "%s"', orig_val, val)
    return val


def parseYear(y, base='auto'):
    if len(y) == 4:
        return y
    elif len(y) == 2:
        y = int(y)
        if base == 'auto':
            if y >= 20:
                return '19%s' % (y)
            if y < 20:
                return '20%s' % (y)
        else:
            return '%s%s' % (base, y)


def get_date_suggestion(val, interactive_mode=False):
    """
    Involving just one field/value
    """

    def suggest_date(val):

        # Year only
        m = re.match('^(\d{4})$', val)
        if m:
            return '%s' % (m.group(1))

        # Year range
        # 2004-2005 : whitespace, tankestrek/bindestrek
        # 2004-05 -> 2004-2005
        m = re.match('^(\d{4})\s?[-–]\s?(\d{2,4})$', val)
        if m:
            startYear = m.group(1)
            endYear = parseYear(m.group(2), startYear[:2])
            if endYear is not None:
                diff = int(endYear[2:]) - int(startYear[2:])
                if len(m.group(2)) == 4:
                    return '%s–%s' % (startYear, endYear)
                elif diff > 0 and diff < 10:
                    return '%s–%s' % (startYear, endYear)

        # ISO-format:
        # - Fjern opptil to omkringliggende ikke-alfanumeriske tegn (\W matcher alt bortsett fra letters, 0-9 og underscore)
        # - Korriger tankestrek -> bindestrek
        m = re.match('^\W{0,2}(\d{4})[-–](\d\d?)[-–](\d\d?)\W{0,2}$', val)
        if m:
            return '%s-%02d-%02d' % (m.group(1), int(m.group(2)), int(m.group(3)))

        # YYYY-MM:
        # - Fjern opptil to omkringliggende ikke-alfanumeriske tegn
        # - Korriger tankestrek -> bindestrek
        # - Endre til måned år
        m = re.match('^\W{0,2}(\d{4})[-–](\d\d?)\W{0,2}$', val)
        if m:
            try:
                return '%s %s' % (months[int(m.group(2)) - 1], m.group(1))
            except IndexError:
                pass

        # Norsk datoformat med to-sifret årstall (1.1.11 eller 01.01.11)
        m = re.match('^(\d\d?)\.(\d\d?)\.(\d{2})$', val)
        if m:
            year = parseYear(m.group(3))
            if year:
                if m.group(1).startswith('0') and len(m.group(2)) == 1:
                    # 05.5.2015 -> 5.5.2015
                    return '%s.%s.%s' % (m.group(1).lstrip('0'), m.group(2), year)
                if m.group(2).startswith('0') and len(m.group(1)) == 1:
                    # 5.05.2015 -> 5.5.2015
                    return '%s.%s.%s' % (m.group(1), m.group(2).lstrip('0'), year)
                return '%s.%s.%s' % (m.group(1), m.group(2), year)

        # 1/10-11 o.l.: Ikke 100 % entydig, men rimelig sannsynlig at d/m-yy på nowp
        m = re.match('^(\d\d?)\/(\d\d?)[- /]+(\d{2,4})$', val)
        if m:
            y = parseYear(m.group(3))
            if y:
                return '{}-{:02d}-{:02d}'.format(y, int(m.group(2)), int(m.group(1)))

        # 1. januar 2014 - 1. februar 2015
        m = re.match('^(\d\d?)[.,]?\s?([a-zA-Z]+) (\d{4})\s?[-–]\s?(\d\d?)[.,]?\s?([a-zA-Z]+) (\d{4})$', val)
        if m:
            day1 = m.group(1).lstrip('0')
            mnd1 = get_month(m.group(2).lower())
            day2 = m.group(4).lstrip('0')
            mnd2 = get_month(m.group(5).lower())
            if mnd1 is not None and mnd2 is not None:
                return '%s. %s %s – %s. %s %s' % (day1, mnd1, m.group(3), day2, mnd2, m.group(6))

        # 1. januar - 1. februar 2015
        m = re.match('^(\d\d?)[.,]?\s?([a-zA-Z]+)\s?[-–]\s?(\d\d?)[.,]?\s?([a-zA-Z]+) (\d{4})$', val)
        if m:
            day1 = m.group(1).lstrip('0')
            mnd1 = get_month(m.group(2).lower())
            day2 = m.group(3).lstrip('0')
            mnd2 = get_month(m.group(4).lower())
            if mnd1 is not None and mnd2 is not None:
                return '%s. %s – %s. %s %s' % (day1, mnd1, day2, mnd2, m.group(5))

        # 1.-2. februar 2015 (punctuation errors)
        m = re.match('^(\d\d?)[.,]?\s?[-–](\d\d?)[.,]?\s? ([a-zA-Z]+) (\d{4})$', val)
        if m:
            day1 = m.group(1).lstrip('0')
            day2 = m.group(2).lstrip('0')
            mnd = get_month(m.group(3).lower())
            if mnd is not None:
                return '%s.–%s. %s %s' % (day1, day2, mnd, m.group(4))

        # month/season year (January 2014, januar, 2014, høst 2014, [[januar 2014]], January 2014, ...) -> januar 2014
        m = re.match('^[^a-zA-Z0-9]{0,2}([a-zA-ZøåØÅ]+)[\., ]{1,2}(\d{4})[^a-zA-Z0-9]{0,2}$', val)
        if m:
            mnd = get_month_or_season(m.group(1).lower())
            if mnd is not None:
                return '%s %s' % (mnd, m.group(2))

        # month/season–month/season year (februar–mars 2010, vår–sommer 2012, Atumn–winter 2010)
        #  - Fix wrong separator (hyphen or /) as in "juni/juli" -> "juni-juli"
        m = re.match('^([a-zA-ZøåØÅ]+)\s?[-–/]\s?([a-zA-ZøåØÅ]+) (\d{4})$', val)
        if m:
            mnd1 = get_month_or_season(m.group(1).lower())
            mnd2 = get_month_or_season(m.group(2).lower())
            if mnd1 is not None and mnd2 is not None:
                return '%s–%s %s' % (mnd1, mnd2, m.group(3))

    def suggest_date_fuzzy(val):
        suggestions = []

        # 'ukjent', 'dato ukjent', 'ukjent dato', 'ukjent publiseringsdato', ...
        for m in re.finditer('[a-zA-Z()]*\s?(undated|unknown|ukjent|udatert|u\.å\.?|n\.d\.?)\s?[a-zA-Z()]*', val, flags=re.I):
            suggestions.append('udatert')

        # Norsk datoformat (1.1.2011 eller 01.01.2011)
        # - Use negative lookbehind and lookahead to ensure digits to not precede or follow
        # - Rett bindestrek -> punktum
        for m in re.finditer('(?<!\d)(\d\d?)[\s.-]+(\d\d?)[\s.-]+(\d{4})(?!\d)', val):
            if m.group(1).startswith('0') and len(m.group(2)) == 1:
                # 05.5.2015 -> 5.5.2015
                suggestions.append('%s.%s.%s' % (m.group(1).lstrip('0'), m.group(2), m.group(3)))
            if m.group(2).startswith('0') and len(m.group(1)) == 1:
                # 5.05.2015 -> 5.5.2015
                suggestions.append('%s.%s.%s' % (m.group(1), m.group(2).lstrip('0'), m.group(3)))
            else:
                suggestions.append('%s.%s.%s' % (m.group(1), m.group(2), m.group(3)))

        # January 1, 2014 -> 1. januar 2014
        # - [^\W\d_] matches unicode letters (\w minus digits and underscore)
        for m in re.finditer('([^\W\d_]{3,})\.?\s?(\d\d?),\s?(\d{4})', val, re.UNICODE):
            mnd = get_month(m.group(1).lower())
            day1 = m.group(2).lstrip('0')
            if mnd is not None:
                suggestions.append('%s. %s %s' % (day1, mnd, m.group(3)))

        # 2014, January 1 -> 1. januar 2014
        for m in re.finditer('(\d{4}),?\s?([^\W\d_]+)\s?(\d\d?)', val, re.UNICODE):
            mnd = get_month(m.group(2).lower())
            day1 = m.group(3).lstrip('0')
            if mnd is not None:
                suggestions.append('%s. %s %s' % (day1, mnd, m.group(1)))

        # Norsk datoformat (1. september 2014)
        # - Use negative lookbehind and lookahead to ensure digits to not precede or follow
        # - Punctuation errors: (1.januar2014, 1, januar 2014, 1 mars. 2010, 1 March 2010) -> 1. januar 2014
        # - Fikser månedsnavn med skrivefeil eller på engelsk eller svensk
        # - 10(th|st|rd)?( of)? -> 10.
        # p_word = '[^ ]*?'
        # p_word_delim = '[ :.,;]'
        # p_before = '^' + ('(?:%s%s)?' % (p_word, p_word_delim))   # match max one words
        # p_after = ('(?:%s%s)?' % (p_word_delim, p_word)) *2 + '$'  # match max two words
        pattern = '(?<!\d)(\d\d?)(?:th|st|rd|nd)?(?: of)?[\W]{0,3}([^\W\d_]{3,})(?: of)?[\W]{0,3}(\d{2}(?:\d{2})?)(?!\d)'
        for m in re.finditer(pattern, val, flags=re.IGNORECASE | re.UNICODE):
            day1 = m.group(1).lstrip('0')
            mnd = get_month(m.group(2))
            year = parseYear(m.group(3))
            if mnd is not None and year is not None:
                suggestions.append('%s. %s %s' % (day1, mnd, year))

        return suggestions

    cleaned_val = pre_clean(val)

    # Check if pre-cleaned date is valid
    if DateValidator(cleaned_val).valid:
        if cleaned_val == val:
            logger.debug('Date "%s" seems to be valid as-is', val)
        else:
            logger.info('Suggests to cleanup "%s" as "%s"', val, cleaned_val)

        return cleaned_val

    dt = suggest_date(cleaned_val)
    if dt is None:
        dts = suggest_date_fuzzy(cleaned_val)
        if len(dts) == 0:
            dt = get_year_suggestion(cleaned_val)
            if dt is None:
                logger.info('Found no date suggestion for "%s"', val)
                if interactive_mode:
                    dt = get_interactive_input(val)
                    if dt is None or dt == '':
                        return None
                else:
                    return None
        elif len(dts) != 1:
            logger.info('Indeterminate: Found more than one (%d) date suggestions for "%s": "%s"', len(dts), val, '", "'.join(dts))
            return None
        else:
            dt = dts[0]

    # Check that suggested date is actually valid
    dv = DateValidator(dt)
    if not dv.valid:
        logger.warning('Date "%s" produced invalid suggestion "%s": %s', val, dt, dv.problem)
        return None

    logger.info('Suggests to change "%s" to "%s"', val, dt)
    return dt


class Template:

    def __init__(self, tpl, interactive_mode):

        self.dato = []
        self.dag = []
        self.mnd = []
        self.aar = []
        self.tpl = tpl

        self.checked = 0
        self.modified = []
        self.unresolved = []

        for p in tpl.parameters:
            if p.key in ['dato', 'utgivelsesdato', 'date', 'laydate', 'arkivdato', 'archivedate', 'arkivdatum', 'besøksdato', 'accessdate', 'hämtdatum']:
                self.dato.append(p)
            if p.key in ['utgivelsesår', 'år', 'year']:
                self.aar.append(p)
            if p.key in ['måned', 'month']:
                self.mnd.append(p)
            if p.key in ['dag', 'day']:
                self.dag.append(p)

        for p in self.aar:

            self.checked += 1

            validator = YearValidator(p.value)

            if validator.valid:
                continue

            suggest = get_year_suggestion(p.value)
            if suggest:
                self.modified.append({'key': p.key, 'old': p.value, 'new': suggest, 'complex': False})
                p.value = suggest
                continue

            if not self.complex_replacements_year(p):
                self.unresolved.append({'key': p.key, 'value': p.value, 'problem': validator.problem})

        for p in self.dato:

            self.checked += 1

            validator = DateValidator(p.value)

            if validator.valid:
                continue

            suggest = get_date_suggestion(p.value, interactive_mode)
            if suggest:
                self.modified.append({'key': p.key, 'old': p.value, 'new': suggest, 'complex': False})
                p.value = suggest
                continue

            suggest2 = get_year_suggestion(p.value)
            if suggest2:
                self.modified.append({'key': p.key, 'old': p.value, 'new': suggest2, 'complex': False})
                p.value = suggest2
                continue

            if not self.complex_replacements(p):
                self.unresolved.append({'key': p.key, 'value': p.value, 'problem': validator.problem})

    def complex_replacements(self, p):
        """
        Check if the combination of a {date} field and a {year} field is a valid date

        Returns: True if a replacement has been made, False otherwise
        """

        if p.key in ['dato', 'date'] and len(self.aar) == 1:
            # If the combination "{date} {year}" is a valid date, replace
            # the {date} field with "{date} {year}" and clear the {year} field.
            combined_value = p.value + ' ' + self.aar[0].value

            suggest = get_date_suggestion(combined_value, False)
            if suggest:
                logger.info('%s:"%s" can be changed to "%s" and %s removed', p.key, p.value, suggest, self.aar[0].key)
                self.modified.append({'key': p.key, 'old': p.value, 'new': suggest, 'complex': True})
                p.value = suggest
                del self.tpl.parameters[self.aar[0].key]
                return True

            return False

    def complex_replacements_year(self, p):
        """
        Check if {year} field value should be moved to a {date} field

        Returns: True if a replacement has been made, False otherwise
        """

        date_fields = [x for x in self.dato if x.key in ['dato', 'utgivelsesdato', 'date'] and x.value != '']
        if len(date_fields) != 0:
            # There is already a date field
            return False

        suggest = None
        if DateValidator(p.value).valid:
            # The value is not a valid year field value, but is a valid date field value
            suggest = p.value
        else:
            suggest2 = get_date_suggestion(p.value)
            if suggest2:
                suggest = suggest2

        if suggest is None:
            return False

        # Add the value to either the {date} field if English template or {dato} otherwise
        param = 'date' if p.key == 'year' else 'dato'
        self.modified.append({'key': param, 'old': p.value, 'new': suggest, 'complex': True})
        self.tpl.parameters[param] = suggest

        # Remove the original {year} field
        del self.tpl.parameters[p.key]

        return True


class Page:

    def format_entry(self, s):
        return "Endret '%(key)s' fra '%(old)s' til '%(new)s'" % s

    def __init__(self, page, interactive_mode):

        logger.info('Checking page: %s', page.name)

        self.checked = 0
        self.modified = []
        self.unresolved = []

        # te = page.text()
        txt = page.text()

        # Due to <https://github.com/danmichaelo/mwtemplates/issues/3>
        if re.search('<nowiki ?/>', txt, re.I) is not None:
            return

        te = TemplateEditor(txt)

        modified = False
        for k, v in te.templates.iteritems():
            if k in ['Kilde www', 'Kilde bok', 'Kilde artikkel', 'Kilde avhandling', 'Kilde avis', 'Cite web', 'Citeweb', 'Cite news', 'Cite journal', 'Cite book', 'Tidningsref', 'Webbref', 'Bokref']:
                for tpl in v:
                    t = Template(tpl, interactive_mode)
                    self.checked += t.checked
                    self.modified.extend(t.modified)
                    self.unresolved.extend(t.unresolved)

        for u in self.unresolved:
            u['page'] = page.name

        if len(self.modified) != 0:
            if len(self.modified) == 1:
                summary = 'CS1-kompatible datoer: %s' % (self.format_entry(self.modified[0]))
            elif len(self.modified) == 2:
                summary = 'CS1-kompatible datoer: %s, %s' % (self.format_entry(self.modified[0]), self.format_entry(self.modified[1]))
            else:
                summary = 'CS1-kompatible datoer: Fikset %d datoer' % (len(self.modified))

            logger.info('Saving %d fixed date(s)', len(self.modified))
            time.sleep(1)

            try:
                res = page.save(te.wikitext(), summary=summary)
            except mwclient.errors.ProtectedPageError:
                logger.error('ERROR: Page protected, could not save')

            if res.get('newrevid') is not None:
                with codecs.open('modified.txt', 'a', 'utf8') as f:
                    for x in self.modified:
                        ti = quote(page.name.replace(' ', '_').encode('utf8'))
                        difflink = '//no.wikipedia.org/w/index.php?title=%s&diff=%s&oldid=%s' % (ti, res['newrevid'], res['oldrevid'])
                        f.write('| [[%s]] ([%s diff]) || Endret %s fra %s til %s || %s\n|-\n' % (page.name, difflink, x['key'], x['old'], x['new'], 'kompleks' if x['complex'] else ''))

                with codecs.open('modified-simple.txt', 'a', 'utf8') as f:
                    for x in self.modified:
                        ti = quote(page.name.replace(' ', '_').encode('utf8'))
                        f.write('%s\t%s\t%s\n' % (page.name, x['old'], x['new']))


def main():

    parser = argparse.ArgumentParser(description='CS1 cleanup')
    parser.add_argument('--page', required=False, help='Name of a single page to check')
    parser.add_argument('--interactive_mode', default=False, action='store_true', help='Interactive mode')
    args = parser.parse_args()

    cnt = {'pagesChecked': 0, 'datesChecked': 0, 'datesModified': 0, 'datesUnresolved': 0}
    pagesWithNoKnownErrors = []
    unresolved = []

    config = json.load(open('config.json', 'r'))

    site = Site('no.wikipedia.org', **config)
    cat = site.Categories['Sider med kildemaler som inneholder datofeil']

    if args.page:
        page = site.pages[args.page]
        p = Page(page, args.interactive_mode)

    else:
        n = 0
        for page in cat.members(namespace=0):
            n += 1
            # logging.info('%02d %s - %.1f MB', n, page.name, memory_usage_psutil())
            # print "-----------[ %s ]-----------" % page.name
            p = Page(page, args.interactive_mode)
            cnt['pagesChecked'] += 1
            cnt['datesChecked'] += p.checked
            cnt['datesModified'] += len(p.modified)
            cnt['datesUnresolved'] += len(p.unresolved)

            if len(p.modified) == 0 and len(p.unresolved) == 0:
                pagesWithNoKnownErrors.append(page.name)
                # print(page.name)

            unresolved.extend(p.unresolved)

            # if cnt['pagesChecked'] > 100:
            #     break

    # print
    # print "Pages with no known templates with date errors:"
    # for p in pagesWithNoKnownErrors:
    #     print ' - %s' % p

    cnt['datesOk'] = cnt['datesChecked'] - cnt['datesModified'] - cnt['datesUnresolved']

    cnt['now'] = datetime.now().strftime('%F %T')

    unresolvedTxt = u"Siste kjøring: %(now)s. Sjekket %(pagesChecked)d hovednavneromssider i [[:Kategori:Sider med kildemaler som inneholder datofeil]]. Fant %(datesChecked)d datofelt, hvorav " % cnt
    unresolvedTxt += u"%(datesOk)d var i tråd med CS1, %(datesModified)d ble korrigert og %(datesUnresolved)d kunne ikke korrigeres automatisk. Feltene som ikke kunne korrigeres automatisk er listet opp i tabellen under." % cnt
    unresolvedTxt += u'\n\n{|class="wikitable sortable"\n! Artikkel !! Felt !! Verdi !! Problem \n|-\n'

    for p in unresolved:
        if p.get('problem') is None:
            p['problem'] = 'Ikke entydig/forståelig'
        unresolvedTxt += u'| [[%(page)s]] || %(key)s || <nowiki>%(value)s</nowiki> || %(problem)s\n|-\n' % p

    page = site.pages[u'Bruker:DanmicholoBot/Datofiks/Uløst']
    page.save(unresolvedTxt, summary='Oppdaterer')


if __name__ == '__main__':
    main()
