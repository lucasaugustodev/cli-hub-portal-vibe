from setuptools import setup, find_namespace_packages

setup(
    name="cli-anything-hub-portal-vibe",
    version="1.0.0",
    description="CLI-Anything harness for Hub Portal Vibe (SomosAHub)",
    packages=find_namespace_packages(include=["cli_anything.*"]),
    install_requires=[
        "click>=8.0.0",
        "prompt-toolkit>=3.0.0",
        "supabase>=2.0.0",
    ],
    entry_points={
        "console_scripts": [
            "cli-anything-hub-portal-vibe=cli_anything.hub_portal_vibe.hub_portal_vibe_cli:main",
        ],
    },
    python_requires=">=3.10",
)
