import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()


setuptools.setup(
    name="staticviking2",
    packages=["staticviking"],
    package_dir={"staticviking": "staticviking"},
    package_data={
        'staticviking': ['default_config.json', 'themes/*'],
        'staticviking.templates.abc': ["**"],
    },
    version="0.0.1",
    author="Martin Baun",
    author_email="pypi@martinbaun.com",
    description="Simplest static page engine for Developers",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://martinbaun.com/blog/posts/staticviking-zeroconf-static-website-for-blogs-wikis/",
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
