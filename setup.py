from setuptools import setup, find_packages

setup(
    name="wechat-articles-notion",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'requests',
        'Pillow',
    ],
) 