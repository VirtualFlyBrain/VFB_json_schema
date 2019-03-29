import unittest
from vfb_query_builder.query_roller import QueryLibrary, query_builder
from .test_tools import TestWrapper


class TermInfoRollerTest(unittest.TestCase):

    def setUp(self):
        self.ql = QueryLibrary()
        self.qw = TestWrapper('vfb_terminfo.json')
        print("Running", self.id().split('.')[1:])

    def test_class_term(self):
        query = query_builder(query_labels=["Class"],
                              clauses=[self.ql.term()],
                              query_short_forms=['FBbt_00007422'])
        r = self.qw.test(t=self,
                         query=query)

    def test_individual_term(self):
        query = query_builder(query_labels=["Individual"],
                              clauses=[self.ql.term()],
                              query_short_forms=['VFB_00011179'])
        r = self.qw.test(t=self,
                         query=query)

    def test_class_images(self):
        query = query_builder(query_labels=["Class"],
                              clauses=[self.ql.term(),
                                       self.ql.anatomy_channel_image()],
                              query_short_forms=['FBbt_00007422'])
        r = self.qw.test(t=self,
                         query=query)

    def test_class_xrefs(self):
        query = query_builder(query_labels=["Class"],
                              clauses=[self.ql.term(), 
                                       self.ql.xrefs()],
                              query_short_forms=['FBbt_00007422'])
        r = self.qw.test(t=self,
                         query=query)

    def test_class_parents(self):
        query = query_builder(query_labels=["Class"],
                              clauses=[self.ql.term(), 
                                       self.ql.parents()],
                              query_short_forms=['FBbt_00007422'])
        r = self.qw.test(t=self,
                         query=query)

    def test_class_relationships(self):
        query = query_builder(query_labels=["Class"],
                              clauses=[self.ql.term(),
                                       self.ql.relationships()],
                              query_short_forms=['FBbt_00007422'])
        r = self.qw.test(t=self,
                         query=query)

    def test_class_def_pubs(self):
        query = query_builder(query_labels=["Class"],
                              clauses=[self.ql.term(),
                                       self.ql.def_pubs()],
                              query_short_forms=['FBbt_00000591'])
        r = self.qw.test(t=self,
                         query=query)

    def test_class_pub_syn(self):
        query = query_builder(query_labels=["Class"],
                              clauses=[self.ql.term(),
                                       self.ql.pub_syn()],
                              query_short_forms=['FBbt_00000591'])
        r = self.qw.test(t=self,
                         query=query)

    def test_individual_relationships(self):
        query = query_builder(query_labels=["Individual"],
                              clauses=[self.ql.term(),
                                       self.ql.relationships()],
                              query_short_forms=['VFB_00011179'])
        r = self.qw.test(t=self,
                         query=query)

    def test_individual_parents(self):
        query = query_builder(query_labels=["Individual"],
                              clauses=[self.ql.term(),
                                       self.ql.parents()],
                              query_short_forms=['VFB_00011179'])
        r = self.qw.test(t=self,
                         query=query)

    def test_individual_xrefs(self):
        query = query_builder(query_labels=["Individual"],
                              clauses=[self.ql.term(),
                                       self.ql.xrefs()],
                              query_short_forms=['VFB_00020249'])
        r = self.qw.test(t=self,
                         query=query)

    def test_individual_image(self):
        query = query_builder(query_labels=["Individual"],
                              clauses=[self.ql.term(),
                                       self.ql.channel_image()],
                              query_short_forms=['VFB_00011179'])
        r = self.qw.test(t=self,
                         query=query)

    def test_individual_dataset_license(self):
        query = query_builder(query_labels=["Individual"],
                              clauses=[self.ql.term(),
                                       self.ql.dataSet_license()],
                              query_short_forms=['VFB_00011179'])
        r = self.qw.test(t=self,
                         query=query)

    def test_class(self):
        query = self.ql.class_query(short_form='FBbt_00007422')
        r = self.qw.test(t=self,
                         query=query)

    def test_individual(self):
        query = self.ql.anatomical_ind_query(short_form='VFB_00011179')
        r = self.qw.test(t=self,
                         query=query)

    def test_dataset_license(self):
        query = query_builder(query_labels=['DataSet'],
                              query_short_forms=['Ito2013'],
                              clauses=[self.ql.term(),
                                       self.ql.license()])
        r = self.qw.test(t=self,
                         query=query)

    def test_dataset_xrefs(self):
        query = query_builder(query_labels=['DataSet'],
                              query_short_forms=['Ito2013'],
                              clauses=[self.ql.term(),
                                       self.ql.xrefs()])
        r = self.qw.test(t=self,
                         query=query)

    def test_dataset_pub(self):
        query = query_builder(query_labels=['DataSet'],
                              query_short_forms=['Ito2013'],
                              clauses=[self.ql.term(),
                                       self.ql.pub()])
        r = self.qw.test(t=self,
                         query=query)

    def test_dataset_anatomy_channel_image(self):
        query = query_builder(query_labels=['DataSet'],
                              query_short_forms=['Ito2013'],
                              clauses=[self.ql.term(),
                                       self.ql.anatomy_channel_image()])
        r = self.qw.test(t=self,
                         query=query)

    def test_template(self):
        query = self.ql.template_query(short_form="VFB_00017894", pretty_print=True)
        r = self.qw.test(t=self,
                         query=query)

    def test_template_domains(self):
        query = query_builder(query_labels=['Template'],
                              query_short_forms=['VFB_00017894'],
                              clauses=[self.ql.term(),
                                       self.ql.template_domain()])
        r = self.qw.test(t=self,
                         query=query)

    def test_template_channel(self):
        query = query_builder(query_labels=['Template'],
                              query_short_forms=['VFB_00017894'],
                              clauses=[self.ql.term(),
                                       self.ql.template_channel()])
        r = self.qw.test(t=self,
                         query=query)

    def tearDown(self):
        return

