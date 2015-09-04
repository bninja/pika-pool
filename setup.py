import re
import setuptools


setuptools.setup(
    name='pika-pool',
    version=(
        re
        .compile(r".*__version__ = '(.*?)'", re.S)
        .match(open('pika_pool.py').read())
        .group(1)
    ),
    url='https://github.com/bninja/pika-pool',
    license='BSD',
    author='egon',
    author_email='egon@gb.com',
    description='Pools for pikas.',
    long_description=open('README.rst').read(),
    py_modules=['pika_pool'],
    include_package_data=True,
    platforms='any',
    install_requires=[
        'pika >=0.9,<0.11',
    ],
    extras_require={
        'tests': [
            'pytest >=2.5.2,<3',
            'pytest-cov >=1.7,<2',
        ],
    },
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)
