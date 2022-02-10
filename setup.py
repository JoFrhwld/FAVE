# -*- coding: utf-8 -*-
from setuptools import setup

packages = \
['fave', 'fave.align', 'fave.align.model', 'fave.extract']

package_data = \
{'': ['*'],
 'fave': ['praatScripts/*'],
 'fave.align': ['examples/*', 'examples/test/*', 'old_docs/*', 'readme_img/*'],
 'fave.align.model': ['11025/*',
                      '16000 (old model)/*',
                      '16000/*',
                      '8000/*',
                      'backups dicts/*',
                      'g-dropping Jiahong/*',
                      'g-dropping Jiahong/16000/*'],
 'fave.extract': ['config/*', 'old_docs/*']}

setup_kwargs = {
    'name': 'fave',
    'version': '2.0.0.dev0',
    'description': 'Forced alignment and vowel extraction',
    'long_description': None,
    'author': 'FAVE contributors',
    'author_email': None,
    'maintainer': None,
    'maintainer_email': None,
    'url': None,
    'packages': packages,
    'package_data': package_data,
    'python_requires': '>=3.7,<4.0',
}


setup(**setup_kwargs)
