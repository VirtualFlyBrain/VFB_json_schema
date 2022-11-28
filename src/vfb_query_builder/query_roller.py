from dataclasses import dataclass, field
from typing import List
from string import Template
import subprocess
from xml.sax import saxutils
import json


def get_version_tag():
    tag = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'])
    return tag.decode(encoding='ascii').rstrip()


@dataclass
class Clause:
    """Specifies a single cypher clause (MATCH + WITH/RETURN values + variables
    to be carried over in subsequent clause.)
    Conventions:
        1. First clause is a MATCH statement returning one or more nodes specified by
        a combination of neo4j labels specified in `starting labels`
        with a short_form in `starting_short_forms`, bound to the variable 'primary'
        (default specification of pvar).  This should have a return statement specifying how
        primary should be unpacked into a datastructure in  the return statement.
        2. Subsequent clauses are OPTIONAL MATCH statements, they may return a
        3. Any MATCH statement may consist of multiple whole cypher clauses (MATCH  + WITH)
          In this case, each internal WITH clause must have a $v for interpolation of
          accumulated vars

    MATCH: A cypher (OPTIONAL) MATCH clause. This must be a Template instance.
    It *may* contain references to interpolation vars, specified by clause attributes:
        $labels: labels of primary matched term.  Can be used to modify
                 labels of $pvar$labels in other clauses in order
                 to further restrict.
        $pvar: Binding for variable (node_var) from previous clause.
        By default bound to 'primary' but may be bound to any node_var specified
            in a previous clause.
        $ssf: starting short forms
        $v: vars
    WITH: A cypher string that converts variable output of the MATCH
          statement into one or more data structures (strings, lists or maps),
          each bound to a variable name.  These variable names must be
          referenced in vars.
    vars: a list of variable names for data structures in with statement.
          These will be interpolated into subsequent clauses and the return statement
    node_vars: a list of variables returned by the MATCH statement,
              referring to whole nodes, to be interpolated into subsequent clauses.
    RETURN: A cypher string that converts variables referenced in node_vars
    into a data structure in the final return statement of the generated cypher query.
    """

    MATCH: Template  # Should probably make this a string and refactor to make Template object inside function.
    WITH: str
    vars: List[str] = field(default_factory=list)
    RETURN: str = ''
    node_vars: List[str] = field(default_factory=list)
    starting_short_forms: list = field(default_factory=list)
    starting_labels: list = field(default_factory=list)
    pvar: str = 'primary'
    limit: str = ''
    prel: str = ''

    def get_clause(self, varz, pretty_print=True):
        """Generate a cypher string using the attributes of this clause object,
        interpolating a list of variables specified by the varz arg"""
        sep = ' '
        if pretty_print:
            sep = ' \n'
        l = ['']
        if self.starting_labels:
            l.extend(self.starting_labels)
        return sep.join(
            [self.MATCH.substitute(pvar=self.pvar,
                                   v=', '.join(varz),
                                   ssf=str(self.starting_short_forms),
                                   labels=':'.join(l),
                                   prel=self.prel,
                                   limit=self.limit),
             'WITH ' + ','.join([self.WITH] + varz)])


def query_builder(clauses: List[Clause], query_short_forms=None,
                  query_labels=None, pretty_print=True, annotate=True, q_name=''):
    """clauses: A list of Clause objects. The first element in the list must be an initial clause.
    Initial clauses must have slot for short_forms """

    if not query_labels:
        query_labels = []  # Set to some default for no var.
    clauses[0].starting_short_forms = query_short_forms
    clauses[0].starting_labels = query_labels

    sep = ' '
    if pretty_print:
        sep = ' \n'

    # Stacks
    node_vars = []
    data_vars = []
    return_clauses = []
    out = []

    for c in clauses:

        out.append(c.get_clause(varz=node_vars + data_vars))
        node_vars.extend(c.node_vars)
        data_vars.extend(c.vars)
        if c.RETURN:
            return_clauses.append(c.RETURN)

        # TODO: Add in some checks to make sure vars don't get stomped
    if annotate:
        if q_name:
            return_clauses.append("'%s' AS query" % q_name)
        return_clauses.append("'%s' AS version " % get_version_tag())
    return_clause = "RETURN " + ', '.join(return_clauses + data_vars)
    out.append(return_clause)
    return sep.join(out)


def roll_min_node_info(var):
    """Rolls core JSON (specifying minimal info about an entity.
    var: the variable name for the entity within this cypher clause."""
    return "{ short_form: %s.short_form, label: coalesce(%s.label,''), " \
           "iri: %s.iri, types: labels(%s), unique_facets: apoc.coll.sort(coalesce(%s.uniqueFacets, [])), symbol: coalesce(([]+%s.symbol)[0], '')} " % (var, var, var, var, var, var)



def roll_min_edge_info(var):
    """Rolls core JSON (specifying minimal info about an edge.
    var: the variable name for the edge within this cypher clause."""
    return "{ label: %s.label, " \
           "iri: %s.iri, type: type(%s) } " % (var, var, var)  # short_forms are not present in OLS-PDB

def roll_pub_return(var):
    s = Template("{ core: $core, "
                 "PubMed: coalesce(([]+$v.PMID)[0], ''), "
                 "FlyBase: coalesce(([]+$v.FlyBase)[0], ''), DOI: coalesce(([]+$v.DOI)[0], '') }")
    return s.substitute(core=roll_min_node_info(var), v=var)


# We sometimes need to extend return from term with additional info from other clauses
# For this it helps to contruct return as a dict

def roll_license_return_dict(var):
    return {'icon': "coalesce(([]+%s.license_logo)[0], '')" % var,
            'link': "coalesce(([]+%s.license_url)[0], '')" % var}


def roll_dataset_return_dict(var, typ=''):
    return {
        "link": "coalesce(([]+%s.dataset_link)[0], '')" % var,
    }


def roll_node_map(var: str, d: dict, typ=''):
    if typ:
        if typ == 'core':
            d.update({'core': roll_min_node_info(var)})
        elif typ == 'extended_core':
            d.update({'core': roll_min_node_info(var),
                      'description': "coalesce(%s.description, [])" % var,
                      "comment": "coalesce(%s.comment, [])" % var
                      })

        else:
            raise Exception('Unknown type: %s should be one or core, extended_core' % typ)
    return '{ ' + ', '.join([' : '.join(kv) for kv in d.items()]) + ' }'


class QueryLibraryCore:

    # Using class to wrap for convenience.
    # Could do the same with a set of static methods.
    # This class contains methods for generating query clauses.

    def __init__(self):
        # Using methods for ease of reading code - so these can be next to queries where they apply.
        self._set_image_query_common_elements()
        self._set_pub_common_query_elements()
        self.dataset_spec_fields = {
            "link": "coalesce(%s.dataset_link, '')"
        }
        self.license_spec_fields = {'icon': "coalesce(([]+%s.license_logo)[0], '')",
                                    'link': "coalesce(([]+%s.license_url)[0], '')x"
                                    }

    def term(self, return_extensions=None):
        if return_extensions is None:
            return_extensions = {}
        return Clause(
            MATCH=Template("MATCH (primary$labels) WHERE primary.short_form in $ssf "),
            WITH='primary',
            node_vars=['primary'],
            RETURN=roll_node_map(
                d=return_extensions,
                typ='extended_core',
                var='primary') + " AS term")

    # EXPRESSION QUERIES

    def xrefs(self):
        match_self_xref = "OPTIONAL MATCH (s:Site { short_form: apoc.convert.toList(primary.self_xref)[0] }) "
        match_ext_xref = "OPTIONAL MATCH (s:Site)<-[dbx:database_cross_reference]-($pvar$labels) "

        xr = "CASE WHEN s IS NULL THEN %s ELSE COLLECT" \
             "({ link_base: coalesce(([]+s.link_base)[0], ''), " \
             "accession: coalesce(%s, ''), " \
             "link_text: primary.label + ' on ' + s.label, " \
             "homepage: coalesce(([]+s.homepage)[0], ''), " \
             "site: %s, icon: coalesce(([]+s.link_icon_url)[0], ''),  " \
             "link_postfix: coalesce(([]+s.link_postfix)[0], '')}) "  # Should be $pvar$labels not primary, but need sub on WITH!
        xrs = "END AS self_xref, $v"  # Passing vars
        xrx = "+ self_xref END AS xrefs"

        return Clause(
            MATCH=Template(' '.join([match_self_xref, "WITH", xr, xrs, match_ext_xref])
                           % ('[]', 'primary.short_form',
                              roll_min_node_info("s"))),
            WITH='  '.join([xr, xrx]) % ('self_xref',
                                         '([]+dbx.accession)[0]',
                                         roll_min_node_info("s")),
            vars=["xrefs"])

    # RELATIONSHIPS

    def parents(self):  return Clause(vars=["parents"],
                                      MATCH=Template("OPTIONAL MATCH (o:Class)"
                                                     "<-[r:SUBCLASSOF|INSTANCEOF]-($pvar$labels) "),
                                      WITH="CASE WHEN o IS NULL THEN [] ELSE COLLECT "
                                           "(%s) END AS parents " % roll_min_node_info("o"))  # Draft

    def relationships(self): return (Clause(vars=["relationships"],
                                            MATCH=Template("OPTIONAL MATCH "
                                                           "(o:Class)<-[r {type:'Related'}]-($pvar$labels)"),
                                            WITH="CASE WHEN o IS NULL THEN [] "
                                                 "ELSE COLLECT ({ relation: %s, object: %s }) "
                                                 "END AS relationships " % (roll_min_edge_info("r"),
                                                                            roll_min_node_info("o"))))

    def related_individuals(self): return (Clause(vars=["related_individuals"],
                                                  MATCH=Template(
                                                      "OPTIONAL MATCH "
                                                      "(o:Individual)<-[r {type:'Related'}]-($pvar$labels)"),
                                                  WITH="CASE WHEN o IS NULL THEN [] ELSE COLLECT "
                                                       "({ relation: %s, object: %s }) "
                                                       "END AS related_individuals "
                                                       % (roll_min_edge_info("r"),
                                                          roll_min_node_info("o"))))

    def ep_stage(self):
        return Clause(
            MATCH=Template("OPTIONAL MATCH ($pvar$labels)-[r:Related]->(o:FBdv)"),
            WITH="CASE WHEN o IS NULL THEN [] ELSE COLLECT "
                 "({ relation: %s, object: %s }) "
                 "END AS stages "
                 "" % (roll_min_edge_info("r"),
                       roll_min_node_info("o")),
            vars=['stages']
        )

    # IMAGES

    def anat_cluster_dataset_pubs(self):
        return Clause(
            MATCH=Template("MATCH ($pvar$labels)<-[:composed_primarily_of]-(c:Cluster)"
                           "-[:has_source]->(ds:scRNAseq_DataSet)"
                           "OPTIONAL MATCH (ds)-[:has_reference]->(p:pub)"),
            WITH="%s AS cluster, %s AS dataset, COLLECT(%s) AS pubs" 
                 "" % (roll_min_node_info("c"), roll_min_node_info("ds"), roll_pub_return("p")),
            vars=["cluster, dataset, pubs"]
        )

    def cluster_anat(self):
        return Clause(
            MATCH=Template("MATCH (a:Anatomy)<-[:composed_primarily_of]-($pvar$labels)"),
            WITH="%s AS anatomy" 
                 "" % roll_min_node_info("a"),
            vars=["anatomy"]
        )

    def cluster_expression(self):
        return Clause(
            MATCH=Template("MATCH ($pvar$labels)-[e:expresses]->(g:Gene)"),
            WITH="e.expression_level[0] as expression_level, "
                 "e.expression_extent[0] as expression_extent, "
                 "%s AS gene" % (roll_min_node_info("g")),
            vars=["expression_level", "expression_extent", "gene"]
        )

    def _set_image_query_common_elements(self):
        self._channel_image_match = "<-[:depicts]-" \
                                    "(channel:Individual)-[irw:in_register_with]" \
                                    "->(template:Individual)-[:depicts]->" \
                                    "(template_anat:Individual) WITH template" \
                                    ", channel, template_anat, irw, $v %s $limit " \
                                    "OPTIONAL MATCH (channel)-[:is_specified_output_of" \
                                    "]->(technique:Class) "

        self._channel_image_return = "{ channel: %s, imaging_technique: %s," \
                                     "image: { template_channel : %s, template_anatomy: %s," \
                                     "image_folder: COALESCE(([]+irw.folder)[0], ''), " \
                                     "index: coalesce(apoc.convert.toInteger(([]+irw.index)[0]), []) + [] }" \
                                     "}" % (roll_min_node_info('channel'),
                                            roll_min_node_info('technique'),
                                            roll_min_node_info('template'),
                                            roll_min_node_info('template_anat'))

    def channel_image(self):
        return Clause(
            MATCH=Template("OPTIONAL MATCH ($pvar$labels)" + self._channel_image_match % ''),
            WITH="CASE WHEN channel IS NULL THEN []"
                 " ELSE collect (" + self._channel_image_return + ") END AS channel_image",
            vars=["channel_image"])

 #   def type_anatomy_channel_image(self):
 #       return Clause(
 #           MATCH=Template("MATCH (primary:Class) WHERE primary.short_form IN $ssf WITH primary "
 #                          "MATCH (primary)<-[:SUBCLASSOF*0..]-(c2:Class)<-[:INSTANCEOF]-(i:Individual)"
 #                          "" + self._channel_image_match % ', i'),
 #           WITH="c2, i",
 #           RETURN="CASE WHEN channel IS NULL THEN [] "
 #                  "ELSE collect({ type: collect(distinct(%s), anatomy: %s, channel_image: %s })"
 #                  "AS type_anatomy_channel_image" % (roll_min_node_info("c2"),
 #                                                     roll_min_node_info("i"),
 #                                                     self._channel_image_return),
 #           vars=["type_anatomy_channel_image"]
 #       )

    def image_type(self):
        return Clause(
            MATCH=Template("OPTIONAL MATCH ($pvar)-[:INSTANCEOF]->(typ:Class) "),
            WITH="CASE WHEN typ is null THEN [] "
                 "ELSE collect (%s) END AS types" % roll_min_node_info('typ'),
        vars=["types"])

    def anatomy_channel_image(self):

        return Clause(
            MATCH=Template(
                "CALL apoc.cypher.run('WITH $pvar OPTIONAL MATCH ($pvar$labels)<- "
                "[:has_source|SUBCLASSOF|INSTANCEOF*]-(i:Individual)<-[:depicts]- "
                "(channel:Individual)-[irw:in_register_with] "
                "->(template:Individual)-[:depicts]-> "
                "(template_anat:Individual) RETURN template, channel, template_anat, i, irw "
                "limit 10', {$pvar:$pvar}) yield value with value.template as template, value.channel as channel,"
                "value.template_anat as template_anat, value.i as i, value.irw as irw, $v "
                "OPTIONAL MATCH (channel)-[:is_specified_output_of]"
                "->(technique:Class) "),
            WITH="CASE WHEN channel IS NULL THEN [] " \
                 "ELSE COLLECT({ anatomy: %s, channel_image: %s }) " \
                 "END AS anatomy_channel_image " % (
                     roll_min_node_info("i"), self._channel_image_return),

            vars=["anatomy_channel_image"],
            limit='limit 10, {}) yield value')

    def template_domain(self):  return Clause(
        MATCH=Template(
            "OPTIONAL MATCH (technique:Class)<-[:is_specified_output_of]"
            "-(channel:Individual)"
            "-[irw:in_register_with]->(template:Individual)-[:depicts]->($pvar$labels) "
            "WHERE technique.short_form IN ['FBbi_00000224','FBbi_00000251'] "
            "AND exists(irw.index) "
            "WITH $v, collect ({ channel: channel, irw: irw}) AS painted_domains "
            "UNWIND painted_domains AS pd "
            "OPTIONAL MATCH (channel:Individual { short_form: pd.channel.short_form})"
            "-[:depicts]-(ai:Individual)-[:INSTANCEOF]->(c:Class) "),
        WITH="collect({ anatomical_type: %s ,"
             " anatomical_individual: %s, folder: ([]+pd.irw.folder)[0], "
             "center: coalesce (pd.irw.center, []), "
             "index: [] + coalesce (pd.irw.index, []) })"
             " AS template_domains" % (roll_min_node_info("c"),
                                       roll_min_node_info("ai")),
        vars=["template_domains"])

    def template_channel(self):  return Clause(
        MATCH=Template(
            "MATCH (channel:Individual)<-[irw:in_register_with]-"
            "(channel:Individual)-[:depicts]->($pvar$labels)"),
        WITH="{ index: coalesce(apoc.convert.toInteger(irw.index), []) + [], "
             "extent: ([]+irw.extent)[0], center: ([]+irw.center)[0], voxel: ([]+irw.voxel)[0], "
             "orientation: coalesce(([]+irw.orientation)[0], ''), "
             "image_folder: coalesce(([]+irw.folder)[0],''), "
             "channel: %s } as template_channel" % roll_min_node_info("channel"),
        vars=["template_channel"])

    ## PUBS

    def _set_pub_common_query_elements(self):
        # This is only a function for ease of code editing - places declaration next to where it is used.
        self._pub_return = "{ core: %s, " \
                           "PubMed: coalesce(([]+p.PMID)[0], ''), " \
                           "FlyBase: coalesce(([]+p.FlyBase)[0], ''), " \
                           "DOI: coalesce(([]+p.DOI)[0], '') } " \
                           "" % roll_min_node_info("p")

        # temp fixes in here for list -> single !
        self._syn_return = "{ label: coalesce(([]+rp.value)[0], ''), " \
                            "scope: coalesce(rp.scope, ''), " \
                            "type: coalesce(([]+rp.has_synonym_type)[0],'') } "

    def def_pubs(self):
        return Clause(MATCH=Template("OPTIONAL MATCH ($pvar$labels)-"
                                     "[rp:has_reference]->(p:pub) "
                                     "WHERE rp.typ = 'def' "),  # tmp fix rp.typ shld be []]!
                      WITH="CASE WHEN p is null THEN "
                           "[] ELSE collect(" + self._pub_return
                           + ") END AS def_pubs",
                      vars=['def_pubs'])

    def pub_syn(self):
        return Clause(MATCH=Template("OPTIONAL MATCH ($pvar$labels)-"
                                     "[rp:has_reference]->(p:pub) where rp.typ = 'syn'"),  # tmp fix rp.typ shld be []]!
                      WITH="CASE WHEN p is null THEN [] "
                           "ELSE collect({ pub: %s, synonym: %s }) END AS pub_syn"
                           % (self._pub_return, self._syn_return),
                      vars=['pub_syn'])

    def pubs(self):
        return Clause(MATCH=Template("OPTIONAL MATCH ($pvar$labels)"
                                     "-[rp:has_reference]->(p:pub) "),
                      WITH="CASE WHEN p is null THEN [] ELSE "
                           "collect(" + self._pub_return + ") END AS pubs",
                      vars=['pubs'])

    def neuron_split(self):
        return Clause(
            MATCH=Template("OPTIONAL MATCH (:Class { label: 'intersectional expression pattern'})"
                           "<-[:SUBCLASSOF]-(ep:Class)<-[ar:part_of]-(anoni:Individual)"
                           "-[:INSTANCEOF]->($pvar)"),
            WITH="CASE WHEN ep IS NULL THEN [] ELSE COLLECT(%s) END AS targeting_splits" % roll_min_node_info("ep"),
            vars=['targeting_splits'])

    def split_neuron(self):
        return Clause(
            MATCH=Template("OPTIONAL MATCH (:Class { label: 'intersectional expression pattern'})"
                           "<-[:SUBCLASSOF]-($pvar)<-[ar:part_of]-(anoni:Individual)"
                           "-[:INSTANCEOF]->(n:Neuron)"),
            WITH="CASE WHEN n IS NULL THEN [] ELSE COLLECT(%s) END AS target_neurons" % roll_min_node_info("n"),
            vars=['target_neurons'])


    def dataSet_license(self, prel='has_source'):
        return Clause(
            MATCH=Template("OPTIONAL MATCH "
                           "($pvar$labels)-[:$prel]-(ds:DataSet)"
                           "-[:has_license|license]->(l:License)"),
            WITH="COLLECT ({ dataset: %s, license: %s}) "
                 "AS dataset_license" % (roll_node_map(var='ds',
                                                       d=roll_dataset_return_dict('ds'),
                                                       typ='core'),
                                         roll_node_map(var='l',
                                                       d=roll_license_return_dict('l'),
                                                       typ='core')),
            vars=['dataset_license'],
            prel=prel)

    def license(self):
        return Clause(
            MATCH=Template("OPTIONAL MATCH "
                           "($pvar$labels)-[:has_license|license]->(l:License)"),
            WITH="collect (%s) as license"
                 % roll_node_map(var='l',
                                 typ='core',
                                 d=roll_license_return_dict('l')),
            vars=['license'])

    def dataset_counts(self):
        return Clause(
            MATCH=Template("OPTIONAL MATCH ($pvar)<-[:has_source]-(i:Individual)"
                           " WITH  "
                           "i, $v OPTIONAL MATCH (i)-[:INSTANCEOF]-(c:Class)"),
            WITH="DISTINCT { images: count(distinct i),"
                 "types: count(distinct c) } as dataset_counts",
            vars=['dataset_counts']
        )


class QueryLibrary(QueryLibraryCore):

    # Class wrapping TermInfo queries & queries -> results tables.

    ## TermInfo

    def anatomical_ind_term_info(self, short_form: list,
                                 *args,
                                 pretty_print=False,
                                 q_name='Get JSON for Individual'):
        return query_builder(query_labels=['Individual'],
                             query_short_forms=short_form,
                             clauses=[self.term(),
                                      self.dataSet_license(),
                                      self.parents(),
                                      self.relationships(),
                                      self.xrefs(),
                                      self.channel_image(),
                                      self.pub_syn(),
                                      self.def_pubs()
                                      ],
                             q_name=q_name,
                             pretty_print=pretty_print)  # Is Anatomy label sufficient here

    def license_term_info(self, short_form: list,
                          *args,
                          pretty_print=False,
                          q_name='Get JSON for License'):
        return query_builder(query_labels=['License'],
                             query_short_forms=short_form,
                             clauses=[self.term(
                                 return_extensions=roll_license_return_dict('primary'))],
                             q_name=q_name,
                             pretty_print=pretty_print)

    def class_term_info(self, short_form,
                    *args,
                    pretty_print=False,
                    q_name='Get JSON for Class',
                    additional_clauses=None):
        if additional_clauses is None:
            additional_clauses = []
        return query_builder(query_labels=['Class'],
                             query_short_forms=short_form,
                             clauses=[self.term(),
                                      self.parents(),
                                      self.relationships(),
                             #         self.related_individuals(),
                                      self.xrefs(),
                                      self.anatomy_channel_image(),
                                      self.pub_syn(),
                                      self.def_pubs()] + additional_clauses,
                             q_name=q_name,
                             pretty_print=pretty_print)

    def neuron_class_term_info(self, short_form,
                               *args,
                               pretty_print=False,
                               q_name="Get JSON for Neuron Class"):
        return self.class_term_info(short_form, *args,
                                q_name=q_name,
                                pretty_print=pretty_print,
                                additional_clauses=[self.neuron_split()])

    def split_class_term_info(self, short_form,
                              *args,
                              pretty_print=False,
                              q_name="Get JSON for Split Class"):
        return self.class_term_info(short_form, *args,
                                q_name=q_name,
                                pretty_print=pretty_print,
                                additional_clauses=[self.split_neuron()])


    def dataset_term_info(self, short_form: list, *args, pretty_print=False,
                      q_name='Get JSON for DataSet'):
        return query_builder(query_labels=['DataSet'],
                             query_short_forms=short_form,
                             clauses=[self.term(
                                 return_extensions=
                                 roll_dataset_return_dict(
                                     'primary',
                                     typ='core')),
                                 self.anatomy_channel_image(),
                                 self.xrefs(),
                                 self.license(),
                                 self.pubs(),
                                 self.dataset_counts()
                             ],
                             q_name=q_name,
                             pretty_print=pretty_print)

    def pub_term_info(self, short_form: list, *args, pretty_print=False,
                           q_name='Get JSON for pub'):
        return_clause_hack = ", {" \
                             "title: coalesce(([]+primary.title)[0], '') ," \
                             "PubMed: coalesce(([]+primary.PMID)[0], ''), "  \
                             "FlyBase: coalesce(([]+primary.FlyBase)[0], ''), " \
                             "DOI: coalesce(([]+primary.DOI)[0], '') }" \
                             "AS pub_specific_content"

        return query_builder(
            query_short_forms=short_form,
            query_labels=['Individual', 'pub'],
            clauses=[self.term(),
                     self.dataSet_license(prel='has_reference')],
            q_name=q_name,
            pretty_print=pretty_print
        ) + return_clause_hack


    def template_term_info(self, short_form: list, *args, pretty_print=False,
                           q_name='Get JSON for Template'):
        return query_builder(query_labels=['Template'],
                             query_short_forms=short_form,
                             clauses=[self.term(),
                                      self.template_channel(),
                                      self.template_domain(),
                                      self.dataSet_license(),
                                      self.parents(),
                                      self.relationships(),
                                      self.xrefs(),
                                      self.related_individuals()
                                      ],
                             q_name=q_name,
                             pretty_print=pretty_print)

    #

    def anat_2_ep_wrapper(self):
        return Clause(
            MATCH=Template("MATCH (ep:Class:Expression_pattern)<-[ar:overlaps|part_of]-(:Individual)"
                           "-[:INSTANCEOF]->(anat:Class) WHERE anat.short_form in $ssf "
                           "WITH DISTINCT collect(DISTINCT ar.pub) as pubs, anat, ep "
                           "UNWIND pubs as p MATCH (pub:pub { short_form: p}) "),
            WITH="anat, ep, collect(%s) as pubs" % roll_pub_return("pub"),
            vars=['pubs'],
            node_vars=['anat', 'ep'],
            RETURN='%s as anatomy, %s AS expression_pattern' % (roll_min_node_info('anat'), roll_min_node_info('ep')))

    def ep_2_anat_wrapper(self):
        return Clause(
            MATCH=Template("MATCH (ep:Expression_pattern:Class)<-[ar:overlaps|part_of]-(anoni:Individual)"
                           "-[:INSTANCEOF]->(anat:Class) WHERE ep.short_form in $ssf "
                           "WITH  anoni, anat, ar "
                           "OPTIONAL MATCH (p:pub { short_form: ar.pub}) "),
            WITH="anat, anoni, %s AS pub" % roll_pub_return("p"),
            vars=['pub'],
            node_vars=['anoni', 'anat'],
            RETURN='%s AS anatomy' % (roll_min_node_info('anat')))

        # XREFS

    def template_2_datasets_wrapper(self):
        return Clause(MATCH=Template("MATCH (t:Template)<-[:depicts]-(tc:Template)<-"
                                     "[:in_register_with]-(c:Individual)-[:depicts]"
                                     "->(ai:Individual)-[:has_source]->(ds:DataSet) WHERE t.short_form in $ssf"),
                      WITH="distinct ds",
                      vars=[],
                      node_vars=['ds'],
                      RETURN="%s as dataset" % (roll_min_node_info('ds')))

    def all_datasets_wrapper(self):
        return Clause(MATCH=Template("MATCH (ds:DataSet)"),
                      WITH="ds",
                      vars=[],
                      node_vars=['ds'],
                      RETURN="%s as dataset" % (roll_min_node_info('ds')))

    def anat_2_ep_query(self, short_forms, *args, pretty_print=False):
        # we want images of eps (ep, returned by self.anat_2_ep_wrapper())
        aci = self.anatomy_channel_image()
        aci.__setattr__('pvar', 'ep')
        aci.__setattr__('limit', '')
        return query_builder(query_labels=['Class'],
                             query_short_forms=short_forms,
                             clauses=[self.anat_2_ep_wrapper(),
                                      aci],
                             q_name='Get JSON for anat_2_ep query',
                             pretty_print=pretty_print)

    def ep_2_anat_query(self, short_forms, *args, pretty_print=False):
        # columns: anatomy,
        aci = self.anatomy_channel_image()
        # We want images of anat, returned by self.anat_2_ep_wrapper())
        aci.__setattr__('pvar', 'anat')
        # Add Synaptic neuropil restriction
        aci.__setattr__('starting_labels', ['Synaptic_neuropil'])
        # Return relationship on anoni
        rel = self.ep_stage()
        rel.__setattr__('pvar', 'anoni')

        return query_builder(query_labels=['Class'],
                             query_short_forms=short_forms,
                             clauses=[self.ep_2_anat_wrapper(),
                                      rel,
                                      aci],
                             q_name='Get JSON for ep_2_anat query',
                             pretty_print=pretty_print)

    def template_2_datasets_query(self, short_form):
        aci = self.anatomy_channel_image()
        aci.__setattr__('pvar', 'ds')
        # In the absence of extra tools available for Neo4j3.n
        # We can't set limits on numbers of images.
        # For this reason, we may have to remove aci from this
        # query for now.  Maybe add counts instead for now?
        pub = self.pubs()
        pub.__setattr__('pvar', 'ds')
        li = self.license()
        li.__setattr__('pvar', 'ds')
        counts = self.dataset_counts()
        counts.__setattr__('pvar', 'ds')
        return query_builder(query_short_forms=[short_form],
                             clauses=[self.template_2_datasets_wrapper(),
                                      aci,  # commenting as too slow w/o limit
                                      pub,
                                      li,
                                      counts])

    def all_datasets_query(self):
        aci = self.anatomy_channel_image()
        aci.__setattr__('pvar', 'ds')
        # In the absence of extra tools available for Neo4j3.n
        # We can't set limits on numbers of images.
        # For this reason, we may have to remove aci from this
        # query for now.  Maybe add counts instead for now?
        pub = self.pubs()
        pub.__setattr__('pvar', 'ds')
        li = self.license()
        li.__setattr__('pvar', 'ds')
        counts = self.dataset_counts()
        counts.__setattr__('pvar', 'ds')
        return query_builder(clauses=[self.all_datasets_wrapper(),
                                      aci, # commenting as too slow w/o limit
                                      pub,
                                      li,
                                      counts])

    def anat_image_query(self, short_forms: List):
        return query_builder(query_short_forms=short_forms,
                             query_labels=['Individual'],
                             clauses=[self.term(),
                                      self.channel_image(),
                                      self.image_type()],
                             q_name='Get JSON for anat image query',
                             pretty_print=True)

    def anat_query(self, short_forms: List):
        return query_builder(query_short_forms=short_forms,
                             query_labels=['Class', 'Anatomy'],
                             clauses=[self.term(),
                                      self.anatomy_channel_image()],
                             q_name='Get JSON for anat query',
                             pretty_print=True)

    def anat_scRNAseq_query(self, short_forms: List):
        return query_builder(query_short_forms=short_forms,
                             query_labels=['Class', 'Anatomy'],
                             clauses=[self.term(), self.anat_cluster_dataset_pubs()],
                             q_name='Get JSON for anat scRNAseq query',
                             pretty_print=True)

    def cluster_expression_query(self, short_forms: List):
        return query_builder(query_short_forms=short_forms,
                             query_labels=['Individual', 'Cluster'],
                             clauses=[self.term(), self.cluster_expression(), self.cluster_anat()],
                             q_name='Get JSON for cluster expression query',
                             pretty_print=True)

def term_info_export(escape=True):
    # Generate a JSON with TermInto queries
    ql = QueryLibrary()
    query_methods = ['anatomical_ind_term_info',
                     'class_term_info',
                     'neuron_class_term_info',
                     'split_class_term_info',
                     'dataset_term_info',
                     'license_term_info',
                     'template_term_info',
                     'pub_term_info']

    out = {}
    for qm in query_methods:
        # This whole approach feels a bit hacky...
        qf = getattr(ql, qm)
        q_name = qf.__kwdefaults__['q_name']
        q = qf(short_form='[$id]')
        if escape:
            out[q_name] = '&quot;statement&quot;: &quot;' + q.replace('  ',' ').replace('<','&lt;').replace('\n',' ').replace('  ',' ') + '&quot;, &quot;parameters&quot; : { &quot;id&quot; : &quot;$ID&quot; }'
        else:
            out[q_name] = q
    return json.dumps(out)
