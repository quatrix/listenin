from base_handler import BaseHandler


class HealthHandler(BaseHandler):
    def get_last_upload(self, box):
        return self.settings['samples'].all()[box][0]['date']

    def get(self):
        box = self.get_argument('box')

        self.finish({
            'last_upload': self.get_last_upload(box)
        })
