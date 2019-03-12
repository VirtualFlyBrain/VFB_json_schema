import unittest
from query_roller import QueryGenerator
from uk.ac.ebi.vfb.neo4j.neo4j_tools import neo4j_connect,results_2_dict_list
from schema_test_suite import get_validator, validate
import datetime
import json

class test_wrapper():

    def __init__(self):
        self.V = get_validator("../../json_schema/vfb_termInfo.json")
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


class QueryRollerTest(unittest.TestCase):

    def setUp(self):
        self.qg = QueryGenerator()
        self.qw = test_wrapper()
        print("Running", self.id().split('.')[1:])



    def test_class_term(self):
        query = self.qg.roll_query(types=["Class"],
                                   clauses=[],
                                   short_form='FBbt_00007422')
        r = self.qw.test(t=self,
                         query=query)


    def test_individual_term(self):
        query = self.qg.roll_query(types=["Individual"],
                                   clauses=[],
                                   short_form='VFB_00011179')
        r = self.qw.test(t=self,
                         query=query)

    def test_class_images(self):

        query = self.qg.roll_query(types=["Class"],
                                   clauses=[self.qg.anatomy_channel_image],
                                   short_form='FBbt_00007422')
        r = self.qw.test(t=self,
                         query=query)

    def test_class_xrefs(self):
        query = self.qg.roll_query(types=["Class"],
                                   clauses=[self.qg.xrefs],
                                   short_form='FBbt_00007422')
        r = self.qw.test(t=self,
                         query=query)


    def test_class_parents(self):
        query = self.qg.roll_query(types=["Class"],
                                   clauses=[self.qg.parents],
                                   short_form='FBbt_00007422')
        r = self.qw.test(t=self,
                         query=query)

    def test_class_relationships(self):
        query = self.qg.roll_query(types=["Class"],
                                   clauses=[self.qg.relationships],
                                   short_form='FBbt_00007422')
        r = self.qw.test(t=self,
                         query=query)

    def test_class_def_pubs(self):
        query = self.qg.roll_query(types=["Class"],
                                   clauses=[self.qg.def_pubs],
                                   short_form='FBbt_00000591')
        r = self.qw.test(t=self,
                         query=query)

    def test_class_pub_syn(self):
        query = self.qg.roll_query(types=["Class"],
                                   clauses=[self.qg.pub_syn],
                                   short_form='FBbt_00000591')
        r = self.qw.test(t=self,
                         query=query)

    def test_individual_relationships(self):
        query = self.qg.roll_query(types=["Individual"],
                                   clauses=[self.qg.relationships],
                                   short_form='VFB_00011179')
        r = self.qw.test(t=self,
                         query=query)


    def test_individual_parents(self):
        query = self.qg.roll_query(types=["Individual"],
                                   clauses=[self.qg.parents],
                                   short_form='VFB_00011179')
        r = self.qw.test(t=self,
                         query=query)

    def test_individual_xrefs(self):
        query = self.qg.roll_query(types=["Individual"],
                                   clauses=[self.qg.xrefs],
                                   short_form='VFB_00020249')
        r = self.qw.test(t=self,
                         query=query)

    def test_individual_image(self):
        query = self.qg.roll_query(types=["Individual"],
                                   clauses=[self.qg.channel_image],
                                   short_form='VFB_00011179')
        r = self.qw.test(t=self,
                         query=query)

    def test_individual_dataset_license(self):
        query = self.qg.roll_query(types=["Individual"],
                                   clauses=[self.qg.dataSet_license],
                                   short_form='VFB_00011179')
        r = self.qw.test(t=self,
                         query=query)


    def test_class(self):
        query = self.qg.class_query(short_form='FBbt_00007422')
        r = self.qw.test(t=self,
                         query=query)


    def test_individual(self):
        query = self.qg.anatomical_ind_query(short_form='VFB_00011179')
        r = self.qw.test(t=self,
                         query=query)


    def test_dataset_license(self):
        query = self.qg.roll_query(types = ['DataSet'],
                                   short_form='Ito2013',
                                   clauses=[self.qg.license])
        r = self.qw.test(t=self,
                         query=query)

    def test_dataset_xrefs(self):
        query = self.qg.roll_query(types = ['DataSet'],
                                   short_form='Ito2013',
                                   clauses=[self.qg.xrefs])
        r = self.qw.test(t=self,
                         query=query)

    def test_dataset_pub(self):
        query = self.qg.roll_query(types = ['DataSet'],
                                   short_form='Ito2013',
                                   clauses=[self.qg.pub])
        r = self.qw.test(t=self,
                         query=query)

    def test_dataset_anatomy_channel_image(self):
        query = self.qg.roll_query(types = ['DataSet'],
                                   short_form='Ito2013',
                                   clauses=[self.qg.anatomy_channel_image])
        r = self.qw.test(t=self,
                         query=query)

    def test_template(self):
        query = self.qg.template_query(short_form="VFB_00017894", pretty_print=True)
        r = self.qw.test(t=self,
                         query=query)

    def test_template_domains(self):
        query = self.qg.roll_query(types=['Template'],
                                   short_form='VFB_00017894',
                                   clauses=[self.qg.template_domain])
        r = self.qw.test(t=self,
                         query=query)

    def test_template_channel(self):
        query = self.qg.roll_query(types=['Template'],
                                   short_form='VFB_00017894',
                                   clauses=[self.qg.template_channel])
        r = self.qw.test(t=self,
                         query=query)


    def tearDown(self):
        return


if __name__ == '__main__':
    unittest.main(verbosity=2)
