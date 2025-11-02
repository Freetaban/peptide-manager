from setuptools import setup, find_packages

setup(
    name='peptide-manager',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'click>=8.0.0',
        'rich>=13.0.0',
        'tabulate>=0.9.0',
        'python-dateutil>=2.8.0',
    ],
    entry_points={
        'console_scripts': [
            'peptide-manager=cli.main:cli',
        ],
    },
    author='Your Name',
    description='Sistema di gestione peptidi completo',
    python_requires='>=3.8',
)
