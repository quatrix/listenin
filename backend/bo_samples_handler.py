from base_handler import CORSHandler

class BOSamplesHandler(CORSHandler):
    def post(self):
        sample_id = int(self.get_argument('sample_id'))
        club_id = self.get_token()['club_id']
        box_id = self.settings['clubs'].get(club_id).get('box_id')
        self.settings['samples'].toggle_hiddeness(box_id, sample_id)
        self.finish({'success': True, 'error': None})
