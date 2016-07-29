from setuptools import setup

setup(name='abook',
      version='0.4.0',
      description='''
       Python library to convert between Abook and vCard
       ''',
      author='Jochen Sprickerhof',
      author_email='abook@jochen.sprickerhof.de',
      license='GPLv3+',
      url='https://github.com/jspricke/python-abook',
      keywords=['Abook'],
      classifiers=[
          'Programming Language :: Python',
          'Development Status :: 4 - Beta',
          'Environment :: Console',
          'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
          'Topic :: Software Development :: Libraries :: Python Modules',
          ],

      install_requires=['configobj', 'python-card-me'],
      py_modules=['abook'],

      entry_points={
          'console_scripts': [
              'abook2vcf = abook:abook2vcf',
              'vcf2abook = abook:vcf2abook',
              ]
          },)
