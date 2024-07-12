import logging
import datetime
import json
import os
import warnings
from vfb_connect.neo.neo4j_tools import Neo4jConnect, dict_cursor
from vfb_query_builder.schema_test_suite import get_validator, validate

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TestWrapper:

    def __init__(self, schema):
        logger.debug("Initializing TestWrapper")
        # This is all completely dependent on repo structure!
        # Ideally it would be configured by passing path as arg
        # But passing args doesn't work reliably with unittest lib.
        pwdl = os.getcwd()
        base = 'file://' + pwdl + '/json_schema/'
        self.V = get_validator(pwdl + "/json_schema/" + schema, base_uri=base)
        self.nc = Neo4jConnect('http://pdb-dev.virtualflybrain.org', 'neo4j', 'neo4j')
        logger.debug(f"Validator and Neo4j connection established. Base URI: {base}")

    def test_content(self, t, d, hard_fail=False):
        logger.debug("Running test_content")
        # test if dict?
        if type(d) == dict:
            for k, v in d.items():
                if not v:
                    warnings.warn("%s is empty" % k)
                    logger.warning(f"{k} is empty")
                if hard_fail:
                    t.assertTrue(bool(v))
                    logger.debug(f"Hard fail check: {k} is {'not empty' if v else 'empty'}")
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
        logger.debug("Running test")
        start_time = datetime.datetime.now()
        if print_query: 
            logger.debug(f"QUERY: {query}")
            print("QUERY: " + query)
        s = self.nc.commit_list([query])
        end_time = datetime.datetime.now()
        diff = end_time - start_time
        time_in_ms = (diff.total_seconds() * 1000)
        logger.debug(f"Query execution time: {time_in_ms} ms")
        
        t.assertTrue(s, "Cypher query failed.")
        if s:
            logger.debug("Cypher query succeeded")
            print(f"Query time (inc API call): {time_in_ms} ms")
            results = dict_cursor(s)
            # Only testing first result if multiple
            if print_result: 
                print(json.dumps(results[0]))
                logger.debug(f"Query results: {results[0]}")
            if single: 
                t.assertEqual(len(results), 1)
                logger.debug("Single result expected and found")
            validation_status = validate(self.V, results[0])
            logger.debug(f"Validation status: {validation_status}")
            t.assertTrue(validation_status)
            self.test_content(t, results[0])
            return results
        else:
            logger.debug("Cypher query returned no results")
            return False
