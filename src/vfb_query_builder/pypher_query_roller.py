from dataclasses import dataclass, field
from typing import List
from pypher import Pypher, Param, __, create_function, create_statement
import subprocess


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

        params = {**self.match_params, **clause_params}
        return __().raw(inplace_bound_params(str(self.MATCH), params))

    def get_with(self, varz):
        if varz:
            self.WITH.append(__().raw(',' + ','.join(varz)))
        return __().raw(inplace_bound_params(str(self.WITH), self.with_params))


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
            return_clauses.append(__().raw(q_name).AS(__.query))
        return_clauses.append(__().raw("'" + str(get_version_tag()) + "'").AS(__.version))
    return_clauses.append(__().raw(','.join(data_vars)))

    return_clause_count = 0
    for return_clause in return_clauses:
        q.append(return_clause)
        if 0 < return_clause_count < len(return_clauses)-1:
            q.append(__().raw(","))
        return_clause_count += 1

    return inplace_bound_params(str(q), q.bound_params)


class QueryLibraryCore:

    def __init__(self):
        # Using methods for ease of reading code - so these can be next to queries where they apply.
        self._set_image_query_common_elements()
        self._set_pub_common_query_elements()

    def term(self):
        return Clause(
            MATCH=__.MATCH.node('primary', labels='$labels')
                    .WHERE.primary.property('short_form').operator('in', Param('ssf', str(''))),
            WITH=__.primary,
            node_vars=['primary'],
            RETURN=roll_node_map(
                typ='extended_core',
                var='primary').append(__.alias(__.term))
        )

    # EXPRESSION QUERIES

    def xrefs(self):
        match_self_xref = __.OptionalMatch.node("s", "Site", short_form=
                            __().func("apoc.convert.toList", __.primary.property("self_xref"))[first_index])
        match_ext_xref = __.OptionalMatch.node("s", "Site").rel_in("dbx", "database_cross_reference").node("$pvar", "$labels")

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
                                     MATCH=__.OptionalMatch.node("o", "Class").rel_in("r", "SUBCLASSOF|INSTANCEOF")
                                     .node("$pvar", "$labels"),
                                     WITH=__.CASE.WHEN.o.IS_NULL.THEN([])
                                     .ELSE.COLLECT(__().raw(roll_min_node_info("o"))).END.AS("parents")
                                     )  # Draft

    def relationships(self): return (Clause(vars=["relationships"],
                                            MATCH=__.OptionalMatch.node("o", "Class")
                                            .rel_in("r", "", type=__().raw("'Related'")).node("$pvar", "$labels"),
                                            WITH=__.CASE.WHEN.o.IS_NULL.THEN([])
                                                .ELSE.COLLECT(__.map(
                                                    relation=Param("info_r_param", "info_r_param"),
                                                    object=Param("info_o_param", "info_o_param")
                                                )).END.AS(__().raw("relationships")),
                                            with_params={"info_r_param": roll_min_edge_info("r"),
                                                         "info_o_param": roll_min_node_info("o")
                                                         }
                                            ))

    def test_func(self):
        q = Pypher()
        q + __.self_xref.END.AS(__.xrefs)
        print(__().raw("") + __.self_xref.END.AS(__.xrefs))

    def anatomy_channel_image(self):
        return Clause(
            MATCH=__.CALL.func("apoc.cypher.run", __().raw("'")
                                .WITH(Param("$pvar", ""))
                                .OptionalMatch.node("$pvar", "$labels").rel_in("", "has_source|SUBCLASSOF|INSTANCEOF*")
                                .node("i", "Individual")
                                .rel_in("", "depicts").node("channel", "Individual").rel_out("irw", "in_register_with")
                                .node("template", "Individual").rel_out("", "depicts").node("template_anat", "Individual")
                                .RETURN(__.template, __.channel, __.template_anat, __.i, __.irw)
                                .Limit(5)
                                .raw("'"), __.map("$pvar:$pvar"))
            .YIELD(__.value.WITH.value.property("template").AS(__.template), __.value.property("channel").AS(__.channel),
                   __.value.property("template_anat").AS(__.template_anat), __.value.property("i").AS(__.i),
                   __.value.property("irw").AS(__.irw), Param("$v", ""))
            .OptionalMatch.node("channel").rel_out(labels="is_specified_output_of").node("technique", "Class"),
            WITH=__.CASE.WHEN.channel.IS_NULL.THEN([])
                .ELSE.COLLECT(__.map(anatomy=roll_min_node_info("i"), channel_image=self._channel_image_return))
                .END.AS(__.anatomy_channel_image),
            vars=["anatomy_channel_image"],
            limit='limit 5, {}) yield value'
        )

    def _set_image_query_common_elements(self):
        # TODO check $v %s $limit
        self._channel_image_match = __().rel_in(labels="depicts").node("channel", "Individual").rel_out("irw", "in_register_with")\
            .node("template", "Individual").rel_out(labels="depicts").node("template_anat", "Individual")\
            .WITH(__.template, __.channel, __.template_anat, __.irw, __().raw("$v $param1 $limit"))\
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
            scope=__.coalesce(__.rp.property('scope')[first_index], empty_str),
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


class QueryLibrary(QueryLibraryCore):
    pass


def inplace_bound_params(cypher, params):
    """
    Embeds bound query param values in the query string.

    Return: updated query string
    """
    for param in params:
        cypher = cypher.replace("$" + param, str(params[param]))
    return cypher


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


def roll_node_map(var: str, typ=''):
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
    return node_map
