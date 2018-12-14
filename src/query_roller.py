from collections import namedtuple
from string import Template

opm = namedtuple("opm", ["MATCH", "var", "RETURN"])


class QueryGenerator(object):

    def __init__(self):

        ### Notes:
        ###  queries have are all scoped to the object
        ###  parts of queries are scoped to __init__
        ###  Queries are all opm objects
        ###  opm.MATCH = MATCH CLAUSE
        ###  opm.RETURN = *contents* of return/with CLAUSE
        ###  specific to this query
        ###  var = name of variable(s) returned by return clause.
        ###  If more than one separate by ','
        ###  the value of 'var' is used to specify an element of the WITH string between clauses.
        ###  LIMIT = False OR explicit additional WITH clause
        ###  specifying limit to number of results returned.
        ###  This WITH clause will be used as a filter before
        ###  the WITH/RETURN clause.

        self.xrefs = opm(
            MATCH=Template("OPTIONAL MATCH (s:Site)<-[dbx:hasDbXref]-(primary) "),
            RETURN="CASE WHEN s IS NULL THEN [] ELSE COLLECT"
                   "({ link: s.link_base + coalesce(dbx.accession, ''), link_text: s.label, "
                   "site: %s, icon: coalesce(s.link_icon_url, '') }) END AS xrefs" % self.roll_min_node_info("s"),
            var="xrefs")

        self.parents = opm(var="parents",
                           MATCH=Template("OPTIONAL MATCH (o:Class)<-[r:SUBCLASSOF|INSTANCEOF]-(primary) "),
                           RETURN="CASE WHEN o IS NULL THEN [] ELSE COLLECT (%s) END AS parents " % self.roll_min_node_info(
                               "o"))  # Draft

        self.relationships = (opm(var="relationships",
                                  MATCH=Template("OPTIONAL MATCH (o)<-[r { type: 'Related' }]-(primary)"),
                                  RETURN="CASE WHEN o IS NULL THEN [] ELSE COLLECT ({ relation: %s, object: %s }) "
                                         "END AS relationships " % (self.roll_min_edge_info("r"),
                                                                    self.roll_min_node_info("o"))))

        self.related_individuals = (opm(var="related_individuals",
                                        MATCH=Template(
                                            "OPTIONAL MATCH (o:Individual)<-[r { type: 'Related' }]-(primary)"),
                                        RETURN="CASE WHEN o IS NULL THEN [] ELSE COLLECT "
                                               "({ relation: %s, object: %s }) "
                                               "END AS related_individuals " % (self.roll_min_edge_info("r"),
                                                                                self.roll_min_node_info("o"))))

        channel_image_match = "<-[:depicts]-" \
                              "(channel:Individual)-[irw:in_register_with]->(template:Individual)-[:depicts]->" \
                              "(template_anat:Individual) WITH template, channel, template_anat, irw, $v %s limit 5 " \
                              "OPTIONAL MATCH (channel)-[:is_specified_output_of]->(technique:Class) "

        self.template_domain = opm(
            MATCH=Template(
                "OPTIONAL MATCH (technique:Class)<-[:is_specified_output_of]"
                "-(channel:Individual)"
                "-[irw:in_register_with]->(template:Individual)-[:depicts]->(primary) "
                "WHERE technique.label = 'computer graphic' "
                "WITH $v, collect ({ channel: channel, irw: irw}) AS painted_domains "
                "UNWIND painted_domains AS pd "
                "MATCH (channel:Individual { short_form: pd.channel.short_form})"
                "-[:depicts]-(ai:Individual)-[:INSTANCEOF]->(c:Class) "),
            RETURN="collect({ anatomical_type: %s ,"
                   " anatomical_individual: %s, folder: pd.irw.folder, "
                   "center: pd.irw.center }) AS template_domains" % (self.roll_min_node_info("c"),
                                                                     self.roll_min_node_info("ai")),
            var="template_domains")

        self.template_channel = opm(
            MATCH=Template(
                "MATCH (channel:Individual)<-[irw:in_register_with]-"
                "(channel:Individual)-[:depicts]->(primary)"),
            RETURN="{ index: coalesce(irw.index, []) + [], extent: irw.extent, center: irw.center, voxel: irw.voxel, "
                   "orientation: irw.orientation, image_folder: irw.folder, "
                   "channel: %s } as template_channel" % self.roll_min_node_info("channel"),
            var="template_channel")

        channel_image_return = "{ channel: %s, imaging_technique: %s," \
                               "image: { template_channel : %s, template_anatomy: %s," \
                               "image_folder: irw.folder, " \
                               "index: coalesce(irw.index, []) + [] }}" % (self.roll_min_node_info('channel'),
                                                                           self.roll_min_node_info('technique'),
                                                                           self.roll_min_node_info('template'),
                                                                           self.roll_min_node_info('template_anat'))

        self.channel_image = opm(
            MATCH=Template("OPTIONAL MATCH (primary)" + channel_image_match % ''),
            RETURN="CASE WHEN channel IS NULL THEN [] ELSE collect (" + channel_image_return + ") END AS channel_image",
            var="channel_image")

        self.anatomy_channel_image = opm(
            MATCH=Template(
                "OPTIONAL MATCH (primary)<-[:has_source|SUBCLASSOF|INSTANCEOF*]-(i:Individual)"
                + channel_image_match % ', i'),  # Hacky sub!
            RETURN="CASE WHEN channel IS NULL THEN [] ELSE COLLECT({ anatomy: %s, channel_image: %s }) " \
                   "END AS anatomy_channel_image " % (
                       self.roll_min_node_info("i"), channel_image_return),
            var="anatomy_channel_image")

        self.term = "{ core: %s, description: coalesce(primary.description, []), " \
                    "comment: coalesce(primary.`annotation-comment`, [])} " \
                    "as term " % (self.roll_min_node_info("primary"))

        pub_return = "{ core: %s, " \
                     "PubMed: coalesce(p.PMID, ''), " \
                     "FlyBase: coalesce(p.FlyBase, ''), DOI: coalesce(p.DOI, '') } " \
                     "" % self.roll_min_node_info("p")  # Draft

        syn_return = "{ label: coalesce(rp.synonym, ''), " \
                     "scope: coalesce(rp.scope, ''), type: coalesce(rp.cat,'') } "  # Dr

        self.def_pubs = opm(MATCH=Template("OPTIONAL MATCH (primary)-[rp:has_reference { typ: 'def'}]->(p:pub) "),
                            RETURN="CASE WHEN p is null THEN [] ELSE collect(" + pub_return + ") END AS def_pubs",
                            var='def_pubs')

        self.pub_syn = opm(MATCH=Template("OPTIONAL MATCH (primary)-[rp:has_reference { typ: 'syn'}]->(p:pub) "),
                           RETURN="CASE WHEN p is null THEN [] ELSE collect({ pub: %s, synonym: %s }) END AS pub_syn"
                                  % (pub_return, syn_return),
                           var='pub_syn')

        self.pub = opm(MATCH=Template("OPTIONAL MATCH (primary)-[rp:has_reference]->(p:pub) "),
                       RETURN="CASE WHEN p is null THEN [] ELSE collect(" + pub_return + ") END AS def_pubs",
                       var='def_pubs')

        dataset_return = "{ core: %s, catmaid_annotation_id: coalesce(ds.catmaid_annotation_id, ''), " \
                         "link: coalesce(ds.dataset_link, '')  }" % (self.roll_min_node_info('ds'))

        license_return = "{ core: %s, " \
                         "icon: coalesce(l.license_logo, ''), link: coalesce(l.license_url, '')} " % (
                             self.roll_min_node_info('l'))

        self.dataSet_license = opm(MATCH=Template("OPTIONAL MATCH (primary)-[:has_source]->(ds:DataSet)"
                                                  "-[:has_license]->(l:License)"),
                                   RETURN="COLLECT ({ dataset: %s, license: %s}) "
                                          "AS dataset_license" % (dataset_return, license_return),
                                   var='dataset_license')

        self.license = opm(MATCH=Template("OPTIONAL MATCH (primary)-[:has_license]->(l:License)"),
                           RETURN="collect (%s) as license" % license_return,
                           var='license')

    def roll_min_node_info(self, var):
        """Rolls core JSON (specifying minimal info about an entity.
        var: the variable name for the entity within this cypher clause."""
        return "{ short_form: %s.short_form, label: %s.label, " \
               "iri: %s.iri, types: labels(%s) } " % (var, var, var, var)

    def roll_min_edge_info(self, var):
        """Rolls core JSON (specifying minimal info about an edge.
        var: the variable name for the edge within this cypher clause."""
        return "{ label: %s.label, " \
               "iri: %s.uri, type: type(%s) } " % (var, var, var)  # short_forms are not present in OLS-PDB

    def roll_query(self, types, clauses, short_form, pretty_print=True):

        """Takes a list of types (Neo4J labels), a short_form
        and a list of clauses (opm objects) and returns a cypher query.
        """
        var_stack = []

        # May need to be more flexible here.  Allow primary query to be passed as arg?
        primary_query = "MATCH (primary:%s {short_form: '%s' })" % (":".join(types), short_form)

        def roll_clause(q, primary="primary"):
            """Rolls a single clause.
            q = opm object specifying clause,
            primary = var name for primary entity match default: 'primary'"""

            # Make an internal copy of var_stack
            # Add primary to this. (Primary should
            # not be on var_stack as we need to keep
            # it out of the final return clause.
            v = list(var_stack)
            v.append(primary)
            vars_string = ", ".join(v)
            delim = " "
            # Output items added to stack in order
            # Will be strung together later with spec' d delim.
            out_list = []
            if pretty_print:
                delim = " \n"
                out_list.append("")  # Adds an extra return
            # MATCH goes first
            out_list.append(q.MATCH.substitute(v=vars_string))  # Multi-clause MATCH statements require vars
            out_list.append("WITH " + q.RETURN + ", " + vars_string)
            out = delim.join(out_list) + delim
            # Update var stack for next round
            if q.var:
                var_stack.append(q.var)
            return out

        q = primary_query

        for c in clauses:
            q += roll_clause(c)

        out = q + "RETURN " + self.term
        if var_stack:
            out += "," + ",".join(var_stack)
        return out

    def anatomical_ind_query(self, short_form, pretty_print=False):
        return self.roll_query(types=['Individual', 'Anatomy'],
                               short_form=short_form,
                               clauses=[self.parents,
                                        self.relationships,
                                        self.xrefs,
                                        self.channel_image,
                                        self.related_individuals],
                               pretty_print=pretty_print)  # Is Anatomy label sufficient here

    def class_query(self, short_form, pretty_print=False):
        return self.roll_query(types=['Class', 'Anatomy'],
                               short_form=short_form,
                               clauses=[self.parents,
                                        self.relationships,
                                        self.xrefs,
                                        self.channel_image,
                                        self.pub_syn,
                                        self.def_pubs],
                               pretty_print=pretty_print)

    def data_set_query(self, short_form, pretty_print=False):
        return self.roll_query(types=['DataSet'],
                               short_form=short_form,
                               clauses=[self.anatomy_channel_image,
                                        self.xrefs,
                                        self.license,
                                        self.pub],
                               pretty_print=pretty_print)

    def template_query(self, short_form, pretty_print=False):
        return self.roll_query(types=['Template'],
                               short_form=short_form,
                               clauses=[self.template_channel,
                                        self.template_domain,
                                        self.license],
                               pretty_print=pretty_print)

# Really need an edge property that distinguishes logical from annotation properties!
# TODO - Add retain related property to edge flipping code.Nico to add to V2.
