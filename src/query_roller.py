from collections import namedtuple


opm = namedtuple("opm", ["MATCH", "var", "RETURN", "LIMIT"])






class QueryGenerator(object):

    def __init__(self):

        ### Assumptions

        pub = "{ pub_core: %s, microref: p.microref, PubMed: p.PMID, " \
              "FlyBase: p.FlyBase, DOI: p.DOI, ISBN: p.ISBN } " % self.roll_core("p")

        synonym = "{ label: rp.synonym, scope: rp.scope, type: rp.cat } "

        self.pub_syn = opm(MATCH="OPTIONAL MATCH (primary)-[rp:has_reference]->(p:pub)",
                           RETURN= "COLLECT ( { pub: %s, synonym: %s } ) AS pub_syn" % (pub, synonym),
                           var='pub_syn',
                           LIMIT=False)

        self.xrefs = opm(
            MATCH="OPTIONAL MATCH (s:Site)<-[dbx:hasDbXref]-(primary) ",
            RETURN="COLLECT({ link: s.link_base + dbx.accession, link_text: s.label, " \
                   "site: %s, icon: coalesce(s.link_icon_url, '') }) AS xrefs" % self.roll_core("s"),
            var="xrefs",
            LIMIT = False)

        # Separate out parents from related?

        self.rels = opm(
                    var="rels",
                    MATCH="OPTIONAL MATCH (o:Class)<-[r]-(primary) ",
                    RETURN= "COLLECT ({ relation: r.label, object: %s } AS rels" % self.roll_core("o"),
                    LIMIT = False)

        image_match = "(i:Individual)<-[:depicts]-" \
                 "(:Individual)-[irw:in_register_with]->(template:Individual)-[:depicts]->" \
                 "(template_anat:Individual) "

        image_return = "{ template: template.label, folder: irw.folder, index: coalesce(irw.index, 0) }"

        self.image = opm(
            MATCH=image_match,
            RETURN=image_return + " AS image",
            var="image",
            LIMIT=False
        )

        self.images = opm(
            MATCH = "OPTIONAL MATCH (primary)<-[:SUBCLASSOF|INSTANCEOF*]-%s" % image_match,
            RETURN = "COLLECT({ anatomy: %s, image: %s }) AS images " % (self.roll_core("i"), image_return),
            var = "images",
            LIMIT = "WITH template, irw, i, %s limit 5")  # Not keen on this hidden sub...

        self.term = "{ core: %s, description: primary.description, comment: coalesce(primary.`annotation-comment`, [])} as term " % (
        self.roll_core("primary"))
        return


    def roll_core(self, var):
        return "{ short_form: %s.short_form, label: %s.label, " \
                "iri: %s.iri, types: labels(%s) } " % (var, var, var, var)

    def roll_query(self, type, clauses, short_form, pretty_print=False):

        """Takes a type (cypher label string, delimited by ':'
        and a list of clauses (opm objects) and returns a cypher query.
        """
        var_stack = []

        primary_query = "MATCH (primary:%s {short_form: '%s' }) " % (type, short_form)

        def roll_clause(q, primary="primary"):
            v = list(var_stack)
            v.append(primary)
            vars_string = ", ".join(v)
            delim = " "
            out_list = []
            if pretty_print:
                delim = " \n"
                out_list.append("")
            out_list.append(q.MATCH)
            if q.LIMIT:
                out_list.append(q.LIMIT % vars_string)
            out_list.append("WITH " + q.RETURN + ", " + vars_string)
            out = delim.join(out_list) + delim
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
        return self.roll_query(type='Individual:Anatomy',
                               short_form=short_form,
                               clauses=[self.xrefs],
                               pretty_print=pretty_print) # Is Anatomy label sufficient here

    def class_query(self, short_form, pretty_print=False):
        return self.roll_query(type='Class:Anatomy',
                               short_form = short_form,
                               clauses=[self.xrefs,
                                        self.images],
                               pretty_print=pretty_print)

    def data_set_query(self, short_form, pretty_print=False):
        return self.roll_query(type='Dataset',
                               short_form=short_form,
                               clauses=[self.xrefs],
                               pretty_print=pretty_print)







# Really need an edge property that distinguishes logical from annotation properties!
# TODO - Add retain related property to edge flipping code.Nico to add to V2.




