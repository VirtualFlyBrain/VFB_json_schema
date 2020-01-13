import unittest
from vfb_query_builder.query_roller import QueryLibrary, term_info_export


class QueryRollerTest(unittest.TestCase):

    def setup(self):
        self.ql = QueryLibrary()

    def test_term_info_query(self):
        print(term_info_export())


if __name__ == '__main__':
    unittest.main()
