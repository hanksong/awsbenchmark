#!/usr/bin/env python3
# requirements.txt generator

import os
import sys
dependencies = [
    "pandas",
    "matplotlib",
    "seaborn",
    "jinja2",
    "numpy",
    "boto3"
]
with open("requirements.txt", "w") as f:
    for dep in dependencies:
        f.write(f"{dep}\n")

print("requirements.txt generated")
