import unittest
from vfb_query_builder.query_roller import QueryLibrary, query_builder
from .test_tools import TestWrapper


class QueryRollerTest(unittest.TestCase):

    def setUp(self):
        self.ql = QueryLibrary()
        self.qw = TestWrapper('vfb_query.json')

        print("Running", self.id().split('.')[1:])

    def test_anat_2_ep_query(self):
        query = self.ql.anat_2_ep_query(short_forms=["FBbt_00050101", "FBbt_00050253", "FBbt_00050143", "FBbt_00050167", "FBbt_00110412", "FBbt_00100218", "FBbt_00003638", "FBbt_00003662", "FBbt_00003641", "FBbt_00003639", "FBbt_00110325", "FBbt_00111506", "FBbt_00111052", "FBbt_00111507", "FBbt_00111508", "FBbt_00111053", "FBbt_00111509", "FBbt_00111510", "FBbt_00111055", "FBbt_00111054", "FBbt_00040033", "FBbt_00110151", "FBbt_00003646", "FBbt_00003643", "FBbt_00110326", "FBbt_00007566", "FBbt_00007565", "FBbt_00007564", "FBbt_00007563", "FBbt_00007562", "FBbt_00007561", "FBbt_00007560", "FBbt_00007559", "FBbt_00003634"], pretty_print=True)

        print("Testing and printing first result in list only.")
        r = self.qw.test(t=self,
                         query=query, single=False)

    def test_anat_image_query(self):
        query=self.ql.anat_image_query(short_forms=["VFB_00002007", "VFB_00002009", "VFB_00002016", "VFB_00002014", "VFB_00012703", "VFB_00002587", "VFB_00002583", "VFB_00002582", "VFB_00013568", "VFB_00013655", "VFB_00003307", "VFB_00013598", "VFB_00003302", "VFB_00003301", "VFB_00003342", "VFB_00009590", "VFB_00013448", "VFB_00008176", "VFB_00013523", "VFB_00001720", "VFB_00003369", "VFB_00003268", "VFB_00003361", "VFB_00003281", "VFB_00013613", "VFB_00013779", "VFB_00013510", "VFB_00013456", "VFB_00013534", "VFB_00013751", "VFB_00013390", "VFB_00003255", "VFB_00003277", "VFB_00013529", "VFB_00003073", "VFB_00013481", "VFB_00013544", "VFB_00013742", "VFB_00013341", "VFB_00013385", "VFB_00013462", "VFB_00013581", "VFB_00003104", "VFB_00013536", "VFB_00013339", "VFB_00003180", "VFB_00013736", "VFB_00013616", "VFB_00013556", "VFB_00010481", "VFB_00013513", "VFB_00013711", "VFB_00013594", "VFB_00013474", "VFB_00010486", "VFB_00013552", "VFB_00013750", "VFB_00013592", "VFB_00010480", "VFB_00003313", "VFB_00003357", "VFB_00003231", "VFB_00003275", "VFB_00013702", "VFB_00003192", "VFB_00013765", "VFB_00010491", "VFB_00003326", "VFB_00003124", "VFB_00003246", "VFB_00003123", "VFB_00003165", "VFB_00013717", "VFB_00013437", "VFB_00013535", "VFB_00013574", "VFB_00013651", "VFB_00013498", "VFB_00003211", "VFB_00003296", "VFB_00003250", "VFB_00013729", "VFB_00013767", "VFB_00013406", "VFB_00100736", "VFB_00100737", "VFB_00100742", "VFB_00100741", "VFB_00003308", "VFB_00003309", "VFB_00003311", "VFB_00003319", "VFB_00003338", "VFB_00003335", "VFB_00003347", "VFB_00003364", "VFB_00003365", "VFB_00003363", "VFB_00003413", "VFB_00003126", "VFB_00003168", "VFB_00003166", "VFB_00003171", "VFB_00003184", "VFB_00003181", "VFB_00003208", "VFB_00003218", "VFB_00003239", "VFB_00003252", "VFB_00003264", "VFB_00003261", "VFB_00003262", "VFB_00003260", "VFB_00003278", "VFB_00003293", "VFB_00013466", "VFB_00013403", "VFB_00013562", "VFB_00013662", "VFB_00013580", "VFB_00013459", "VFB_00013697", "VFB_00003077", "VFB_00013400", "VFB_00013434", "VFB_00013500", "VFB_00013512", "VFB_00013557", "VFB_00013520", "VFB_00013630", "VFB_00003087", "VFB_00013615", "VFB_00013533", "VFB_00010471", "VFB_00003046", "VFB_00000946", "VFB_00013508", "VFB_00011250", "VFB_00013775", "VFB_00010469", "VFB_00013472", "VFB_00013719", "VFB_00013343", "VFB_00013596", "VFB_00013564", "VFB_00013982", "VFB_00003534", "VFB_00011227", "VFB_00013503", "VFB_00013515", "VFB_00013438", "VFB_00010475", "VFB_00003086", "VFB_00010479", "VFB_00013422", "VFB_00013522", "VFB_00013524", "VFB_00010477", "VFB_00013463", "VFB_00013563", "VFB_00013585", "VFB_00000590", "VFB_00013334", "VFB_00013477", "VFB_00013412", "VFB_00013495", "VFB_00013397", "VFB_00013496", "VFB_00013573", "VFB_00013493", "VFB_00013727", "VFB_00013728", "VFB_00013547", "VFB_00013726", "VFB_jrch0a7d", "VFB_jrch0a7c", "VFB_jrch0a2r", "VFB_jrch0a2p", "VFB_jrch0a3d", "VFB_jrch0a8x", "VFB_jrch0b0e", "VFB_jrch0b8f", "VFB_jrch0b9k", "VFB_jrch0b2d", "VFB_jrch0agt", "VFB_jrch0ahm", "VFB_jrch0aj7", "VFB_jrch0aib", "VFB_jrch0aej", "VFB_jrch0as3", "VFB_jrch0ajc", "VFB_jrch0akw", "VFB_jrch0an1", "VFB_jrch0c8z", "VFB_jrch0awo", "VFB_jrch0c5d", "VFB_jrch0av6", "VFB_jrch0atl", "VFB_00102735", "VFB_00102716"])
        print("Testing and printing first result in list only.")
        r = self.qw.test(t=self,
                         query=query, single=False)

    def test_ep_2_anat_query(self):
        query = self.ql.ep_2_anat_query(['VFBexp_FBtp0106753'],
                                       pretty_print=True,)

        print("Testing and printing first result in list only.")
        r = self.qw.test(t=self,
                         query=query, single=False)

    def test_template_2_datasets_query(self):
        query = self.ql.template_2_datasets_query('VFB_00050000')
        print("Testing and printing first result in list only.")
        r = self.qw.test(t=self,
                         query=query, single=False)

    def test_all_datasets_query(self):
        query = self.ql.all_datasets_query()
        print("Testing and printing first result in list only.")
        r = self.qw.test(t=self,
                         query=query, single=False)

    def test_anatomy_query(self):
        query = self.ql.anat_query(short_forms=['FBbt_00048350', 'FBbt_00047826', 'FBbt_00111338', 'FBbt_00048346', 'FBbt_00047227', 'FBbt_00007445', 'FBbt_00003864', 'FBbt_00007452', 'FBbt_00111354', 'FBbt_00007476', 'FBbt_00111661', 'FBbt_00049514', 'FBbt_00100470', 'FBbt_00100225', 'FBbt_00110570', 'FBbt_00111685', 'FBbt_00047723', 'FBbt_00110086', 'FBbt_00067349', 'FBbt_00007444', 'FBbt_00048354', 'FBbt_00003879', 'FBbt_00111481', 'FBbt_00067369', 'FBbt_00111359', 'FBbt_00067350', 'FBbt_00111749', 'FBbt_00100485', 'FBbt_00003994', 'FBbt_00007437', 'FBbt_00110427', 'FBbt_00110983', 'FBbt_00047681', 'FBbt_00067123', 'FBbt_00111715', 'FBbt_00047724', 'FBbt_00047825', 'FBbt_00047429', 'FBbt_00048353', 'FBbt_00111470', 'FBbt_00003875', 'FBbt_00067021', 'FBbt_00100381', 'FBbt_00111355', 'FBbt_00047720', 'FBbt_00067364', 'FBbt_00100388', 'FBbt_00048520', 'FBbt_00003880', 'FBbt_00100489'])
        print("Testing and printing first result in list only.")
        r = self.qw.test(t=self,
                         query=query, single=False)

    def test_anat_scRNAseq_query(self):
        query = self.ql.anat_scRNAseq_query(short_forms=['FBbt_00048152', 'FBbt_00048274'])
        print("Testing and printing first result in list only.")
        r = self.qw.test(t=self,
                         query=query, single=False)

    def test_cluster_expression(self):
        query = self.ql.cluster_expression_query(short_forms=['FBlc0003890', 'FBlc0003882'])
        print("Testing and printing first result in list only.")
        r = self.qw.test(t=self,
                         query=query, single=False)



if __name__ == '__main__':
    unittest.main(verbosity=2)
