import time
from setuptools import find_packages, setup


project_name = 'okimotus-monitor'
version = '0.0.1.%s' % int(time.time())

SCRIPTS = [
    'monitor=monitor.monitor:main'
]

DEPENDENCIES = [
    'argcomplete>=1.12',
    'camel-converter>=3',
    'colorama>=0.4',
    'colored-traceback>=0.3.0',
    'dpath==2.0.1',
    'Jinja2>=3.1.2',
    'Pygments>=2.16',
    'pythondialog>=3.5',
    'requests>=2.28',
    'intelhex>=2.3.0',
    'pyyaml>=6.0.2',
    'tabulate>=0.9.0',
    'pyserial==3.5'
]


TEST_DEPENDENCIES = [
    'pytest',
    'mock',
    'pytest-mock',
    'coverage'
]


setup_config = {
    'name': project_name,
    'version': version,
    'author': "Petros Makris",
    'author_email': "info@okimotus.com",
    'python_requires': ">=3.7",
    'package_dir': {"": "src"},
    'packages': find_packages(where="src", exclude=["*.tests", "*.tests.*", "tests.*", "tests"]),
    'install_requires': DEPENDENCIES,
    'tests_require': TEST_DEPENDENCIES,
    'include_package_data': True,
    'entry_points': { 'console_scripts': SCRIPTS },
}

if __name__ == '__main__':
    setup(**setup_config)
