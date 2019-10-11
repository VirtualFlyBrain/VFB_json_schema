from dataclasses import dataclass, field
from typing import List
from string import Template
import subprocess
from xml.sax import saxutils
import json

def get_version_tag():
    tag = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'])
    return tag.decode(encoding = 'ascii').rstrip()


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
        3. Any MATCH statement my consist of multiple whole cypher clauses (MATCH  + WITH)
          In this case, each internal WITH clause must have a $v for interpolation of
          accumulated vars

    MATCH: A cypher (OPTIONAL) MATCH clause. This must be a Template instance.
    It *may* contain references to interpolation vars, specified by clause attributes:
        $labels: labels of primary matched term.  Can be used to modify
                 labels of $pvar$labels in other clauses in order
                 to further restrict.
        $pvar$labels: pvar;
        $ssf: starting short forms
        $v: vars
    WITH: A cypher string that converts variable output of the MATCH
          statement into one or more data structures (strings, lists or maps),
          each bound to a variable name.  These variable names must be
          referenced in vars.
    vars: a list of variable names for data structures in with statement.
          These will be interpolated into subsequent clauses and the return statement
    node_vars: a list of variables returned by the MATCH statement,
              referring to whole nodes, to be interpolated
               into subsequent clauses.
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
                                   limit=self.limit),
             'WITH ' + ','.join([self.WITH] + varz)])


def query_builder(clauses: List[Clause], query_short_forms=None,
                  query_labels=None, pretty_print=True, annotate = True, q_name = ''):
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
           "iri: %s.iri, types: labels(%s) } " % (var, var, var, var)


def roll_min_edge_info(var):
    """Rolls core JSON (specifying minimal info about an edge.
    var: the variable name for the edge within this cypher clause."""
    return "{ label: %s.label, " \
           "iri: %s.uri, type: type(%s) } " % (var, var, var)  # short_forms are not present in OLS-PDB



def roll_license_return_dict(var):
    return {'icon' :  "coalesce(%s.license_logo, '')" % var,
        'link' : "coalesce(%s.license_url, '')" % var}

def roll_dataset_return_dict(var, typ = ''):
    return  {
        "link": "coalesce(%s.dataset_link, '')" % var
    }

def roll_pub_return(var):
    s = Template("{ core: $core, "
                 "PubMed: coalesce($v.PMID, ''), "
                 "FlyBase: coalesce($v.FlyBase, ''), DOI: coalesce($v.DOI, '') }")
    return s.substitute(core=roll_min_node_info(var), v=var)

def roll_node_map(var: str, d: dict, typ = ''):
    if typ:
        if typ =='core':
            d.update({ 'core': roll_min_node_info(var)})
        elif typ == 'extended_core':
            d.update({ 'core': roll_min_node_info(var),
                       'description': 'coalesce(%s.description, [])' % var,
                       "comment": "coalesce(%s.`annotation - comment`, [])" % var
                    })

        else:
            raise Exception('Unknown type: %s should be one or core, extended_core' % typ)
    return '{ ' + ', '.join([' : '.join(kv) for kv in d.items()]) + ' }'

class QueryLibrary:

    # Using class to wrap for convenience. Could do the same with a set of static methods.

    def __init__(self):

        # Using methods for ease of reading code - so these can be next to queries where they apply.
        self._set_image_query_common_elements()
        self._set_pub_common_query_elements()
        self.dataset_spec_fields = {
        "link": "coalesce(%s.dataset_link, '')"
    }
        self.license_spec_fields = {'icon' :  "coalesce(%s.license_logo, '')",
        'link' : "coalesce(%s.license_url, '')x"}

    def term(self, return_extensions = None):
        if return_extensions is None:
          return_extensions = {}
        return Clause(
            MATCH=Template("MATCH (primary$labels) WHERE primary.short_form in $ssf "),
            WITH='primary',
            node_vars=['primary'],
            RETURN= roll_node_map(
                d = return_extensions,
                typ='extended_core',
                var = 'primary') + " AS term")

    # EXPRESSION QUERIES

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

    def xrefs(self):
        match_self_xref = "OPTIONAL MATCH (s:Site { short_form: primary.self_xref }) "
        match_ext_xref = "OPTIONAL MATCH (s:Site)<-[dbx:hasDbXref]-($pvar$labels) "

        xr = "CASE WHEN s IS NULL THEN %s ELSE COLLECT" \
             "({ link_base: s.link_base, " \
             "accession: coalesce(%s, ''), " \
             "link_text: primary.label + ' on ' + s.label, " \
             "site: %s, icon: coalesce(s.link_icon_url, ''),  " \
             "link_postfix: coalesce(s.link_postfix, '')}) " # Should be $pvar$labels not primary, but need sub on WITH!
        xrs = "END AS self_xref, $v"  # Passing vars
        xrx = "+ self_xref END AS xrefs"

        return Clause(
            MATCH=Template(' '.join([match_self_xref, "WITH", xr, xrs, match_ext_xref])
                           % ('[]','primary.short_form',
                              roll_min_node_info("s"))),
            WITH='  '.join([xr, xrx]) % ('self_xref',
                                         'dbx.accession',
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
                                     "image_folder: irw.folder, " \
                                     "index: coalesce(irw.index, []) + [] }" \
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

    def anatomy_channel_image(self):
        return Clause(
            MATCH=Template(
                "OPTIONAL MATCH ($pvar$labels)<-"
                "[:has_source|SUBCLASSOF|INSTANCEOF*]-(i:Individual)"
                + self._channel_image_match % ', i'),  # Hacky sub!
            WITH="CASE WHEN channel IS NULL THEN [] " \
                 "ELSE COLLECT({ anatomy: %s, channel_image: %s }) " \
                 "END AS anatomy_channel_image " % (
                 roll_min_node_info("i"), self._channel_image_return),
            vars=["anatomy_channel_image"],
            limit='limit 5')


    def template_domain(self):  return Clause(
    MATCH=Template(
        "OPTIONAL MATCH (technique:Class)<-[:is_specified_output_of]"
        "-(channel:Individual)"
        "-[irw:in_register_with]->(template:Individual)-[:depicts]->($pvar$labels) "
        "WHERE has(irw.index) "
        "WITH $v, collect ({ channel: channel, irw: irw}) AS painted_domains "
        "UNWIND painted_domains AS pd "
        "MATCH (channel:Individual { short_form: pd.channel.short_form})"
        "-[:depicts]-(ai:Individual)-[:INSTANCEOF]->(c:Class) "),
    WITH="collect({ anatomical_type: %s ,"
         " anatomical_individual: %s, folder: pd.irw.folder, "
         "center: coalesce (pd.irw.center, []), "
         "index: [] + coalesce (pd.irw.index, []) })"
         " AS template_domains" % (roll_min_node_info("c"),
                                   roll_min_node_info("ai")),
    vars=["template_domains"])


    def template_channel(self):  return Clause(
    MATCH=Template(
        "MATCH (channel:Individual)<-[irw:in_register_with]-"
        "(channel:Individual)-[:depicts]->($pvar$labels)"),
    WITH="{ index: coalesce(irw.index, []) + [], "
         "extent: irw.extent, center: irw.center, voxel: irw.voxel, "
         "orientation: irw.orientation, image_folder: irw.folder, "
         "channel: %s } as template_channel" % roll_min_node_info("channel"),
    vars=["template_channel"])

    ## PUBS

    def _set_pub_common_query_elements(self):
        # This is only a function for ease of code editing - places declaration next to where it is used.
        self._pub_return = "{ core: %s, " \
                           "PubMed: coalesce(p.PMID, ''), " \
                           "FlyBase: coalesce(p.FlyBase, ''), DOI: coalesce(p.DOI, '') } " \
                           "" % roll_min_node_info("p")

        self._syn_return = "{ label: coalesce(rp.synonym, ''), " \
                           "scope: coalesce(rp.scope, ''), type: coalesce(rp.cat,'') } "


    def def_pubs(self):  return Clause(MATCH=Template("OPTIONAL MATCH ($pvar$labels)-"
                                                      "[rp:has_reference { typ: 'def'}]->(p:pub) "),
                                       WITH="CASE WHEN p is null THEN "
                                            "[] ELSE collect(" + self._pub_return + ") END AS def_pubs",
                                       vars=['def_pubs'])

    def pub_syn(self):  return Clause(MATCH=Template("OPTIONAL MATCH ($pvar$labels)-"
                                                     "[rp:has_reference { typ: 'syn'}]->(p:pub) "),
                                      WITH="CASE WHEN p is null THEN [] "
                                           "ELSE collect({ pub: %s, synonym: %s }) END AS pub_syn"
                                           % (self._pub_return, self._syn_return),
                                      vars=['pub_syn'])

    def pub(self):  return Clause(MATCH=Template("OPTIONAL MATCH ($pvar$labels)"
                                                 "-[rp:has_reference]->(p:pub) "),
                                  WITH="CASE WHEN p is null THEN [] ELSE "
                                       "collect(" + self._pub_return + ") END AS def_pubs",
                                  vars=['def_pubs'])

    def neuron_split(self):
        return Clause(
            MATCH=Template("OPTIONAL MATCH (:Class { label: 'intersectional expression pattern'})"
                           "<-[:SUBCLASSOF]-(ep:Class)<-[ar:part_of]-(anoni:Individual)"
                           "-[:INSTANCEOF]->($pvar)"),
            WITH="COLLECT(%s) as targeting_splits" % roll_min_node_info("ep"),
            vars=['targeting_splits'])

    def split_neuron(self):
        return Clause(
            MATCH=Template("OPTIONAL MATCH (:Class { label: 'intersectional expression pattern'})"
                           "<-[:SUBCLASSOF]-($pvar)<-[ar:part_of]-(anoni:Individual)"
                           "-[:INSTANCEOF]->(n:Neuron)"),
            WITH="COLLECT(%s) as target_neurons" % roll_min_node_info("n"),
            vars=['target_neurons'])


    def dataSet_license(self):
        return Clause(
            MATCH=Template("OPTIONAL MATCH "
                           "($pvar$labels)-[:has_source]->(ds:DataSet)"
                            "-[:has_license]->(l:License)"),
            WITH="COLLECT ({ dataset: %s, license: %s}) "
                  "AS dataset_license" % (roll_node_map(var = 'ds',
                                                        d=roll_dataset_return_dict('ds'),
                                                        typ='core'),
                                          roll_node_map(var = 'l',
                                                        d=roll_license_return_dict('l'),
                                                        typ='core')),
            vars=['dataset_license'])

    def license(self):
        return Clause(
            MATCH=Template("OPTIONAL MATCH "
                           "($pvar$labels)-[:has_license]->(l:License)"),
            WITH="collect (%s) as license" % roll_node_map(var = 'l',
                                                           typ='core',
                                                           d = roll_license_return_dict('l')),
            vars=['license'])

    # COMPOUND QUERIES

    def anatomical_ind_query(self, short_form,
                             *args,
                             pretty_print=False,
                             q_name='Get JSON for Individual:Anatomy'):

        return query_builder(query_labels=['Individual', 'Anatomy'],
                             query_short_forms=[short_form],
                             clauses=[self.term(),
                                      self.dataSet_license(),
                                      self.parents(),
                                      self.relationships(),
                                      self.xrefs(),
                                      self.channel_image(),
                                      self.related_individuals()],
                             q_name=q_name,
                             pretty_print=pretty_print)  # Is Anatomy label sufficient here

    def license_query(self, short_form,
                      *args,
                      pretty_print=False,
                      q_name='Get JSON for License'):
        return query_builder(query_labels=['License'],
                             query_short_forms=[short_form],
                             clauses=[self.term(
                                return_extensions=roll_license_return_dict('primary'))],
                             q_name=q_name,
                             pretty_print=pretty_print)

    def class_query(self, short_form,
                    *args,
                    pretty_print=False,
                    q_name='Get JSON for Class',
                    additional_clauses=None):
        if additional_clauses is None:
            additional_clauses = []
        return query_builder(query_labels=['Class'],
                             query_short_forms=[short_form],
                             clauses=[self.term(),
                                      self.parents(),
                                      self.relationships(),
                                      self.related_individuals(),
                                      self.xrefs(),
                                      self.anatomy_channel_image(),
                                      self.pub_syn(),
                                      self.def_pubs()] + additional_clauses,
                             q_name=q_name,
                             pretty_print=pretty_print)

    def neuron_class_query(self, short_form,
                    *args,
                    pretty_print=False,
                    q_name="Get JSON for Neuron Class"):
        return self.class_query(short_form, *args,
                                q_name=q_name,
                                pretty_print=pretty_print,
                                additional_clauses=[self.neuron_split()])

    def split_class_query(self, short_form,
                    *args,
                    pretty_print=False,
                    q_name="Get JSON for Split Class"):
        return self.class_query(short_form, *args,
                                q_name=q_name,
                                pretty_print=pretty_print,
                                additional_clauses=[self.split_neuron()])

    def dataset_query(self, short_form, *args, pretty_print=False,
                      q_name='Get JSON for DataSet'):
        return query_builder(query_labels=['DataSet'],
                             query_short_forms=[short_form],
                             clauses=[self.term(
                                 return_extensions=
                                     roll_dataset_return_dict(
                                                        'primary',
                                                        typ='core')),
                                    self.anatomy_channel_image(),
                                    self.xrefs(),
                                    self.license(),
                                    self.pub()],
                             q_name=q_name,
                             pretty_print=pretty_print)

    def template_query(self, short_form, *args, pretty_print=False,
                       q_name='Get JSON for Template'):
        return query_builder(query_labels=['Template'],
                             query_short_forms=[short_form],
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

    def ep_2_anat_query(self, short_form, *args, pretty_print=False):
        # columns: anatomy,
        aci = self.anatomy_channel_image()
        # We want images of anat, returned by self.anat_2_ep_wrapper())
        aci.__setattr__('pvar', 'anat')
        # Add Synaptic neuropil restriction
        aci.__setattr__('starting_labels', ['Synaptic_neuropil'])
        # Remove limits on number images returns
        aci.__setattr__('limit', '')
        # Return relationship on anoni
        rel = self.ep_stage()
        rel.__setattr__('pvar', 'anoni')

        return query_builder(query_labels=['Class'],
                             query_short_forms=[short_form],
                             clauses=[self.ep_2_anat_wrapper(),
                                      rel,
                                      aci],
                             q_name='Get JSON for ep_2_anat query',
                             pretty_print=pretty_print)


def term_info_export():
    # Generate a JSON with TermInto queries
    ql = QueryLibrary()
    query_methods = ['anatomical_ind_query',
                     'class_query',
                     'dataset_query',
                     'license_query',
                     'template_query']

    out = {}
    for qm in query_methods:
        # This whole approach feels a bit hacky...
        qf = getattr(ql, qm)
        q_name = qf.__kwdefaults__['q_name']
        q = qf(short_form='$ID')
        out[q_name] = saxutils.escape(q)
    return json.dumps(out)







