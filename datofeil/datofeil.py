# encoding=utf8
from __future__ import unicode_literals

import os
import psutil
import sys
import re
import sys
import time
import argparse
import codecs
import json
import urllib2

from mwclient import Site
from mwtemplates import TemplateEditor

from .correct import correct

import logging


def memory_usage_psutil():
    # return the memory usage in MB
    process = psutil.Process(os.getpid())
    mem = process.get_memory_info()[0] / float(2 ** 20)
    return mem

logger = logging.getLogger('datofeil')

months = ['januar', 'februar', 'mars', 'april', 'mai', 'juni', 'juli', 'august', 'september', 'oktober', 'november', 'desember']
seasons = ['våren', 'sommeren', 'høsten', 'vinteren']
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
}


def is_valid_month(name):
    return name in months


def is_valid_month_or_season(name):
    name = name[0].lower() + name[1:]  # ignore case on first character
    return name in months or name in seasons


def get_month(val):
    val = val.lower()
    if is_valid_month(val):
        return val
    elif val in monthsdict:
        return monthsdict[val]
    else:
        suggest = correct(val)
        if suggest != val:
            return suggest
    return None


def get_month_or_season(val):
    val = val.lower()
    if is_valid_month_or_season(val):
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


def is_valid_year(val):
    val = val.strip()

    if re.match('^$', val):
        # print 'Warning: empty year found'
        return True  # empty

    # 2014
    if re.match('^\d{4}$', val):
        return True

    if re.match('^ca?\. \d{4}$', val):
        return True


def get_year_suggestion(val):

    # Pre-clean
    val = val.strip()
    val = re.sub('<!--.*?-->', '', val)  # strip comments
    val = val.strip()
    if is_valid_year(val):
        return val

    # [[2011]]
    m = re.match('^\[\[(\d{4})\]\]$', val)
    if m:
        return m.group(1)

    # Ca. 2011
    m = re.match('^ca. (\d{4})$', val, flags=re.I)
    if m:
        return 'ca. %s' % m.group(1)


def is_valid_date(val):

    val = val.strip()

    if re.match('^$', val):
        # print 'Warning: empty date found'
        return True  # empty

    if re.match('^udatert$', val):
        return True

    if re.match('^u\.d\.$', val):
        return True

    # 2014-01-01
    if re.match('^\d{4}-\d{2}-\d{2}$', val):
        return True

    # 2014
    if re.match('^\d{4}$', val):
        return True

    # 2014–2015
    if re.match('^\d{4}–\d{4}$', val):
        return True

    # 1.1.2001
    if re.match('^\d\d?\.\d\d?\.\d{4}$', val):
        return True

    # 1. januar 2014
    m = re.match('^(\d\d?)\. ([a-z]+) (\d{4})$', val)
    if m and is_valid_month(m.group(2)):
        return True

    # 1.–2. januar 2014
    m = re.match('^(\d\d?)\.–(\d\d?)\. ([a-z]+) (\d{4})$', val)
    if m and is_valid_month(m.group(3)):
        return True

    # 1. januar – 2. februar 2014
    m = re.match('^(\d\d?)\. ([a-z]+) – (\d\d?)\. ([a-z]+) (\d{4})$', val)
    if m and is_valid_month(m.group(2)) and is_valid_month(m.group(4)):
        return True

    # 1. januar 2014 – 1. februar 2015
    m = re.match('^(\d\d?)\. ([a-z]+) (\d{4}) – (\d\d?)\. ([a-z]+) (\d{4})$', val)
    if m and is_valid_month(m.group(2)) and is_valid_month(m.group(5)):
        return True

    # januar 2014
    m = re.match('^([A-Za-zøå]+) (\d{4})$', val)
    if m and is_valid_month_or_season(m.group(1)):
        return True

    # januar–februar 2014
    m = re.match('^([A-Za-zøå]+)–([a-z]+) (\d{4})$', val)
    if m and is_valid_month_or_season(m.group(1)) and is_valid_month_or_season(m.group(2)):
        return True

    # januar 2014 – februar 2015
    m = re.match('^([A-Za-zøå]+) (\d{4}) – ([a-zøå]+) (\d{4})$', val)
    if m and is_valid_month_or_season(m.group(1)) and is_valid_month_or_season(m.group(3)):
        return True

    return False


def pre_clean(val):
    # Pre-clean
    val = re.sub('<!--.*?-->', '', val)  # strip comments
    val = re.sub('&ndash;', '–', val)    # bruk unicode
    val = re.sub('&nbsp;', ' ', val)     # bruk vanlig mellomrom
    val = re.sub(r',? kl\.\s?\d\d?[:.]\d\d([:.]\d\d)?$', '', val)  # fjern klokkeslett
    val = re.sub(r',? \d\d?:\d\d$', '', val)  # fjern klokkeslett
    val = re.sub(r'\[\[[^\]]+?\|([^\]]+?)\]\]', r'\1', val)    # strip wikilinks
    val = re.sub(r'\[\[([^|]+?)\]\]', r'\1', val)    # strip wikilinks
    val = val.strip()
    return val


def parseYear(y, base='auto'):
    if len(y) == 4:
        return y
    elif len(y) == 2:
        y = int(y)
        if base == 'auto':
            if y >= 20:
                return '19%s' % (y)
            if y <= 14:
                return '20%s' % (y)
        else:
            return '%s%s' % (base, y)


def get_date_suggestion(val):
    """
    Involving just one field/value
    """

    val = pre_clean(val)
    if is_valid_date(val):
        return val

    # 'ukjent', 'dato ukjent', 'ukjent dato', 'ukjent publiseringsdato', ...
    m = re.match('^[a-zA-Z]*\s?(ukjent|udatert|u\.å\.?|n\.d\.?)\s?[a-zA-Z]*$', val, flags=re.I)
    if m:
        return 'udatert'

    # Year only
    # - Remove linking
    m = re.match('^\[{0,2}(\d{4})\]{0,2}$', val)
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
    # - Fjern opptil to omkringliggende ikke-alfanumeriske tegn
    # - Korriger tankestrek -> bindestrek
    m = re.match('^[^a-zA-Z0-9]{0,2}(\d{4})[-–](\d\d?)[-–](\d\d?)[^a-zA-Z0-9]{0,2}$', val)
    if m:
        return '%s-%02d-%02d' % (m.group(1), int(m.group(2)), int(m.group(3)))

    # YYYY-MM:
    # - Fjern opptil to omkringliggende ikke-alfanumeriske tegn
    # - Korriger tankestrek -> bindestrek
    # - Endre til måned år
    m = re.match('^[^a-zA-Z0-9]{0,2}(\d{4})[-–](\d\d?)[^a-zA-Z0-9]{0,2}$', val)
    if m:
        try:
            return '%s %s' % (months[int(m.group(2)) - 1], m.group(1))
        except IndexError:
            pass

    # Norsk datoformat (1.1.2011)
    # - Fjern opptil to omkringliggende ikke-alfanumeriske tegn
    # - Rett bindestrek -> punktum
    m = re.match('^[^a-zA-Z0-9]{0,2}(\d\d?)[.-](\d\d?)[.-](\d{4})[^a-zA-Z0-9]{0,2}$', val)
    if m:
        return '%s.%s.%s' % (m.group(1), m.group(2), m.group(3))

    # Norsk datoformat med to-sifret årstall (1.1.11)
    m = re.match('^(\d\d?\.\d\d?)\.(\d{2})$', val)
    if m:
        y = parseYear(m.group(2))
        if y:
            return '%s.%s' % (m.group(1), y)

    # Norsk datoformat (1. september 2014)
    # - Fjern opptil to omkringliggende ikke-alfanumeriske tegn
    # - Punctuation errors: (1.januar 2014, 1, januar 2014, 1 mars. 2010) -> 1. januar 2014
    # - Fikser månedsnavn med skrivefeil eller på engelsk eller svensk
    # - 10(th|st|rd)?( of)? -> 10.
    m = re.match('^[^a-zA-Z0-9]{0,2}(\d\d?)(?:th|st|rd)?(?: of)?[^a-zA-Z0-9]{0,3}([a-zA-Z]+)[^a-zA-Z0-9]{0,3}(\d{4})[^a-zA-Z0-9]{0,2}$', val)
    if m:
        mnd = get_month(m.group(2).lower())
        if mnd is not None:
            return '%s. %s %s' % (m.group(1), mnd, m.group(3))

    # 1. januar 2014 - 1. februar 2015
    m = re.match('^(\d\d?)[.,]?\s?([a-zA-Z]+) (\d{4})\s?[-–]\s?(\d\d?)[.,]?\s?([a-zA-Z]+) (\d{4})$', val)
    if m:
        mnd1 = get_month(m.group(2).lower())
        mnd2 = get_month(m.group(5).lower())
        if mnd1 is not None and mnd2 is not None:
            return '%s. %s %s – %s. %s %s' % (m.group(1), mnd1, m.group(3), m.group(4), mnd2, m.group(6))

    # 1. januar - 1. februar 2015
    m = re.match('^(\d\d?)[.,]?\s?([a-zA-Z]+)\s?[-–]\s?(\d\d?)[.,]?\s?([a-zA-Z]+) (\d{4})$', val)
    if m:
        mnd1 = get_month(m.group(2).lower())
        mnd2 = get_month(m.group(4).lower())
        if mnd1 is not None and mnd2 is not None:
            return '%s. %s – %s. %s %s' % (m.group(1), mnd1, m.group(3), mnd2, m.group(5))

    # 1.-2. februar 2015 (punctuation errors)
    m = re.match('^(\d\d?)[.,]?\s?[-–](\d\d?)[.,]?\s? ([a-zA-Z]+) (\d{4})$', val)
    if m:
        mnd = get_month(m.group(3).lower())
        if mnd is not None:
            return '%s.–%s. %s %s' % (m.group(1), m.group(2), mnd, m.group(4))

    # month/season year (January 2014, januar, 2014, høst 2014, [[januar 2014]], January 2014, ...) -> januar 2014
    m = re.match('^[^a-zA-Z0-9]{0,2}([a-zA-ZøåØÅ]+)[\., ]{1,2}(\d{4})[^a-zA-Z0-9]{0,2}$', val)
    if m:
        mnd = get_month_or_season(m.group(1).lower())
        if mnd is not None:
            return '%s %s' % (mnd, m.group(2))

    # month/season–month/season year (februar–mars 2010, vår–sommer 2012, Atumn–winter 2010)
    m = re.match('^([a-zA-ZøåØÅ]+)\s?[-–]\s?([a-zA-ZøåØÅ]+) (\d{4})$', val)
    if m:
        mnd1 = get_month_or_season(m.group(1).lower())
        mnd2 = get_month_or_season(m.group(2).lower())
        if mnd1 is not None and mnd2 is not None:
            return '%s–%s %s' % (mnd1, mnd2, m.group(3))

    # January 1, 2014 -> 1. januar 2014
    m = re.match('^([a-zA-Z]+) (\d\d?), (\d{4})$', val)
    if m:
        mnd = get_month(m.group(1).lower())
        if mnd is not None:
            return '%s. %s %s' % (m.group(2), mnd, m.group(3))

    return None


class Template:

    def __init__(self, tpl):

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

            if is_valid_year(p.value):
                continue

            suggest = get_year_suggestion(p.value)
            if suggest:
                self.modified.append({'key': p.key, 'old': p.value, 'new': suggest, 'complex': False})
                p.value = suggest
                continue

            if not self.complex_replacements_year(p):
                self.unresolved.append({'key': p.key, 'value': p.value})

        for p in self.dato:

            self.checked += 1

            if is_valid_date(p.value):
                continue

            suggest = get_date_suggestion(p.value)
            if suggest:
                self.modified.append({'key': p.key, 'old': p.value, 'new': suggest, 'complex': False})
                p.value = suggest
                continue

            suggest2 = get_year_suggestion(p.value)
            logger.info(suggest2)
            if suggest2:
                self.modified.append({'key': p.key, 'old': p.value, 'new': suggest2, 'complex': False})
                p.value = suggest2
                continue

            if not self.complex_replacements(p):
                self.unresolved.append({'key': p.key, 'value': p.value})

    def complex_replacements(self, p):
        """
        Replacements involving more than one field/value

        Returns: True if a replacement has been made, False otherwise
        """

        if p.key in ['dato', 'date']:
            # 14. mai
            m = re.match('^(\d\d?)[.,]\s?([a-zA-Z]+)$', p.value)
            if m:
                mnd = get_month(m.group(2))
                if mnd is not None and len(self.aar) == 1:
                    m2 = re.match('^\[{0,2}(\d{4})\]{0,2}$', self.aar[0].value)
                    if m2:
                        suggest = '%s. %s %s' % (m.group(1), mnd, m2.group(1))
                        self.modified.append({'key': p.key, 'old': p.value, 'new': suggest, 'complex': True})
                        p.value = suggest
                        del self.tpl.parameters[self.aar[0].key]
                        return True

        return False

    def complex_replacements_year(self, p):
        """
        Replacements involving more than one field/value

        Returns: True if a replacement has been made, False otherwise
        """

        q = [x for x in self.dato if x.key in ['dato', 'utgivelsesdato', 'date'] and x.value != '']
        if len(q) != 0:
            return False

        suggest = None
        if is_valid_date(p.value):
            suggest = p.value
        else:
            suggest2 = get_date_suggestion(p.value)
            if suggest2:
                suggest = suggest2

        if suggest is None:
            return False

        param = 'date' if p.key == 'year' else 'dato'
        self.modified.append({'key': param, 'old': p.value, 'new': suggest, 'complex': True})
        self.tpl.parameters[param] = suggest
        del self.tpl.parameters[p.key]
        return True


class Page:

    def format_entry(self, s):
        return '%(key)s : %(old)s → %(new)s' % s

    def __init__(self, page):

        self.checked = 0
        self.modified = []
        self.unresolved = []

        # te = page.text()
        te = TemplateEditor(page.text())

        modified = False
        for k, v in te.templates.iteritems():
            if k in ['Kilde www', 'Kilde bok', 'Kilde artikkel', 'Kilde avhandling', 'Cite web', 'Citeweb', 'Cite news', 'Cite journal', 'Cite book', 'Tidningsref', 'Webbref', 'Bokref']:
                for tpl in v:
                    pass
                    t = Template(tpl)
                    self.checked += t.checked
                    self.modified.extend(t.modified)
                    self.unresolved.extend(t.unresolved)

        for u in self.unresolved:
            u['page'] = page.name

        if len(self.modified) != 0:
            if len(self.modified) == 1:
                summary = '[Datofiks] %s' % (self.format_entry(self.modified[0]))
            elif len(self.modified) == 2:
                summary = '[Datofiks] %s, %s' % (self.format_entry(self.modified[0]), self.format_entry(self.modified[1]))
            else:
                summary = '[Datofiks] Fikset %d datoer' % (len(self.modified))

            logger.info('%s: %d modified : %s', page.name, len(self.modified), summary)
            time.sleep(3)

            try:
                res = page.save(te.wikitext(), summary=summary)
            except mwclient.errors.ProtectedPageError:
                logger.error('ERROR: Page protected, could not save')

            f = codecs.open('modified.txt', 'a', 'utf8')
            for x in self.modified:
                ti = urllib2.quote(page.name.replace(' ', '_').encode('utf8'))
                difflink = '//no.wikipedia.org/w/index.php?title=%s&diff=%s&oldid=%s' % (ti, res['newrevid'], res['oldrevid'])
                f.write('| [[%s]] ([%s diff]) || %s: %s → %s || %s\n|-\n' % (page.name, difflink, x['key'], x['old'], x['new'], 'kompleks' if x['complex'] else ''))
            f.close()


def main():

    parser = argparse.ArgumentParser(description='Datofeilfikser')
    parser.add_argument('--page', required=False, help='Name of a single page to check')
    args = parser.parse_args()

    cnt = {'pagesChecked': 0, 'datesChecked': 0, 'datesModified': 0, 'datesUnresolved': 0}
    pagesWithNoKnownErrors = []
    unresolved = []

    config = json.load(open('config.json', 'r'))

    site = Site('no.wikipedia.org')
    site.login(config['username'], config['password'])
    cat = site.Categories['Sider med kildemaler som inneholder datofeil']

    if args.page:
        page = site.pages[args.page]
        p = Page(page)

    else:
        n = 0
        for page in cat.members():
            n += 1
            logging.info('%02d %s - %.1f MB', n, page.name, memory_usage_psutil())
            # print "-----------[ %s ]-----------" % page.name
            p = Page(page)
            cnt['pagesChecked'] += 1
            cnt['datesChecked'] += p.checked
            cnt['datesModified'] += len(p.modified)
            cnt['datesUnresolved'] += len(p.unresolved)

            if len(p.modified) == 0 and len(p.unresolved) == 0:
                pagesWithNoKnownErrors.append(page.name)

            unresolved.extend(p.unresolved)

            # if cnt['pagesChecked'] > 100:
            #     break

    # print
    # print "Pages with no known templates with date errors:"
    # for p in pagesWithNoKnownErrors:
    #     print ' - %s' % p

    cnt['datesOk'] = cnt['datesChecked'] - cnt['datesModified'] - cnt['datesUnresolved']

    unresolvedTxt = u"Pages checked: %(pagesChecked)d, dates checked: %(datesChecked)d, of which<br>\n" % cnt
    unresolvedTxt += "  OK: %(datesOk)d, modified: %(datesModified)d, unresolved errors: %(datesUnresolved)d\n\n" % cnt
    unresolvedTxt += u'Unresolved errors:\n\n{|class="wikitable sortable"\n! Artikkel !! Felt !! Verdi\n|-\n'

    for p in unresolved:
        unresolvedTxt += u'| [[%(page)s]] || %(key)s || <nowiki>%(value)s</nowiki>\n|-\n' % p

    page = site.pages[u'Bruker:DanmicholoBot/Datofiks/Uløst']
    page.save(unresolvedTxt, summary='Oppdaterer')


if __name__ == '__main__':
    main()
