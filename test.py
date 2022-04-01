from __future__ import unicode_literals

import json
import select
import threading
import time
import uuid

import pika
import pytest

import pika_pool


@pytest.fixture(scope='session')
def params():
    return pika.URLParameters('amqp://guest:guest@localhost:5672/')


@pytest.fixture(scope='session', autouse=True)
def schema(request, params):
    cxn = pika.BlockingConnection(params)
    channel = cxn.channel()
    channel.queue_declare(queue='pika_pool_test')


consumed = {
}


@pytest.fixture(scope='session', autouse=True)
def consume(params):

    def _callback(ch, method, properties, body):
        msg = Message.from_json(body)
        consumed[msg.id] = msg

    def _forever():
        channel.start_consuming()

    cxn = pika.BlockingConnection(params)
    channel = cxn.channel()
    channel.queue_declare(queue='pika_pool_test')
    channel.basic_consume(_callback, queue='pika_pool_test', no_ack=True)

    thd = threading.Thread(target=_forever)
    thd.daemon = True
    thd.start()


@pytest.fixture
def null_pool(params):
    return pika_pool.NullPool(
        create=lambda: pika.BlockingConnection(params),
    )


class Message(dict):

    @classmethod
    def generate(cls, **kwargs):
        id = kwargs.pop('id', uuid.uuid4().hex)
        return cls(id=id, **kwargs)

    @property
    def id(self):
        return self['id']

    def to_json(self):
        return json.dumps(self)

    @classmethod
    def from_json(cls, raw):
        return cls(json.loads(raw.decode('utf-8')))


class TestNullPool(object):

    def test_pub(self, null_pool):
        msg = Message.generate()
        with null_pool.acquire() as cxn:
            cxn.channel.basic_publish(
                exchange='',
                routing_key='pika_pool_test',
                body=msg.to_json()
            )
        time.sleep(0.1)
        assert msg.id in consumed


@pytest.fixture
def queued_pool(params):
    return pika_pool.QueuedPool(
        create=lambda: pika.BlockingConnection(params),
        recycle=10,
        stale=10,
        max_size=10,
        max_overflow=10,
        timeout=10,
    )


@pytest.fixture
def empty_queued_pool(request, queued_pool):
    queued = [queued_pool.acquire() for _ in range(queued_pool.max_size)]
    request.addfinalizer(lambda: [cxn.release() for cxn in queued])
    overflow = [queued_pool.acquire() for _ in range(queued_pool.max_overflow)]
    request.addfinalizer(lambda: [cxn.release() for cxn in overflow])
    return queued_pool


def test_use_it():
    params = pika.URLParameters(
      'amqp://guest:guest@localhost:5672/?'
      'socket_timeout=10&'
      'connection_attempts=2'
    )

    pool = pika_pool.QueuedPool(
        create=lambda: pika.BlockingConnection(parameters=params),
        max_size=10,
        max_overflow=10,
        timeout=10,
        recycle=3600,
        stale=45,
    )

    with pool.acquire() as cxn:
        cxn.channel.basic_publish(
            body=json.dumps({
                'type': 'banana',
                'description': 'they are yellow'
            }),
            exchange='',
            routing_key='fruits',
            properties=pika.BasicProperties(
                content_type='application/json',
                content_encoding='utf-8',
                delivery_mode=2,
            )
        )
        assert 'cxn=localhost:5672//' in str(cxn.fairy)


class TestQueuedPool(object):

    def test_invalidate_connection(slef, queued_pool):
        msg = Message.generate()
        with pytest.raises(select.error):
            with queued_pool.acquire() as cxn:
                fairy = cxn.fairy
                raise select.error(9, 'Bad file descriptor')
        assert fairy.cxn.is_closed

    def test_pub(self, queued_pool):
        msg = Message.generate()
        with queued_pool.acquire() as cxn:
            cxn.channel.basic_publish(
                exchange='',
                routing_key='pika_pool_test',
                body=msg.to_json()
            )
        time.sleep(0.1)
        assert msg.id in consumed

    def test_expire(self, queued_pool):
        with queued_pool.acquire() as cxn:
            expired = id(cxn.fairy.cxn)
            expires_at = cxn.fairy.created_at + queued_pool.recycle
        with queued_pool.acquire() as cxn:
            assert expired == id(cxn.fairy.cxn)
            cxn.fairy.created_at -= queued_pool.recycle
        with queued_pool.acquire() as cxn:
            assert expired != id(cxn.fairy.cxn)

    def test_stale(self, queued_pool):
        with queued_pool.acquire() as cxn:
            stale = id(cxn.fairy.cxn)
            fairy = cxn.fairy
        with queued_pool.acquire() as cxn:
            assert stale == id(cxn.fairy.cxn)
        fairy.released_at -= queued_pool.stale
        with queued_pool.acquire() as cxn:
            assert stale != id(cxn.fairy.cxn)

    def test_overflow(self, queued_pool):
        queued = [queued_pool.acquire() for _ in range(queued_pool.max_size)]
        with queued_pool.acquire() as cxn:
            fairy = cxn.fairy
            for cxn in queued:
                cxn.release()
        assert fairy.cxn.is_closed

    def test_timeout(self, empty_queued_pool):
        empty_queued_pool.timeout = 2
        st = time.time()
        with pytest.raises(pika_pool.Timeout):
            empty_queued_pool.acquire()
        elapsed = time.time() - st
        assert elapsed < 2.5

    def test_timeout_override(self, empty_queued_pool):
        st = time.time()
        with pytest.raises(pika_pool.Timeout):
            empty_queued_pool.acquire(timeout=1)
        elapsed = time.time() - st
        assert elapsed < 1.5
