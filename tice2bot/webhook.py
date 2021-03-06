from urllib.parse import parse_qs
from urllib.parse import urlparse

import tornado.ioloop
import tornado.web
import tornado.escape

import redis
from config.bot_config import REDIS_DB, REDIS_HOST, REDIS_PORT, WEBHOOK_IP, WEBHOOK_PORT

redis_ctx = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)


class IceCast2Auth(tornado.web.RequestHandler):

    def post(self):

        try:

            data = urlparse(self.request.body_arguments['mount'][0])
            key = parse_qs(data.query).get(b'key')[0]

            ip = urlparse(self.request.body_arguments['ip'][0])
            ip = ip.path

            x_real_ip = self.request.headers.get('X-Real-IP')
            remote_ip = x_real_ip or self.request.remote_ip

            server_ip = redis_ctx.hget(key, 'server').decode('utf-8')

            # if the user trying to play between the stream servers
            if server_ip != remote_ip:

                self.set_header('icecast-auth-user', '0')
                return

            username = redis_ctx.hget(key, 'username')
            ip_redis = redis_ctx.hget(key, 'ip')
            stream = redis_ctx.hget(key, 'stream')

            if username:

                # if ip_redis is none, means brand new conenction and here
                # we knowing the user ip send by icecast listener_add
                if ip_redis == b'none':

                    redis_ctx.hset(key, 'ip', ip)
                    ip_redis = ip

                # if ip_redis is real ip but differes from the user's one
                # we have to reject this connection. This means the user is shered its key
                # with somebody else or the user had new ip address if the second one is happen,
                # then we the user have to renew itsr key, there are a /renewkey command for
                # this purpose

                if ip_redis and ip_redis != 'none' and ip_redis != ip:

                    self.set_header('icecast-auth-user', '0')
                    return

                print('{} is authenticated and starting listening'.format(username))
                self.set_header('icecast-auth-user', '1')

            else:

                self.set_header('icecast-auth-user', '0')

        except Exception as e:

            print(e)
            self.set_header('icecast-auth-user', '0')


def make_app():

    return tornado.web.Application([
        (r'/icecast/', IceCast2Auth),
    ])

if __name__ == '__main__':

    app = make_app()
    app.listen(WEBHOOK_PORT, WEBHOOK_IP)
    tornado.ioloop.IOLoop.current().start()

