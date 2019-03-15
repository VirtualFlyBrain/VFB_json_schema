import unittest
from query_roller import QueryLibrary, query_builder
from uk.ac.ebi.vfb.neo4j.neo4j_tools import neo4j_connect, results_2_dict_list
from schema_test_suite import get_validator, validate
import datetime
import json
import os


class TestWrapper:

    def __init__(self, schema):

        # This is all completely dependent on repo structure!
        # Ideally it would be configured by passing path as arg
        # But passing args doesn't work reliably with unittest lib.

        pwdl = os.getcwd().split('/')
        base = 'file://' + '/'.join(pwdl[0:-2]) + '/json_schema/'
        self.V = get_validator("../../json_schema/" + schema,
                               base_uri=base)
        self.nc = neo4j_connect('http://pdb.virtualflybrain.org', 'neo4j', 'neo4j')

    def test(self, t, query, single=True, print_result=True, print_query=True):

        """Runs Cypher query.
            Tests if query failed else
            Tests length of results,
            Tests results validity against schema.
            query = cypher query,
            t = QueryRollerTest object,
            single = True if results list length should be one
            print results: wot it sez on the tin"""
        start_time = datetime.datetime.now()
        if print_query: print("QUERY: " + query)
        s = self.nc.commit_list([query])
        end_time = datetime.datetime.now()
        diff = end_time - start_time
        time_in_ms = (diff.total_seconds() * 1000)
        t.assertTrue(s, "Cypher query failed.")
        if s:
            print("Query time (inc API call): %d ms" % time_in_ms)
            results = results_2_dict_list(s)
            if print_result: print(json.dumps(results[0]))
            if single: t.assertEqual(len(results), 1)
            validation_status = validate(self.V, results[0])
            t.assertTrue(validation_status)
            return results
        else:
            return False


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


class QueryRollerTest(unittest.TestCase):

    def setUp(self):
        self.ql = QueryLibrary()
        self.qw = TestWrapper('vfb_query.json')
        print("Running", self.id().split('.')[1:])


    def test_anat_2_ep_query(self):
        query= self.ql.anat_2_ep_query(short_forms=["FBbt_00050101", "FBbt_00050253", "FBbt_00050143", "FBbt_00050167", "FBbt_00110412", "FBbt_00100218", "FBbt_00003638", "FBbt_00003662", "FBbt_00003641", "FBbt_00003639", "FBbt_00110325", "FBbt_00111506", "FBbt_00111052", "FBbt_00111507", "FBbt_00111508", "FBbt_00111053", "FBbt_00111509", "FBbt_00111510", "FBbt_00111055", "FBbt_00111054", "FBbt_00040033", "FBbt_00110151", "FBbt_00003646", "FBbt_00003643", "FBbt_00110326", "FBbt_00007566", "FBbt_00007565", "FBbt_00007564", "FBbt_00007563", "FBbt_00007562", "FBbt_00007561", "FBbt_00007560", "FBbt_00007559", "FBbt_00003634"], pretty_print=True)

#       r = self.qw.test(t=self,
#                     query=query)

    def test_ep_2_anat_query(self):
        query= self.ql.ep_2_anat_query('VFBexp_FBtp0040533',
                                       pretty_print=True)

 #       r = self.qw.test(t=self,
 #                    query=query)


if __name__ == '__main__':
    unittest.main(verbosity=2)
