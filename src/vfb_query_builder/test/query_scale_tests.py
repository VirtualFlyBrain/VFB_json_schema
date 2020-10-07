import unittest
from vfb_query_builder.query_roller import QueryLibrary
from vfb_connect.cross_server_tools import VfbConnect
from .test_tools import TestWrapper

class QueryRollerScaleTest(unittest.TestCase):

    def setUp(self):
        self.ql = QueryLibrary()
        self.qw = TestWrapper('vfb_query.json')
        self.vc = VfbConnect()
        print("Running", self.id().split('.')[1:])

    def test_anat_query_scaling(self):
        # test for hundreds
        #neurons = [n.split('/')[-1] for n in self.vc.oc.get_subclasses("'antennal lobe projection neuron'", query_by_label=True)]
        #query = self.ql.anat_query(short_forms=neurons)
        #print("Testing and printing first result in list only.")
        #r = self.qw.test(t=self,
        #                 query=query, single=False)
        # test for thousands
        neurons = [n.split('/')[-1] for n in self.vc.oc.get_subclasses("'neuron'", query_by_label=True)]
        query = self.ql.anat_query(short_forms=neurons)
        print("Testing and printing first result in list only.")
        r = self.qw.test(t=self,
                         query=query, single=False)


    def test_ind_query_scaling(self):
        # test for thousands
        neurons = [n.split('/')[-1] for n in self.vc.oc.get_instances("'antennal lobe projection neuron'", query_by_label=True)]
        query = self.ql.anat_image_query(short_forms=neurons)
        print("Testing and printing first result in list only.")
        r = self.qw.test(t=self,
                         query=query, single=False)
        # test for 10s of thousands (commenting for now as timing out)
        #neurons = [n.split('/')[-1] for n in self.vc.oc.get_instances("'neuron'", query_by_label=True)]
        #query = self.ql.anat_image_query(short_forms=neurons)
        #print("Testing and printing first result in list only.")
        #r = self.qw.test(t=self,
        #                query=query, single=False)

if __name__ == '__main__':
    unittest.main()
