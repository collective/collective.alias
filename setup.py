from setuptools import setup, find_packages
import os

version = '2.0.dev0'

setup(name='collective.alias',
      version=version,
      description="Aliasing of Plone content",
      long_description=open("README.txt").read() + "\n" +
                       open(os.path.join("docs", "HISTORY.txt")).read(),
      # Get more strings from http://www.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
        "Framework :: Plone",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
        ],
      keywords='plone alias',
      author='Martin Aspeli',
      author_email='optilude@gmail.com',
      url='http://pypi.python.org/pypi/collective.alias',
      license='GPL',
      packages = find_packages('src'),
      package_dir = {'': 'src'},
      namespace_packages=['collective'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          'plone.app.dexterity [relations]',
          'plone.app.registry >= 1.0b1',
          'rwproperty',
          'plone.contentrules',
          'plone.directives.dexterity',
          'plone.portlets',
      ],
      extras_require={
          'test': [
              'collective.testcaselayer',
              'Products.PloneTestCase',
          ]
      },
      entry_points="""
      [z3c.autoinclude.plugin]
      target = plone
      """,
      )
