from dataclasses import dataclass, field
from typing import List
from string import Template


## Spec:

## First clause is always a match on one or more short_forms - so we need a way to sub these.
## First clause may include passed neo labels - so we need a way to sub these.
## First clause WITH will include at least one node var


@dataclass
class Clause:
    MATCH: Template
    WITH: str
    vars: List[str] = field(default_factory=list)
    RETURN: str = ''
    node_vars: List[str] = field(default_factory=list)
    starting_short_forms: list = field(default_factory=list)
    starting_labels: list = field(default_factory=list)
    pvar: str = 'primary'

    def get_clause(self, varz, pretty_print=True):
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
                                   labels=':'.join(l)),
             'WITH ' + ','.join([self.WITH] + varz)])


def query_builder(clauses: List[Clause], query_short_forms=None,
                  query_labels=None, pretty_print=True):
    """clauses: A list of Clause object. The first element in the list must be an initial clause.
    Initial clauses must have slot for short_forms indicated with ** """

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

        # Add in some checks to make sure vars don't get stomped

    return_clause = "RETURN " + ', '.join(return_clauses + data_vars)
    out.append(return_clause)
    return sep.join(out)


def roll_min_node_info(var):
    """Rolls core JSON (specifying minimal info about an entity.
    var: the variable name for the entity within this cypher clause."""
    return "{ short_form: %s.short_form, label: %s.label, " \
           "iri: %s.iri, types: labels(%s) } " % (var, var, var, var)


def roll_min_edge_info(var):
    """Rolls core JSON (specifying minimal info about an edge.
    var: the variable name for the edge within this cypher clause."""
    return "{ label: %s.label, " \
           "iri: %s.uri, type: type(%s) } " % (var, var, var)  # short_forms are not present in OLS-PDB


def roll_pub_return(var):
    s = Template("{ core: $core, "
                 "PubMed: coalesce($v.PMID, ''), "
                 "FlyBase: coalesce($v.FlyBase, ''), DOI: coalesce($v.DOI, '') }")
    return s.substitute(core=roll_min_node_info(var), v=var)


class QueryLibrary:

    def __init__(self):
        self._dataset_return = "{ core: %s, catmaid_annotation_id: " \
                               "coalesce(ds.catmaid_annotation_id, ''), " \
                               "link: coalesce(ds.dataset_link, '')  }" \
                               % (roll_min_node_info('ds'))

        self._license_return = "{ core: %s, " \
                               "icon: coalesce(l.license_logo, ''), " \
                               "link: coalesce(l.license_url, '')} " % (
                                   roll_min_node_info('l'))

        self._channel_image_match = "<-[:depicts]-" \
                                    "(channel:Individual)-[irw:in_register_with]" \
                                    "->(template:Individual)-[:depicts]->" \
                                    "(template_anat:Individual) WITH template" \
                                    ", channel, template_anat, irw, $v %s limit 5 " \
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

        self._pub_return = "{ core: %s, " \
                           "PubMed: coalesce(p.PMID, ''), " \
                           "FlyBase: coalesce(p.FlyBase, ''), DOI: coalesce(p.DOI, '') } " \
                           "" % roll_min_node_info("p")  # Draft

        self._syn_return = "{ label: coalesce(rp.synonym, ''), " \
                           "scope: coalesce(rp.scope, ''), type: coalesce(rp.cat,'') } "

    def term(self):
        return Clause(
            MATCH=Template("MATCH (primary$labels) WHERE primary.short_form in $ssf "),
            WITH='primary',
            node_vars=['primary'],
            RETURN="{ core: %s, description: coalesce(primary.description, []), " \
                   "comment: coalesce(primary.`annotation-comment`, [])} " \
                   "AS term" % (roll_min_node_info("primary")))

    def anat_2_ep_wrapper(self):
        return Clause(
            MATCH=Template("MATCH (ep$labels)<-[ar:overlaps|part_of]-(:Individual)"
                           "-[:INSTANCEOF]->(anat:Class) WHERE anat.short_form in $ssf "
                           "WITH DISTINCT collect(ar.pub) as pubs, anat "
                           "UNWIND pubs as p MATCH (pub:pub { short_form: p}) "),
            WITH="anat, collect(%s) as pns" % roll_pub_return("pub"),
            vars=['pns'],
            node_vars=['anat'],
            RETURN='%s as anatomy' % roll_min_node_info('anat'))

    def ep_2_anat_wrapper(self):
        return Clause(
            MATCH=Template("MATCH (ep:Expression_pattern)-[ar:overlaps|has_part]"
                           "-(i:Individual)-[:INSTANCEOF]->(a:Class)"
                           "WITH  i, a, ep, er "
                           "OPTIONAL MATCH (p:pub { short_form: ar.pub}) ") ,
            WITH="i, ep, %s as anat, %s as pub" % (roll_min_node_info('anat'), roll_pub_return("pub")),
            vars=['anat', 'pub'],
            node_vars=['i', 'ep'],
            RETURN='%s AS expression_pattern' % (roll_min_node_info('ep')))

    # Re-use relationship?
    def ep_stage(self):
        return Clause(
            MATCH=Template("OPTIONAL MATCH (i)-[sr:Related]->(s:FBdv)"),
            WITH="collect({ term: %s, rel: %s } AS "
        )





    def xrefs(self):  return Clause(
        MATCH=Template("OPTIONAL MATCH (s:Site)<-[dbx:hasDbXref]-($pvar) "),
        WITH="CASE WHEN s IS NULL THEN [] ELSE COLLECT"
             "({ link: s.link_base + coalesce(dbx.accession, ''), link_text: s.label, "
             "site: %s, icon: coalesce(s.link_icon_url, '') }) END AS xrefs" % roll_min_node_info("s"),
        vars=["xrefs"])

    def parents(self):  return Clause(vars=["parents"],
                                      MATCH=Template("OPTIONAL MATCH (o:Class)"
                                                     "<-[r:SUBCLASSOF|INSTANCEOF]-($pvar) "),
                                      WITH="CASE WHEN o IS NULL THEN [] ELSE COLLECT "
                                           "(%s) END AS parents " % roll_min_node_info("o"))  # Draft

    def relationships(self): return  (Clause(vars=["relationships"],
                                      MATCH=Template("OPTIONAL MATCH "
                                                     "(o)<-[r {type:'Related'}]-($pvar)"),
                                      WITH="CASE WHEN o IS NULL THEN [] "
                                           "ELSE COLLECT ({ relation: %s, object: %s }) "
                                           "END AS relationships " % (roll_min_edge_info("r"),
                                                                      roll_min_node_info("o"))))

    def related_individuals(self): return  (Clause(vars=["related_individuals"],
                                            MATCH=Template(
                                                "OPTIONAL MATCH "
                                                "(o:Individual)<-[r {type:'Related'}]-($pvar)"),
                                            WITH="CASE WHEN o IS NULL THEN [] ELSE COLLECT "
                                                 "({ relation: %s, object: %s }) "
                                                 "END AS related_individuals "
                                                 % (roll_min_edge_info("r"),
                                                    roll_min_node_info("o"))))

    def template_domain(self):  return Clause(
        MATCH=Template(
            "OPTIONAL MATCH (technique:Class)<-[:is_specified_output_of]"
            "-(channel:Individual)"
            "-[irw:in_register_with]->(template:Individual)-[:depicts]->($pvar) "
            "WHERE technique.label = 'computer graphic' "
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
            "(channel:Individual)-[:depicts]->($pvar)"),
        WITH="{ index: coalesce(irw.index, []) + [], "
             "extent: irw.extent, center: irw.center, voxel: irw.voxel, "
             "orientation: irw.orientation, image_folder: irw.folder, "
             "channel: %s } as template_channel" % roll_min_node_info("channel"),
        vars=["template_channel"])

    def channel_image(self):  return Clause(
        MATCH=Template("OPTIONAL MATCH ($pvar)" + self._channel_image_match % ''),
        WITH="CASE WHEN channel IS NULL THEN []"
             " ELSE collect (" + self._channel_image_return + ") END AS channel_image",
        vars=["channel_image"])

    def anatomy_channel_image(self):  return Clause(
        MATCH=Template(
            "OPTIONAL MATCH ($pvar)<-"
            "[:has_source|SUBCLASSOF|INSTANCEOF*]-(i:Individual)"
            + self._channel_image_match % ', i'),  # Hacky sub!
        WITH="CASE WHEN channel IS NULL THEN [] "
             "ELSE COLLECT({ anatomy: %s, channel_image: %s }) " \
             "END AS anatomy_channel_image " % (
                 roll_min_node_info("i"), self._channel_image_return),
        vars=["anatomy_channel_image"])

    def def_pubs(self):  return Clause(MATCH=Template("OPTIONAL MATCH ($pvar)-"
                                                      "[rp:has_reference { typ: 'def'}]->(p:pub) "),
                                       WITH="CASE WHEN p is null THEN "
                                            "[] ELSE collect(" + self._pub_return + ") END AS def_pubs",
                                       vars=['def_pubs'])

    def pub_syn(self):  return Clause(MATCH=Template("OPTIONAL MATCH ($pvar)-"
                                                     "[rp:has_reference { typ: 'syn'}]->(p:pub) "),
                                      WITH="CASE WHEN p is null THEN [] "
                                           "ELSE collect({ pub: %s, synonym: %s }) END AS pub_syn"
                                           % (self._pub_return, self._syn_return),
                                      vars=['pub_syn'])

    def pub(self):  return Clause(MATCH=Template("OPTIONAL MATCH ($pvar)"
                                                 "-[rp:has_reference]->(p:pub) "),
                                  WITH="CASE WHEN p is null THEN [] ELSE "
                                       "collect(" + self._pub_return + ") END AS def_pubs",
                                  vars=['def_pubs'])

    def dataSet_license(self):  return Clause(MATCH=Template("OPTIONAL MATCH "
                                                             "($pvar)-[:has_source]->(ds:DataSet)"
                                                             "-[:has_license]->(l:License)"),
                                              WITH="COLLECT ({ dataset: %s, license: %s}) "
                                                   "AS dataset_license" % (self._dataset_return, self._license_return),
                                              vars=['dataset_license'])

    def license(self):  return Clause(MATCH=Template("OPTIONAL MATCH "
                                                     "($pvar)-[:has_license]->(l:License)"),
                                      WITH="collect (%s) as license" % self._license_return,
                                      vars=['license'])

    def anatomical_ind_query(self, short_form, pretty_print=False):
        return query_builder(query_labels=['Individual', 'Anatomy'],
                             query_short_forms=[short_form],
                             clauses=[self.term(),
                                      self.parents(),
                                      self.relationships(),
                                      self.xrefs(),
                                      self.channel_image(),
                                      self.related_individuals()],
                             pretty_print=pretty_print)  # Is Anatomy label sufficient here

    def class_query(self, short_form, pretty_print=False):
        return query_builder(query_labels=['Class', 'Anatomy'],
                             query_short_forms=[short_form],
                             clauses=[self.term(),
                                      self.parents(),
                                      self.relationships(),
                                      self.xrefs(),
                                      self.channel_image(),
                                      self.pub_syn(),
                                      self.def_pubs()],
                             pretty_print=pretty_print)

    def data_set_query(self, short_form, pretty_print=False):
        return query_builder(query_labels=['DataSet'],
                             query_short_forms=[short_form],
                             clauses=[self.term(),
                                      self.anatomy_channel_image(),
                                      self.xrefs(),
                                      self.license(),
                                      self.pub()],
                             pretty_print=pretty_print)

    def template_query(self, short_form, pretty_print=False):
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
                             pretty_print=pretty_print)

    def ep_2_anat_query(self, short_form, pretty_print=False):
        aci = self.anatomy_channel_image()
        aci.__setattr__('pvar', 'anat')
        return query_builder(query_labels=['Class'],
                             query_short_forms=[short_form],
                             clauses=[self.anat_2_ep_wrapper(),
                                      aci],
                             pretty_print=pretty_print)

    def anat_2_ep_query(self, short_forms, pretty_print=False):

        aci = self.anatomy_channel_image()
        aci.__setattr__('pvar', 'ep')
        rel = self.relationships()
        rel.__setattr__('pvar', 'i')

        return query_builder(query_labels=['Class'],
                             query_short_forms=short_forms,
                             clauses=[self.anat_2_ep_wrapper(),
                                      rel,
                                      aci],
                             pretty_print=pretty_print)



ql = QueryLibrary()

print(ql.ep_2_anat_query('VFBexp_FBtp0040533'))
