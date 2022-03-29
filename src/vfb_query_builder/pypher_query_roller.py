from dataclasses import dataclass, field
from typing import List
from pypher import Pypher, Param, __, create_function, create_statement
import subprocess
import re

empty_str = Param('empty_str', "''")
first_index = Param('first_index', 0)
create_function('labels', {'name': 'labels'})
create_statement('CALL', {'name': 'CALL'})
create_statement('YIELD', {'name': 'YIELD'})


def get_version_tag():
    tag = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'])
    return tag.decode(encoding='ascii').rstrip()


@dataclass
class Clause:
    MATCH: Pypher
    WITH: Pypher
    vars: List[str] = field(default_factory=list)
    RETURN: Pypher = None
    node_vars: List[str] = field(default_factory=list)
    starting_short_forms: list = field(default_factory=list)
    starting_labels: list = field(default_factory=list)
    match_params: dict = field(default_factory=dict)
    with_params: dict = field(default_factory=dict)
    pvar: str = 'primary'
    limit: str = ''
    prel: str = ''

    def get_match(self, varz):
        """Generate a cypher string using the attributes of this clause object,
        interpolating a list of variables specified by the varz arg"""
        clause_params = dict()
        clause_params["pvar"] = self.pvar
        clause_params["v"] = ', '.join(varz)
        clause_params["ssf"] = str(self.starting_short_forms)
        clause_params["labels"] = ':'.join(self.starting_labels)
        clause_params["prel"] = self.prel
        clause_params["limit"] = self.limit

        params = {**self.match_params, **clause_params, **self.MATCH.bound_params}
        return __().raw(inplace_bound_params(str(self.MATCH), params))

    def get_with(self, varz):
        if varz:
            self.WITH.append(__().raw(',' + ','.join(varz)))
        params = {**self.with_params, **self.WITH.bound_params}
        return __().raw(inplace_bound_params(str(self.WITH), params))


def query_builder(clauses: List[Clause], query_short_forms=None,
                  query_labels=None, pretty_print=True, annotate=True, q_name=''):
    """clauses: A list of Clause objects. The first element in the list must be an initial clause.
    Initial clauses must have slot for short_forms """
    if query_labels is None:
        query_labels = []
    clauses[0].starting_short_forms = query_short_forms
    clauses[0].starting_labels = query_labels

    # Stacks
    node_vars = []
    data_vars = []
    return_clauses = [__.RETURN]

    q = Pypher()
    for c in clauses:
        q.append(c.get_match(varz=node_vars + data_vars))
        q.WITH.append(c.get_with(varz=node_vars + data_vars))
        node_vars.extend(c.node_vars)
        data_vars.extend(c.vars)
        if c.RETURN:
            return_clauses.append(c.RETURN)

    if annotate:
        if q_name:
            return_clauses.append(__().raw("'"+q_name+"'").AS(__.query))
        return_clauses.append(__().raw("'" + str(get_version_tag()) + "'").AS(__.version))
    if data_vars:
        return_clauses.append(__().raw(','.join(data_vars)))

    return_clause_count = 0
    for return_clause in return_clauses:
        q.append(return_clause)
        if 0 < return_clause_count < len(return_clauses) - 1:
            q.append(__().raw(","))
        return_clause_count += 1

    cypher = str(q)
    cypher = cypher.replace("`", "")
    return inplace_bound_params(cypher, q.bound_params)


class QueryLibraryCore:

    def __init__(self):
        # Using methods for ease of reading code - so these can be next to queries where they apply.
        self._set_image_query_common_elements()
        self._set_pub_common_query_elements()

    def term(self, return_extensions=None):
        return Clause(
            MATCH=__.MATCH.node('primary', labels='$labels')
                .WHERE.primary.property('short_form').operator('in', Param('ssf', str(''))),
            WITH=__.primary,
            node_vars=['primary'],
            RETURN=roll_node_map(
                base_map=return_extensions,
                typ='extended_core',
                var='primary').append(__.alias(__.term))
        )

    # EXPRESSION QUERIES

    def xrefs(self):
        match_self_xref = __.OptionalMatch.node("s", "Site", short_form=
        __().func("apoc.convert.toList", __.primary.property("self_xref"))[first_index])
        match_ext_xref = __.OptionalMatch.node("s", "Site").rel_in("dbx", "database_cross_reference").node("$pvar",
                                                                                                           "$labels")

        xr = __.CASE.WHEN.s.IS_NULL.THEN(Param("param1", "param1")).ELSE.COLLECT(__.map(
            link_base=__.coalesce(__.s.property('link_base')[first_index], empty_str),
            accession=__.coalesce(Param("accession_param", "accession_param"), empty_str),
            link_text=__.primary.property("label") + __().raw("' on '") + __.s.property("label"),
            homepage=__.coalesce(__.s.property('homepage')[first_index], empty_str),
            site=__().bind_param("site_param", "site_param"),
            icon=__.coalesce(__.s.property('link_icon_url')[first_index], empty_str),
            link_postfix=__.coalesce(__.s.property("link_postfix"), empty_str)
        ))  # Should be $pvar$labels not primary, but need sub on WITH!
        xrs = __.END.AS(__.self_xref).raw(", $v")  # Passing vars
        xrx = __().raw("+").self_xref.END.AS(__.xrefs)

        return Clause(
            MATCH=match_self_xref.append(__.WITH).append(xr.clone()).append(xrs).append(match_ext_xref),
            WITH=xr.clone().append(xrx),
            vars=["xrefs"],
            match_params={"param1": "[]",
                          "accession_param": "primary.short_form",
                          "site_param": roll_min_node_info("s"),
                          },
            with_params={"param1": "self_xref",
                         "accession_param": "dbx.accession[0]",
                         "site_param": roll_min_node_info("s"),
                         }
        )

    # RELATIONSHIPS

    def parents(self): return Clause(vars=["parents"],
                                     MATCH=__.OptionalMatch.node("o", "Class").rel_in("r", ["SUBCLASSOF", "INSTANCEOF"])
                                     .node("$pvar", "$labels"),
                                     WITH=__.CASE.WHEN.o.IS_NULL.THEN([])
                                     .ELSE.COLLECT(__().raw(roll_min_node_info("o"))).END.AS("parents")
                                     )  # Draft

    def relationships(self): return (Clause(vars=["relationships"],
                                            MATCH=__.OptionalMatch.node("o", "Class")
                                            .rel_in("r", "", type=__().raw("'Related'")).node("$pvar", "$labels"),
                                            WITH=__.CASE.WHEN.o.IS_NULL.THEN([])
                                            .ELSE.COLLECT(__.map(
                                                relation=roll_min_edge_info("r"),
                                                object=roll_min_node_info("o")
                                            )).END.AS(__().raw("relationships"))
                                            ))

    def related_individuals(self): return (Clause(vars=["related_individuals"],
                                                  MATCH=__.OptionalMatch.node("o", "Individual")
                                                    .rel_in("r", "", type=__().raw("'Related'")).node("$pvar", "$labels"),
                                                  WITH= __.CASE.WHEN.o.IS_NULL.THEN([])
                                                    .ELSE.COLLECT(__.map(
                                                        relation=roll_min_edge_info("r"),
                                                        object=roll_min_node_info("o")
                                                    )).END.AS(__().raw("related_individuals"))
                                                  ))

    def ep_stage(self):
        return Clause(
            MATCH=__.OptionalMatch.node("$pvar", "$labels").rel_out("r", "Related").node("o", "FBdv"),
            WITH=__.CASE.WHEN.o.IS_NULL.THEN([]).ELSE.COLLECT(__.map(
                relation=roll_min_edge_info("r"),
                object=roll_min_node_info("o")
            )).END.AS(__.stages),
            vars=['stages']
        )

    # IMAGES

    def _set_image_query_common_elements(self):
        # TODO check $v %s $limit
        self._channel_image_match = __().rel_in(labels="depicts").node("channel", "Individual").rel_out("irw",
                                                                                                        "in_register_with") \
            .node("template", "Individual").rel_out(labels="depicts").node("template_anat", "Individual") \
            .WITH(__.template, __.channel, __.template_anat, __.irw, __().raw("$v $param1 $limit")) \
            .OptionalMatch.node("channel").rel_out(labels="is_specified_output_of").node("technique", "Class")
        self._channel_image_return = __.map(
            channel=roll_min_node_info('channel'),
            imaging_technique=roll_min_node_info('technique'),
            image=__.map(
                template_channel=roll_min_node_info('template'),
                template_anatomy=roll_min_node_info('template_anat'),
                image_folder=__.coalesce(__.irw.property('folder')[first_index], empty_str),
                index=__.coalesce(__().func("apoc.convert.toInteger", __.irw.property('index')[first_index]),
                                  __.List()) + __.List()
            )
        )

    def channel_image(self):
        return Clause(
            MATCH=__.OptionalMatch.node("$pvar", "$labels").append(self._channel_image_match.clone()),
            WITH=__.CASE.WHEN.channel.IS_NULL.THEN([])
                .ELSE.COLLECT(self._channel_image_return.clone()).END.AS(__.channel_image),
            match_params={"param1": ""},
            vars=["channel_image"])

    def image_type(self):
        return Clause(
            MATCH=__.OptionalMatch.node("$pvar").rel_out(labels="INSTANCEOF").node("typ", "Class"),
            WITH=__.CASE.WHEN.typ.IS_NULL.THEN([])
                .ELSE.COLLECT(roll_min_node_info('typ').clone()).END.AS(__.types),
        vars=["types"])

    def anatomy_channel_image(self):
        return Clause(
            MATCH=__.CALL.func("apoc.cypher.run", __().raw("'")
                               .WITH(Param("$pvar", ""))
                               .OptionalMatch.node("$pvar", "$labels").rel_in("", "has_source|SUBCLASSOF|INSTANCEOF*")
                               .node("i", "Individual")
                               .rel_in("", "depicts").node("channel", "Individual").rel_out("irw", "in_register_with")
                               .node("template", "Individual").rel_out("", "depicts").node("template_anat",
                                                                                           "Individual")
                               .RETURN(__.template, __.channel, __.template_anat, __.i, __.irw)
                               .Limit(5)
                               .raw("'"), __.map("$pvar:$pvar"))
                .YIELD(__.value.WITH.value.property("template").AS(__.template),
                       __.value.property("channel").AS(__.channel),
                       __.value.property("template_anat").AS(__.template_anat), __.value.property("i").AS(__.i),
                       __.value.property("irw").AS(__.irw), Param("$v", ""))
                .OptionalMatch.node("channel").rel_out(labels="is_specified_output_of").node("technique", "Class"),
            WITH=__.CASE.WHEN.channel.IS_NULL.THEN([])
                .ELSE.COLLECT(__.map(anatomy=roll_min_node_info("i"), channel_image=self._channel_image_return))
                .END.AS(__.anatomy_channel_image),
            vars=["anatomy_channel_image"],
            limit='limit 5, {}) yield value'
        )

    def template_domain(self):  return Clause(
        MATCH=__.OptionalMatch.node("technique", "Class").rel_in(labels="is_specified_output_of")
            .node("channel", "Individual").rel_out("irw", "in_register_with").node("template", "Individual")
            .rel_out(labels="depicts").node("$pvar", "$labels")
            .WHERE(__.technique.property('short_form') == Param("$tsf", "$tsf")).raw("AND").exists(__.irw.property("index"))
            .WITH(__().raw("$v"), __.COLLECT(__.map(channel=__.channel, irw=__.irw))).AS(__.painted_domains)
            .Unwind(__.painted_domains).AS(__.pd)
            .MATCH.node("channel", "Individual", short_form=__.pd.property("channel").property("short_form"))
            .rel(labels="depicts").node("ai", "Individual").rel_out(labels="INSTANCEOF").node("c", "Class"),
        WITH=__.COLLECT(__.map(
                anatomical_type=roll_min_node_info("c"),
                anatomical_individual=roll_min_node_info("ai"),
                folder=__.pd.property("irw").property("folder")[first_index],
                center=__.coalesce(__.pd.property('irw').property('center'), __.List()),
                index=__.List().raw(" + ").coalesce(__.pd.property('irw').property('index'), __.List()),
            )).AS(__.template_domains),
        vars=["template_domains"],
        match_params={"tsf": "'FBbi_00000224'"})

    def template_channel(self):  return Clause(
        MATCH=__.MATCH.node("channel", "Individual").rel_in("irw", "in_register_with").node("channel", "Individual")
                .rel_out(labels="depicts").node("$pvar", "$labels"),
        WITH=__.map(
            index=__.coalesce(__().func("apoc.convert.toInteger", __.irw.property('index')[first_index]), __.List()) + __.List(),
            extent=__.irw.property('extent')[first_index],
            center=__.irw.property('center')[first_index],
            voxel=__.irw.property('voxel')[first_index],
            orientation=__.coalesce(__.irw.property('orientation')[first_index], empty_str),
            image_folder=__.coalesce(__.irw.property('folder')[first_index], empty_str),
            channel=roll_min_node_info("channel")
        ).AS(__.template_channel),
        vars=["template_channel"])

    ## PUBS

    def _set_pub_common_query_elements(self):
        # This is only a function for ease of code editing - places declaration next to where it is used.
        self._pub_return = __.map(
            core=roll_min_node_info("p"),
            PubMed=__.coalesce(__.p.property('PMID')[first_index], empty_str),
            FlyBase=__.coalesce(__.p.property('FlyBase')[first_index], empty_str),
            DOI=__.coalesce(__.p.property('DOI')[first_index], empty_str)
        )

        # temp fixes in here for list -> single !
        self._syn_return = __.map(
            label=__.coalesce(__.rp.property('value')[first_index], empty_str),
            scope=__.coalesce(__.rp.property('scope'), empty_str),
            type=__.coalesce(__.rp.property('has_synonym_type')[first_index], empty_str),
        )

    def def_pubs(self):
        return Clause(
            MATCH=__.OptionalMatch.node("$pvar", "$labels").rel_out("rp", "has_reference").node("p", "pub")
                      .WHERE.rp.property("typ") == __().raw("'def'"),
            WITH=__.CASE.WHEN.p.IS_NULL.THEN([])
                      .ELSE.COLLECT(__().raw(self._pub_return)).END.AS(__.def_pubs),
            vars=['def_pubs'])

    def pub_syn(self):
        return Clause(
            MATCH=__.OptionalMatch.node("$pvar", "$labels").rel_out("rp", "has_reference").node("p", "pub")
                      .WHERE.rp.property("typ") == __().raw("'syn'"),  # tmp fix rp.typ shld be []]!
            WITH=__.CASE.WHEN.p.IS_NULL.THEN([])
                      .ELSE.COLLECT(__.map(
                        pub=self._pub_return,
                        synonym=self._syn_return
            )).END.AS(__.pub_syn),
            vars=['pub_syn'])

    def pubs(self):
        return Clause(
            MATCH=__.OptionalMatch.node("$pvar", "$labels").rel_out("rp", "has_reference").node("p", "pub"),
            WITH=__.CASE.WHEN.p.IS_NULL.THEN([])
                .ELSE.COLLECT(self._pub_return).END.AS(__.pubs),
            vars=['pubs'])

    def neuron_split(self):
        return Clause(
            MATCH=__.OptionalMatch.node(labels="Class", label=__().raw("'intersectional expression pattern'"))
                .rel_in(labels="SUBCLASSOF").node("ep", "Class").rel_in("ar", "part_of").node("anoni", "Individual")
                .rel_out(labels="INSTANCEOF").node("$pvar"),
            WITH=__.CASE.WHEN.ep.IS_NULL.THEN([])
                .ELSE.COLLECT(roll_min_node_info("ep")).END.AS(__.targeting_splits),
            vars=['targeting_splits'])

    def split_neuron(self):
        return Clause(
            MATCH=__.OptionalMatch.node(labels="Class", label=__().raw("'intersectional expression pattern'"))
                .rel_in(labels="SUBCLASSOF").node("$pvar").rel_in("ar", "part_of").node("anoni", "Individual")
                .rel_out(labels="INSTANCEOF").node("n", "Neuron"),
            WITH=__.CASE.WHEN.n.IS_NULL.THEN([])
                .ELSE.COLLECT(roll_min_node_info("n")).END.AS(__.target_neurons),
            vars=['target_neurons'])

    def dataSet_license(self, prel='has_source'):
        return Clause(
            MATCH=__.OptionalMatch.node("$pvar", "$labels").rel(labels="$prel")
                .node("ds", "DataSet").rel_out("", ["has_license", "license"]).node("l", "License"),
            WITH=__.COLLECT(__.map(
                dataset=roll_node_map(var='ds',
                                      base_map=roll_dataset_return_dict('ds'),
                                      typ='core'),
                license=roll_node_map(var='l',
                                      base_map=roll_license_return_dict('l'),
                                      typ='core')
            )).AS(__.dataset_license),
            vars=['dataset_license'],
            prel=prel)

    def license(self):
        return Clause(
            MATCH=__.OptionalMatch.node("$pvar", "$labels").rel_out(labels=["has_license", "license"])
                .node("l", "License"),
            WITH=__.COLLECT(roll_node_map(var='l',
                                          base_map=roll_license_return_dict('l'),
                                          typ='core')
                            ).AS(__.license),
            vars=['license'])

    def dataset_counts(self):
        return Clause(
            MATCH=__.OptionalMatch.node("$pvar").rel_in(labels="has_source").node("i", "Individual")
                .WITH(__.i, __().raw("$v")).OptionalMatch.node("i").rel(labels="INSTANCEOF").node("c", "Class"),
            WITH=__().raw("DISTINCT").map(images=__.count(__.Distinct(__.i)),
                                 types=__.count(__.Distinct(__.c))).AS(__.dataset_counts),
            vars=['dataset_counts']
        )


def roll_license_return_dict(var):
    return __.map(
        icon=__.coalesce(__().raw(var).property('license_logo')[first_index], empty_str),
        link=__.coalesce(__().raw(var).property('license_url')[first_index], empty_str)
    )


# We sometimes need to extend return from term with additional info from other clauses
# For this it helps to contruct return as a dict


def roll_dataset_return_dict(var, typ=''):
    return __.map(
        link=__.coalesce(__().raw(var).property('dataset_link')[first_index], empty_str)
    )


def roll_min_node_info(var):
    """Rolls core JSON (specifying minimal info about an entity.
    var: the variable name for the entity within this cypher clause."""
    return __.map(
        short_form=__().raw(var).property('short_form'),
        label=__.coalesce(__().raw(var).property('label'), empty_str),
        iri=__().raw(var).property('iri'),
        types=__.labels(__().raw(var)),
        symbol=__.coalesce(__().raw(var).property('symbol')[first_index], empty_str)
    )


def roll_min_edge_info(var):
    """Rolls core JSON (specifying minimal info about an edge.
    var: the variable name for the edge within this cypher clause."""
    return __.map(
        label=__().raw(var).property('label'),
        iri=__().raw(var).property('iri'),
        type=__().type(__().raw(var))
    )


def roll_pub_return(var):
    return __.map(
        core=roll_min_node_info(var),
        PubMed=__.coalesce(__().raw(var).property('PMID')[first_index], empty_str),
        FlyBase=__.coalesce(__().raw(var).property('FlyBase')[first_index], empty_str),
        DOI=__.coalesce(__().raw(var).property('DOI')[first_index], empty_str),
    )


def roll_node_map(var: str, base_map=None, typ=''):
    node_map = None
    if typ:
        if typ == 'core':
            node_map = __.map(
                core=roll_min_node_info(var)
            )
        elif typ == 'extended_core':
            node_map = __.map(
                core=roll_min_node_info(var),
                description=__.coalesce(__.primary.property('description'), __.List()),
                comment=__.coalesce(__.primary.property('comment'), __.List()),
            )
        else:
            raise Exception('Unknown type: %s should be one or core, extended_core' % typ)

    return merge_maps(base_map, node_map)


class QueryLibrary(QueryLibraryCore):

    # Class wrapping TermInfo queries & queries -> results tables.

    ## TermInfo

    def anatomical_ind_term_info(self, short_form: list,
                                 *args,
                                 pretty_print=False,
                                 q_name='Get JSON for Individual:Anatomy'):
        return query_builder(query_labels=['Individual', 'Anatomy'],
                             query_short_forms=short_form,
                             clauses=[self.term(),
                                      self.dataSet_license(),
                                      self.parents(),
                                      self.relationships(),
                                      self.xrefs(),
                                      self.channel_image(),
                                      #         self.related_individuals()
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
        return_clause_hack = __().raw(", ").map(
            title=__.coalesce(__.primary.property('title')[first_index], empty_str),
            PubMed=__.coalesce(__.primary.property('PMID')[first_index], empty_str),
            FlyBase=__.coalesce(__.primary.property('FlyBase')[first_index], empty_str),
            DOI=__.coalesce(__.primary.property('DOI')[first_index], empty_str)
        ).AS(__.pub_specific_content)

        return query_builder(
            query_short_forms=short_form,
            query_labels=['Individual', 'pub'],
            clauses=[self.term(),
                     self.dataSet_license(prel='has_reference')]
        ) + inplace_bound_params(str(return_clause_hack), return_clause_hack.bound_params)

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
            MATCH=__.MATCH.node("ep", "Class:Expression_pattern").rel_in("ar", ["overlaps", "part_of"])
                .node(labels="Individual").rel_out(labels="INSTANCEOF").node("anat", "Class")
                .WHERE.anat.property('short_form').operator('in', Param('ssf', "ssf"))
                .WITH.raw("DISTINCT").Collect(__.Distinct(__.ar.property("pub"))).AS(__.pubs).raw(", ").anat.raw(", ").ep
                .Unwind(__.pubs).AS(__.p)
                .MATCH.node("pub", "pub", short_form=__.p),
            WITH=__.anat.raw(", ").ep.raw(", ").Collect(roll_pub_return("pub")).AS(__.pubs),
            vars=['pubs'],
            node_vars=['anat', 'ep'],
            RETURN=__().append(roll_min_node_info('anat').clone()).AS("anatomy").raw(", ")
                .append(roll_min_node_info('ep').clone()).AS("expression_pattern")
        )

    def ep_2_anat_wrapper(self):
        return Clause(
            # MATCH=Template("MATCH (ep:Expression_pattern:Class)<-[ar:overlaps|part_of]-(anoni:Individual)"
            #                "-[:INSTANCEOF]->(anat:Class) WHERE ep.short_form in $ssf "
            #                "WITH  anoni, anat, ar "
            #                "OPTIONAL MATCH (p:pub { short_form: ar.pub}) "),
            # WITH="anat, anoni, %s AS pub" % roll_pub_return("p"),
            MATCH=__.MATCH.node("ep", "Expression_pattern:Class").rel_in("ar", ["overlaps", "part_of"])
                .node("anoni", "Individual").rel_out(labels="INSTANCEOF").node("anat", "Class")
                .WHERE.ep.property('short_form').operator('in', Param('ssf', "ssf"))
                .WITH(__.anoni, __.anat, __.ar)
                .OptionalMatch.node("p", "pub", short_form=__.ar.property("pub")),
            WITH=__.anat.raw(", ").anoni.raw(", ").append(roll_pub_return("p").clone()).AS(__.pub),
            vars=['pub'],
            node_vars=['anoni', 'anat'],
            RETURN=__().append(roll_min_node_info('anat').clone()).AS("anatomy")
        )

        # XREFS

    def template_2_datasets_wrapper(self):
        return Clause(MATCH=__.MATCH.node("t", "Template").rel_in("depicts").node("tc", "Template")
                          .rel(labels="in_register_with").node("c", "Individual").rel_out(labels="depicts")
                          .node("ai", "Individual").rel_out(labels="has_source").node("ds", "DataSet")
                          .WHERE.t.property("short_form").operator('in', Param('ssf', "ssf")),
                      WITH=__().raw("DISTINCT").ds,
                      vars=[],
                      node_vars=['ds'],
                      RETURN=__().append(roll_min_node_info('ds').clone()).AS("dataset")
                      )

    def all_datasets_wrapper(self):
        return Clause(
            MATCH=__.MATCH.node("ds", "DataSet"),
            WITH=__.ds,
            vars=[],
            node_vars=['ds'],
            RETURN=__().append(roll_min_node_info('ds').clone()).AS("dataset")
        )

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
                             pretty_print=True)

    def anat_query(self, short_forms: List):
        return query_builder(query_short_forms=short_forms,
                             query_labels=['Class', 'Anatomy'],
                             clauses=[self.term(),
                                      self.anatomy_channel_image()],
                             pretty_print=True)


def inplace_bound_params(cypher, params):
    """
    Embeds bound query param values in the query string.

    Return: updated query string
    """
    if "empty_str" not in params:
        params["empty_str"] = "''"
    if "first_index" not in params:
        params["first_index"] = 0
    # cypher = cypher.replace("`$labels`", "$labels")
    for param in params:
        if param == "labels" and not params[param]:
            cypher = handle_empty_labels(cypher)
        cypher = cypher.replace("$" + param, str(params[param]))
    return cypher


def handle_empty_labels(cypher):
    """
    When labels are empty, Pypher generates a faulty definition like "(node_name:'')".
    This function removes ":''" strings to fix this problem and conclude with "(node_name)".
    """
    all_label_indexes = [m.start() for m in re.finditer('\$labels', cypher)]
    for label_index in all_label_indexes:
        semicolon_index = cypher.find(":", label_index - 2, label_index)
        if semicolon_index >= 0:
            cypher = cypher[:semicolon_index] + cypher[label_index + len("$labels"):]
    return cypher


def merge_maps(map1, map2):
    """
    Pypher does not have a map merge or dynamic map generation function.
    So merging given maps with string operations.
    """
    if not map1:
        return map2
    if not map2:
        return map1
    map1_str = inplace_bound_params(str(map1), map1.bound_params)
    map2_str = inplace_bound_params(str(map2), map2.bound_params)
    return __().raw(map1_str[0:map1_str.rfind("}")] + ", " + map2_str[map2_str.find("{") + 1:len(map2_str)])
