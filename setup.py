#!/usr/bin/env python
import io

try:
    from setuptools import setup
except ImportError:
    from ez_setup import use_setuptools

    use_setuptools()

from setuptools import find_packages, setup


def read(*filenames, **kwargs):
    encoding = kwargs.get("encoding", "utf-8")
    sep = kwargs.get("sep", "\n")
    buf = []
    for filename in filenames:
        with io.open(filename, encoding=encoding) as f:
            buf.append(f.read())
    return sep.join(buf)


setup(
    name="DMP-OTSA",
    packages=["DMP-OTSA"],
    version="0.0",
    description="DMP-OTSA",
    author="Kongkiat Rothomphiwat",
    author_email="palmkongkiet@gmail.com",
    url="https://github.com/VISTEC-IST-ROBOTICS-PUBLIC/DMP-OTSA.git",
)
