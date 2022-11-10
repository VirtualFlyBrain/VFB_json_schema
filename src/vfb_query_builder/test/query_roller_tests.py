import unittest
from vfb_query_builder.query_roller import QueryLibrary, term_info_export
import difflib
import json
import urllib.request

class QueryRollerTest(unittest.TestCase):

    def setup(self):
        self.ql = QueryLibrary()
    
    def test_term_info_query(self):
        red = lambda text: f"\033[38;2;255;0;0m{text}\033[38;2;255;255;255m"
        green = lambda text: f"\033[38;2;0;255;0m{text}\033[38;2;255;255;255m"
        blue = lambda text: f"\033[38;2;0;0;255m{text}\033[38;2;255;255;255m"
        white = lambda text: f"\033[38;2;255;255;255m{text}\033[38;2;255;255;255m"
        oldquery = lambda text: f"\x1b[3;30;43m{text}\x1b[0m"
        newquery = lambda text: f"\x1b[6;30;42m{text}\x1b[0m"
        def get_edits_string(old, new):
            result = ""
            codes = difflib.SequenceMatcher(a=old, b=new).get_opcodes()
            for code in codes:
                if code[0] == "equal": 
                    result += white(old[code[1]:code[2]])
                elif code[0] == "delete":
                    result += red(old[code[1]:code[2]])
                elif code[0] == "insert":
                    result += green(new[code[3]:code[4]])
                elif code[0] == "replace":
                    result += (red(old[code[1]:code[2]]) + green(new[code[3]:code[4]]))
            return result
        
        queries = json.loads(term_info_export(escape='xmi'))
        # extract out the cypher queries from the ecore vfb.xmi file into model list
        ecore=urllib.request.urlopen("https://github.com/VirtualFlyBrain/geppetto-vfb/raw/master/model/vfb.xmi")
        model = []
        xmi = []
        for line in ecore:
            xmi.append(line.decode('utf-8'))
            if "query=" in line.decode('utf-8') and "&quot;statement&quot;" in line.decode('utf-8'):
                model.append(line.decode('utf-8').split('"')[1])
        for query in queries:
            print(query)
            print(newquery(queries[query]))
            for cypher in model:
                if query in cypher:
                    print(oldquery(cypher))
                    print(get_edits_string(cypher, queries[query]))
                    for index, line in enumerate(xmi):
                        if cypher in line:
                            xmi[index] = line.replace(cypher, queries[query])
                            break
        print('New vfb.xmi')
        print(''.join(xmi))

        queries = json.loads(term_info_export(escape='json'))
        # extract out the cypher queries from the VFBconnect master branch
        ecore=urllib.request.urlopen("https://github.com/VirtualFlyBrain/VFB_connect/raw/master/src/vfb_connect/resources/VFB_TermInfo_queries.json")
        model = []
        xmi = []
        for line in ecore:
            xmi.append(line.decode('utf-8'))
            if "Get JSON for " in line.decode('utf-8'):
                model.append(line.decode('utf-8'))
        for query in queries:
            print(query)
            print(newquery(queries[query]))
            for cypher in model:
                if query in cypher:
                    print(oldquery(cypher))
                    print(get_edits_string(cypher, queries[query]))
                    for index, line in enumerate(xmi):
                        if cypher in line:
                            xmi[index] = line.replace(cypher, queries[query])
                            break
        print('New VFB_TermInfo_queries.json')
        print(''.join(xmi))

        # extract out the cypher queries from the VFBconnect master branch
        ecore=urllib.request.urlopen("https://github.com/VirtualFlyBrain/VFB_connect/raw/master/src/vfb_connect/resources/VFB_results_single_input.json")
        model = []
        xmi = []
        for line in ecore:
            xmi.append(line.decode('utf-8'))
            if "Get JSON for " in line.decode('utf-8'):
                model.append(line.decode('utf-8'))
        for query in queries:
            print(query)
            print(newquery(queries[query]))
            for cypher in model:
                if query in cypher:
                    print(oldquery(cypher))
                    print(get_edits_string(cypher, queries[query]))
                    for index, line in enumerate(xmi):
                        if cypher in line:
                            xmi[index] = line.replace(cypher, queries[query])
                            break
        print('New VFB_results_single_input.json')
        print(''.join(xmi))


if __name__ == '__main__':
    unittest.main()
