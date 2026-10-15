import unittest
from evaluate import canonical,evaluate

class ScoringTests(unittest.TestCase):
    def test_formats_and_sign(self):
        self.assertEqual(canonical('gesamtbetrag','22.849,78 EUR'),canonical('gesamtbetrag','22849.78'))
        self.assertNotEqual(canonical('gesamtbetrag','-22849.78'),canonical('gesamtbetrag','22849.78'))
        self.assertNotEqual(canonical('gesamtbetrag','22849.78'),canonical('gesamtbetrag','22849.79'))
    def test_date(self):
        self.assertEqual(canonical('belegdatum','2026-07-14'),canonical('belegdatum','14.07.2026'))
    def test_missing_is_not_null_prediction(self):
        truth=[{'id':'x','split':'setup','family':'A','variant':'digital','fields':{'ust_idnr':{'value':None}}}]
        missing=evaluate(truth,[],['ust_idnr'])['summary']['all']
        self.assertEqual(missing['correct'],0)
        null=evaluate(truth,[{'id':'x','fields':{'ust_idnr':None}}],['ust_idnr'])['summary']['all']
        self.assertEqual(null['correct'],1)
        hallucination=evaluate(truth,[{'id':'x','fields':{'ust_idnr':'DE123'}}],['ust_idnr'])['summary']['all']
        self.assertEqual(hallucination['hallucinated_absent'],1)
    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError):evaluate([], [{'id':'unknown','fields':{}}], [])
    def test_invalid_types(self):
        self.assertNotEqual(canonical('gesamtbetrag',True),canonical('gesamtbetrag','1'))
        self.assertNotEqual(canonical('gesamtbetrag','NaN'),canonical('gesamtbetrag','1'))

if __name__=='__main__':unittest.main()
