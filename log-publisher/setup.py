import setuptools

setuptools.setup(
    name="log-parser",
    version="0.0.1",
    author="Carl McGraw",
    author_email="c@rlmcgraw.io",
    description="A small library for the log parser",
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.10",
)
