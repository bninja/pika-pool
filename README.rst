=========
pika-pool
=========

.. image:: https://travis-ci.org/bninja/pika-pool.png
   :target: https://travis-ci.org/bninja/pika-pool
   
.. image:: https://coveralls.io/repos/bninja/pika-pool/badge.png?branch=master
   :target: https://coveralls.io/r/bninja/pika-pool?branch=master

Pika connection pooling inspired by:

- `flask-pika <https://github.com/WeatherDecisionTechnologies/flask-pika>`_
- `sqlalchemy.pool.Pool <http://docs.sqlalchemy.org/en/latest/core/pooling.html#sqlalchemy.pool.Pool>`_

Typically you'll go with local `shovels <https://www.rabbitmq.com/shovel.html>`_, `krazee-eyez kombu <http://bit.ly/1txcnnO>`_, etc. but this works too.

usage
-----

Get it:

.. code:: bash

   pip install pika-pool

and use it:

.. code:: python

   import json

   import pika
   import pika_pool

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

release
-------

Tests pass:

.. code:: bash

   py.test test.py --cov=pika_pool --cov-report term-missing

so update ``__version__`` in:

- ``__init__.py``

then commit and tag it:

.. code:: bash

   git commit -am "release v{version}"
   git tag -a v{version} -m "release v{version}"
   git push --tags

and `travis <https://travis-ci.org/bninja/pika-pool>`_ will publish it to `pypi <https://pypi.python.org/pypi/pika-pool/>`_.
