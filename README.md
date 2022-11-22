# VFB_json_schema [![PDB schema tests](https://github.com/VirtualFlyBrain/VFB_json_schema/actions/workflows/pdb_schema_tests.yml/badge.svg)](https://github.com/VirtualFlyBrain/VFB_json_schema/actions/workflows/pdb_schema_tests.yml)

VFB [json schema spec](https://virtualflybrain.github.io/VFB_json_schema/doc/schema_doc.html#term) + code for rolling queries producing VFB json schema + related integration tests


| PDB | Staging  | Dev  | P2 |
|-------------------|-------------------|-------------------| --- |
| [![Build1][1]][5] | [![Build2][2]][6] | [![Build3][3]][7] | [![Build4][4]][8]

[1]: https://github.com/VirtualFlyBrain/VFB_json_schema/actions/workflows/pdb_schema_tests.yml/badge.svg
[2]: https://github.com/VirtualFlyBrain/VFB_json_schema/actions/workflows/PDB-alpha_schema_tests.yml/badge.svg
[3]: https://github.com/VirtualFlyBrain/VFB_json_schema/actions/workflows/PDB-dev_schema_tests.yml/badge.svg
[4]: https://github.com/VirtualFlyBrain/VFB_json_schema/actions/workflows/PipelinePDB_schema_tests.yml/badge.svg
[5]: https://github.com/VirtualFlyBrain/VFB_json_schema/actions/workflows/pdb_schema_tests.yml
[6]: https://github.com/VirtualFlyBrain/VFB_json_schema/actions/workflows/PDB-alpha_schema_tests.yml
[7]: https://github.com/VirtualFlyBrain/VFB_json_schema/actions/workflows/PDB-dev_schema_tests.yml
[8]: https://github.com/VirtualFlyBrain/VFB_json_schema/actions/workflows/PipelinePDB_schema_tests.yml

## How to add a query:

Queries are composed of clauses. Clauses are encoded by functions in vfb_query_builder.query_roller.QueryLibraryCore.  There main arguments are used to construct a clause (see pydoc for full args):
 MATCH : A Match statement - it is generally safer to use OPTIONAL MATCH here in case no info is returned.
 WITH: defines what goes in the WITH statement that follows.  This might be used to define simple literals (e.g expression_level) or blobs of JSON - most typically minimal node info.
 vars: list of vars from the with clause to pass along in subsequent with clauses and into the return clause.

Queries typically start with a 'term' clause.

To add a new query: 

1. Add new clauses to query_roller.QueryLibraryCore

e.g. 



2. Add any new keys specified in vars to the relevant JSON schema doc.

3. Add a query to the query_library using the querybuilder function, e.g. 

4. Add a new test to the relevant test library, 

e.g.   