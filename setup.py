from setuptools import setup

setup(
    name="codenames",
    version='0.1',
    maintainer='Luminoso Technologies, Inc.',
    maintainer_email='rspeer@luminoso.com',
    platforms=["any"],
    description="An AI that plays Vlaada Chvatil's wordgame using ConceptNet",
    packages=['codenames'],
    include_package_data=True,
    install_requires=['numpy', 'scipy', 'sklearn', 'pandas', 'conceptnet >= 5.5', 'blessings'],
    zip_safe=False,
    classifiers=[
        "Programming Language :: Python :: 3",
    ],
    package_data={
        'codenames': ['data/*'],
    },
    entry_points={
        'console_scripts': ['codenames = codenames.console:main'],
    },
)
