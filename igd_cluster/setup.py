from setuptools import find_packages, setup

setup(
    name="igd_cluster",
    packages=find_packages(exclude=["igd_cluster_tests"]),
    install_requires=[
        "dagster",
        "dagster-cloud"
    ],
    extras_require={"dev": ["dagster-webserver", "pytest"]},
)
