import unittest
from vfb_query_builder.pypher_query_roller import QueryLibrary, query_builder
from .test_tools import TestWrapper


class TermInfoRollerTest(unittest.TestCase):

    def setUp(self):
        self.ql = QueryLibrary()
        self.qw = TestWrapper('vfb_termInfo.json')
        print("Running", self.id().split('.')[1:])

    def test_class_term(self):
        query = query_builder(query_labels=["Class"],
                              clauses=[self.ql.term()],
                              query_short_forms=['FBbt_00000591'])

        r = self.qw.test(t=self, query=query)

    def test_individual_term(self):
        query = query_builder(query_labels=["Individual"],
                              clauses=[self.ql.term()],
                              query_short_forms=['VFB_00011179'])
        r = self.qw.test(t=self, query=query)

    def test_class_images(self):
        query = query_builder(query_labels=["Class"],
                              clauses=[self.ql.term(),
                                       self.ql.anatomy_channel_image()],
                              query_short_forms=['FBbt_00007422'])
        print(query)
        r = self.qw.test(t=self, query=query)

    def test_class_xrefs(self):
        query = query_builder(query_labels=["Class"],
                              clauses=[self.ql.term(),
                                       self.ql.xrefs()],
                              query_short_forms=['VFBexp_FBtp0123937FBtp0120068'])
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
                              query_short_forms=['VFB_00010249'])
        r = self.qw.test(t=self,
                         query=query)

    def test_individual_image(self):
        query = query_builder(query_labels=["Individual"],
                              clauses=[self.ql.term(),
                                       self.ql.channel_image()],
                              query_short_forms=['VFB_00011179'])
        r = self.qw.test(t=self,
                         query=query)

    def test_convert(self):
        self.ql.test_func()
