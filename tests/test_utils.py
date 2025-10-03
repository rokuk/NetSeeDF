import unittest
from utils import tuple_length

class TestTupleLength(unittest.TestCase):
    def test_valid_tuples(self):
        self.assertEqual(tuple_length('(1,2,3)'), 3)
        self.assertEqual(tuple_length('(1,)'), 1)
        self.assertEqual(tuple_length('(a,b,c)'), 3)
        self.assertEqual(tuple_length('(1, 2, 3)'), 3)
        self.assertEqual(tuple_length('(1,2,3,4,5)'), 5)
        self.assertEqual(tuple_length('(foo, bar)'), 2)
        self.assertEqual(tuple_length('( 1 , 2 , 3 )'), 3)
        self.assertEqual(tuple_length('(a, b, c, d)'), 4)

    def test_invalid_tuples(self):
        self.assertEqual(tuple_length(''), -1)
        self.assertEqual(tuple_length('()'), -1)
        self.assertEqual(tuple_length('abc'), -1)
        self.assertEqual(tuple_length('[1,2,3]'), -1)
        self.assertEqual(tuple_length('(1, 2, 3'), -1)
        self.assertEqual(tuple_length('1,2,3'), -1)
        self.assertEqual(tuple_length('(1,,2)'), -1)  # Double comma
        self.assertEqual(tuple_length('(1, 2,, 3)'), -1)
        self.assertEqual(tuple_length('(   )'), -1)  # whitespace only
        self.assertEqual(tuple_length('(1,2,3,)'), -1)  # Trailing comma
        self.assertEqual(tuple_length('(1, (2,3))'), -1)  # Nested tuple as string
        self.assertEqual(tuple_length('(1, (2, 3), 4)'), -1)
        self.assertEqual(tuple_length(None), -1)  # Non-string input
        self.assertEqual(tuple_length(123), -1)   # Non-string input
        self.assertEqual(tuple_length('(, )'), -1)  # tricky case: two empty elements
        self.assertEqual(tuple_length('(  ,   )'), -1)  # two empty elements with spaces
        self.assertEqual(tuple_length('( , , )'), -1)  # three empty elements
        self.assertEqual(tuple_length('( ,a, )'), -1) # empty, value, empty (invalid)
        self.assertEqual(tuple_length('(a,,b)'), -1)  # value, empty, value (invalid)
        self.assertEqual(tuple_length('(a, ,b)'), -1) # value, empty, value (invalid)
        self.assertEqual(tuple_length('(a, b, c, d, )'), -1)

if __name__ == '__main__':
    unittest.main()
