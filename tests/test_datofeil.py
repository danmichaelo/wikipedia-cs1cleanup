# encoding=utf8
from __future__ import unicode_literals
import unittest

from datofeil import is_valid_date, get_date_suggestion, is_valid_year, get_year_suggestion, pre_clean


class TestPreprocessor(unittest.TestCase):

    def setUp(self):
        pass

    def test_isodate(self):
        self.assertTrue(is_valid_date('2014-01-30'))

    def test_std_date(self):
        self.assertTrue(is_valid_date('1. januar 2014'))

    def test_date_range(self):
        self.assertTrue(is_valid_date('1. januar 2014 – 1. februar 2015'))  # tankestrek
        self.assertFalse(is_valid_date('1. januar 2014 - 1. februar 2015'))  # bindestrek
        self.assertTrue(is_valid_date('21.–26. april 2002'))  # tankestrek
        self.assertFalse(is_valid_date('21.-26. april 2002'))  # bindestrek
        self.assertTrue(is_valid_date('januar 2014 – februar 2015'))
        self.assertFalse(is_valid_date('januar 2014–februar 2015'))
        self.assertTrue(is_valid_date('januar–februar 2014'))
        self.assertFalse(is_valid_date('januar – februar 2014–februar'))
        self.assertTrue(is_valid_date('28. februar – 6. mars 2005'))
        self.assertTrue(is_valid_date('1942–1991'))

    def test_pre_clean(self):
        self.assertEqual('2006-10-01', pre_clean('[[2006]]-[[1. oktober|10-01]]'))

    def test_date_suggestions(self):
        self.assertEqual('09.04.2008', get_date_suggestion('[[09.04.2008]]'))
        self.assertEqual('09.04.2008', get_date_suggestion('[[09-04-2008]]'))
        self.assertEqual('2006-10-21', get_date_suggestion('[[2006-10-21]]'))
        self.assertEqual('2006-10-01', get_date_suggestion('[[2006]]-[[1. oktober|10-01]]'))
        self.assertEqual('24. oktober 2007', get_date_suggestion('[[24. oktober]] 2007'))
        self.assertEqual('1. januar 2014', get_date_suggestion('[[1. januar]] [[2014]]'))
        self.assertEqual('1. januar 2014', get_date_suggestion('[[1. januar]], [[2014]]'))
        self.assertEqual('30. november 2010', get_date_suggestion('30. november 2010 kl. 14:12'))
        self.assertEqual('30. november 2010', get_date_suggestion('30. november 2010 14:12'))
        self.assertEqual('30. november 2010', get_date_suggestion('30,november 2010'))
        self.assertEqual('30. november 2010', get_date_suggestion('30.novembir 2010'))
        self.assertEqual('30. november 2010', get_date_suggestion('[[30 november 2010]]'))
        self.assertEqual('23. oktober 1999 – 19. februar 2000', get_date_suggestion('23. oktober 1999 - 19. februar 2000'))
        self.assertEqual('27. september – 4. oktober 2000', get_date_suggestion('27. september–4. oktober 2000'))
        self.assertEqual('21.–26. april 2002', get_date_suggestion('21.-26. april 2002'))  # bindestrek
        self.assertEqual('januar–februar 2002', get_date_suggestion('januar - februar 2002'))  # punctuation
        self.assertEqual('mai 2012', get_date_suggestion('Mai 2012'))
        self.assertEqual('mai 2012', get_date_suggestion('Mail 2012'))
        self.assertEqual('høsten 2012', get_date_suggestion('høst 2012'))
        self.assertEqual('våren 2012', get_date_suggestion('vår 2012'))
        self.assertEqual('høsten 2012', get_date_suggestion('hosten 2012'))
        self.assertEqual('vinteren 1971', get_date_suggestion('Winter, 1971'))
        self.assertEqual(None, get_date_suggestion('c. 2012'))
        self.assertEqual(None, get_date_suggestion('Nr 6, 2012'))
        self.assertEqual(None, get_date_suggestion('2007 - uke 25'))
        self.assertEqual('1942–1991', get_date_suggestion('1942 - 1991'))

    def test_date_suggestions_en(self):
        self.assertEqual('mai 2012', get_date_suggestion('May 2012'))
        self.assertEqual('12. september 2012', get_date_suggestion('12 September 2012'))
        self.assertEqual('14. oktober 2010', get_date_suggestion('14 October 2010'))
        self.assertEqual('14. oktober 2010', get_date_suggestion('14. October 2010'))
        self.assertEqual('6. juli 2011', get_date_suggestion('July 6, 2011'))
        self.assertEqual('oktober–november 1999', get_date_suggestion('October-November 1999'))
        self.assertEqual('15. juni 2006', get_date_suggestion('June 15, 2006 <!--DASHBot-->'))

    def test_date_suggestions_sv(self):
        self.assertEqual('12. mai 2012', get_date_suggestion('12. maj 2012'))

    def test_year_valid(self):
        self.assertTrue(is_valid_year('c. 2014'))
        self.assertTrue(is_valid_year('ca. 2014'))
        self.assertTrue(is_valid_year('2014'))
        self.assertFalse(is_valid_year('[[2014]]'))

    def test_year_suggestions(self):
        self.assertEqual('2014', get_year_suggestion('[[2014]]'))


if __name__ == '__main__':
    unittest.main()
