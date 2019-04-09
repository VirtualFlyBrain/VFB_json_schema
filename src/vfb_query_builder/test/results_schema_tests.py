import unittest
from vfb_query_builder.query_roller import QueryLibrary
from .test_tools import TestWrapper

class QueryRollerTest(unittest.TestCase):

    def setUp(self):
        self.ql = QueryLibrary()
        self.qw = TestWrapper('vfb_query.json')
        print("Running", self.id().split('.')[1:])


    def test_anat_2_ep_query(self):
        query = self.ql.anat_2_ep_query(short_forms=["FBbt_00050101", "FBbt_00050253", "FBbt_00050143", "FBbt_00050167", "FBbt_00110412", "FBbt_00100218", "FBbt_00003638", "FBbt_00003662", "FBbt_00003641", "FBbt_00003639", "FBbt_00110325", "FBbt_00111506", "FBbt_00111052", "FBbt_00111507", "FBbt_00111508", "FBbt_00111053", "FBbt_00111509", "FBbt_00111510", "FBbt_00111055", "FBbt_00111054", "FBbt_00040033", "FBbt_00110151", "FBbt_00003646", "FBbt_00003643", "FBbt_00110326", "FBbt_00007566", "FBbt_00007565", "FBbt_00007564", "FBbt_00007563", "FBbt_00007562", "FBbt_00007561", "FBbt_00007560", "FBbt_00007559", "FBbt_00003634"], pretty_print=True)

        r = self.qw.test(t=self,
                     query=query, single=False)

    def test_ep_2_anat_query(self):
        query= self.ql.ep_2_anat_query('VFBexp_FBtp0106753',
                                       pretty_print=True)

        r = self.qw.test(t=self,
                    query=query)


if __name__ == '__main__':
    unittest.main(verbosity=2)

