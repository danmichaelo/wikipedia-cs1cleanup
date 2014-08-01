# encoding=utf8
from __future__ import unicode_literals

import re
import sys
import time
import argparse
import codecs
import simplejson as json
import urllib2

from mwclient import Site
from mwtemplates import TemplateEditor

from .correct import correct

months = ['januar', 'februar', 'mars', 'april', 'mai', 'juni', 'juli', 'august', 'september', 'oktober', 'november', 'desember']
seasons = ['vår', 'sommer', 'høst', 'vinter']
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
}
seasonsdict = {
    'spring': 'vår',
    'summer': 'sommer',
    'autumn': 'høst',
    'winter': 'vinter',
}


def is_valid_month(name):
    return name in months


def is_valid_month_or_season(name):
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


def is_valid_date(val):

    val = val.strip()

    if re.match('^$', val):
        # print 'Warning: empty date found'
        return True  # empty

    # 2014-01-01
    if re.match('^\d{4}-\d{2}-\d{2}$', val):
        return True

    # 2014
    if re.match('^\d{4}$', val):
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
    m = re.match('^([a-z]+) (\d{4})$', val)
    if m and is_valid_month_or_season(m.group(1)):
        return True

    # januar–februar 2014
    m = re.match('^([a-z]+)–([a-z]+) (\d{4})$', val)
    if m and is_valid_month_or_season(m.group(1)) and is_valid_month_or_season(m.group(2)):
        return True

    # januar 2014 – februar 2015
    m = re.match('^([a-z]+) (\d{4}) – ([a-z]+) (\d{4})$', val)
    if m and is_valid_month_or_season(m.group(1)) and is_valid_month_or_season(m.group(3)):
        return True

    return False


def get_date_suggestion(val):
    """
    Involving just one field/value
    """

    # Pre-clean
    val = re.sub('<!--.*?-->', '', val)  # strip comments
    val = re.sub('&ndash;', '–', val)    # bruk unicode
    val = re.sub(',? kl\.\s?\d\d?[:.]\d\d([:.]\d\d)?$', '', val)  # fjern klokkeslett
    val = re.sub(r'\[\[.+?\|(.+?)\]\]', r'\1', val)    # strip wikilinks
    val = re.sub(r'\[\[([^|]+?)\]\]', r'\1', val)    # strip wikilinks
    val = val.strip()

    if is_valid_date(val):
        return val

    # Kun årstall
    # - Fjern lenking
    m = re.match('^\[{0,2}(\d{4})\]{0,2}$', val)
    if m:
        return '%s' % (m.group(1))

    # ISO-format:
    # - Fjern lenking og rett tankestrek -> bindestrek
    m = re.match('^\[{0,2}(\d{4})[-–](\d\d?)[-–](\d\d?)\]{0,2}$', val)
    if m:
        return '%s-%02d-%02d' % (m.group(1), int(m.group(2)), int(m.group(3)))

    # Norsk datoformat (1.1.2011)
    # - Fjern lenking og rett bindestrek -> punktum
    m = re.match('^\[{0,2}(\d\d?)[.-](\d\d?)[.-](\d{4})\]{0,2}$', val)
    if m:
        return '%s.%s.%s' % (m.group(1), m.group(2), m.group(3))

    # Norsk datoformat med to-sifret årstall (1.1.11)
    m = re.match('^(\d\d?\.\d\d?)\.(\d{2})$', val)
    if m:
        y = int(m.group(2))
        if y >= 20:
            return '%s.19%s' % (m.group(1), m.group(2))
        if y <= 14:
            return '%s.20%s' % (m.group(1), m.group(2))

    # Norsk datoformat (1. september 2014)
    # - Punctuation errors: (1.januar 2014, 1, januar 2014, 1 mars. 2010) -> 1. januar 2014
    # - Avlenking: [[1. januar]] [[2014]] -> 1. januar 2014
    # - Fikser månedsnavn med skrivefeil eller på engelsk eller svensk
    m = re.match('^[^a-zA-Z0-9]{0,2}(\d\d?)[\., ]{1,2}([a-zA-Z]+)\]{0,2}[\., ]{1,2}\[{0,2}(\d{4})[^a-zA-Z0-9]{0,2}$', val)
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

    # month/season year (January 2014, januar, 2014, [[januar 2014]], January 2014, ...) -> januar 2014
    m = re.match('^[^a-zA-Z0-9]{0,2}([a-zA-Z]+)[\., ]{1,2}(\d{4})[^a-zA-Z0-9]{0,2}$', val)
    if m:
        mnd = get_month_or_season(m.group(1).lower())
        if mnd is not None:
            return '%s %s' % (mnd, m.group(2))

    # month/season–month/season year (februar–mars 2010, vår–sommer 2012, Atumn–winter 2010)
    m = re.match('^([a-zA-Z]+)\s?[-–]\s?([a-zA-Z]+) (\d{4})$', val)
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
            if p.key in ['dato', 'besøksdato', 'arkivdato', 'utgivelsesdato', 'date', 'accessdate', 'archivedate', 'laydate', 'hämtdatum', 'arkivdatum']:
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

            self.unresolved.append('%s=%s' % (p.key, p.value))

        for p in self.dato:

            self.checked += 1

            if is_valid_date(p.value):
                continue

            suggest = get_date_suggestion(p.value)
            if suggest:
                self.modified.append({'key': p.key, 'old': p.value, 'new': suggest, 'complex': False})
                p.value = suggest
                continue

            if not self.complex_replacements(p):
                self.unresolved.append('%s=%s' % (p.key, p.value))

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


class Page:

    def format_entry(self, s):
        return '%(key)s : %(old)s → %(new)s' % s

    def __init__(self, page):

        self.checked = 0
        self.modified = []
        self.unresolved = []

        te = TemplateEditor(page.edit())
        modified = False
        for k, v in te.templates.items():
            if k in ['Kilde www', 'Kilde bok', 'Kilde artikkel', 'Kilde avhandling', 'Cite web', 'Citeweb', 'Cite news', 'Cite journal', 'Cite book', 'Tidningsref', 'Webbref', 'Bokref']:
                for tpl in v:
                    t = Template(tpl)
                    self.checked += t.checked
                    self.modified.extend(t.modified)
                    self.unresolved.extend(t.unresolved)

        if len(self.modified) != 0:
            if len(self.modified) == 1:
                summary = '[Datofiks] %s' % (self.format_entry(self.modified[0]))
            elif len(self.modified) == 2:
                summary = '[Datofiks] %s, %s' % (self.format_entry(self.modified[0]), self.format_entry(self.modified[1]))
            else:
                summary = '[Datofiks] Fikset %d datoer' % (len(self.modified))

            print
            print '%s: %d modified' % (page.name, len(self.modified))
            print summary

            time.sleep(3)

            res = page.save(te.wikitext(), summary=summary)

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
        for page in cat.members():
            # print "-----------[ %s ]-----------" % page.name
            p = Page(page)
            cnt['pagesChecked'] += 1
            cnt['datesChecked'] += p.checked
            cnt['datesModified'] += len(p.modified)
            cnt['datesUnresolved'] += len(p.unresolved)

            if len(p.modified) == 0 and len(p.unresolved) == 0:
                pagesWithNoKnownErrors.append(page.name)

            unresolved.extend(p.unresolved)

            # if cnt['pagesChecked'] > 400:
            #    break

    print
    print "Pages with no known templates with date errors:"
    for p in pagesWithNoKnownErrors:
        print ' - %s' % p

    print
    print "Unresolved date errors:"
    for p in unresolved:
        print ' - %s' % p

    cnt['datesOk'] = cnt['datesChecked'] - cnt['datesModified'] - cnt['datesUnresolved']
    print
    print "Pages checked: %(pagesChecked)d, dates checked: %(datesChecked)d, of which" % cnt
    print "  OK: %(datesOk)d, modified: %(datesModified)d, unresolved errors: %(datesUnresolved)d" % cnt

if __name__ == '__main__':
    main()
