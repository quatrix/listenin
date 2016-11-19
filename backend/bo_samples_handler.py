from base_handler import CORSHandler

class BOSamplesHandler(CORSHandler):
    def post(self):
        sample_id = int(self.get_argument('sample_id'))
        club_id = self.get_token()['club_id']
        self.settings['samples'].toggle_hiddeness(club_id, sample_id)
        self.finish({'success': True, 'error': None})
