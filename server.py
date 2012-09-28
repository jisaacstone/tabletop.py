# -*- coding: utf-8 -*-
"""
    Simple sockjs-tornado chat application. By default will listen on port 8080
"""
import tornado.ioloop
import tornado.web

import sockjs.tornado
from game import PlayerConnection


class IndexHandler(tornado.web.RequestHandler):
    """Regular HTTP handler to serve the chatroom page"""
    def get(self, **kwargs):
        kwargs['game_type'] = kwargs.get('game_type', 'blackjack')
        kwargs['game_id'] = kwargs.get('game_id', None)
        kwargs['player_id'] = kwargs.get('player_id', None)
        self.render('index.html', **kwargs)


if __name__ == "__main__":
    import logging
    logging.getLogger().setLevel(logging.DEBUG)

    # 1. Create chat router
    GameRouter = sockjs.tornado.SockJSRouter(PlayerConnection, '/game')

    # 2. Create Tornado application
    app = tornado.web.Application(
        [(r"/", IndexHandler),
         (r"/g/(?P<game_type>[^/]+)?/?(?P<game_id>[^/]+)?/?(?P<player_id>.+)?",
             IndexHandler),
         ] + GameRouter.urls
    )

    # 3. Make Tornado app listen on port 8080
    app.listen(8080)

    # 4. Start IOLoop
    tornado.ioloop.IOLoop.instance().start()
