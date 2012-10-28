# -*- coding: utf-8 -*-
"""
    Simple sockjs-tornado chat application. By default will listen on port 8080
"""
import json
import tornado.ioloop
import tornado.web

import sockjs.tornado
from tabletop.game import PlayerConnection


class IndexHandler(tornado.web.RequestHandler):
    """Regular HTTP handler to serve the chatroom page"""
    def initialize(self, index_file):
        self.index_file = index_file

    def get(self, **kwargs):
        kwargs = dict((k, json.dumps(v)) for k, v in kwargs.items())
        self.render(self.index_file, args=kwargs)


def runserver(index_file, static_path='/static'):
    import logging
    logging.getLogger().setLevel(logging.DEBUG)

    # 1. Create chat router
    GameRouter = sockjs.tornado.SockJSRouter(PlayerConnection, '/game')

    # 2. Create Tornado application
    app = tornado.web.Application(
        [(r"/", IndexHandler, {'index_file': index_file}),
         (r"/g/(?P<gameType>[^/]+)?/?(?P<gameId>[^/]+)?/?(?P<playerId>.+)?",
             IndexHandler, {'index_file': index_file}),
         (r"/static/(.*)", tornado.web.StaticFileHandler,
             {'path': static_path}),
         ] + GameRouter.urls
    )

    # 3. Make Tornado app listen on port 8080
    app.listen(8080)

    # 4. Start IOLoop
    tornado.ioloop.IOLoop.instance().start()
