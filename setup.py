import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()


setuptools.setup(
    name="staticviking",
    packages=["staticviking"],
    package_dir={"staticviking": "staticviking"},
    package_data={
        'staticviking': ['default_config.json', 'themes/*'],
        'staticviking.templates.abc': ["**"],
    },
    version="0.0.1",
    author="Martin F",
    author_email="pypi.org@tigerteamx.com",
    description="Simplest Blog Engine for Developers",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/tigerteamx/tigerblog",
    install_requires=[],  # Used for dependencies
    entry_points={
        'console_scripts': ['staticviking = staticviking.staticviking:cli']
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    keywords=['blog', 'productivity', 'static site generator'],
    python_requires='>=3.8',
    include_package_data=True,
)
