from vfb_connect.neo.neo4j_tools import Neo4jConnect, dict_cursor
from vfb_query_builder.schema_test_suite import get_validator, validate
import datetime
import json
import os
import warnings


class TestWrapper:

    def __init__(self, schema):



        # This is all completely dependent on repo structure!
        # Ideally it would be configured by passing path as arg
        # But passing args doesn't work reliably with unittest lib.
        pwdl = os.getcwd()
        base = 'file://' + pwdl + '/json_schema/'
        self.V = get_validator(pwdl + "/json_schema/" + schema,
                                base_uri=base)
        self.nc = Neo4jConnect('http://pdb-dev.virtualflybrain.org', 'neo4j', 'neo4j')

    def test_content(self, t, d, hard_fail=False):
        # test if dict?
        if type(d) == dict:
            for k,v in d.items():
                if not v:
                    warnings.warn("%s is empty" % k)
                if hard_fail:
                    t.assertTrue(bool(v))
            #    self.test_content(t, v)


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
            results = dict_cursor(s)
            # Only testing first result if multiple
            if print_result: print(json.dumps(results[0]))
            if single: t.assertEqual(len(results), 1)
            validation_status = validate(self.V, results[0])
            t.assertTrue(validation_status)
            self.test_content(t, results[0])
            return results
        else:
            return False
