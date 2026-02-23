from setuptools import setup, find_packages
import os

with open('requirements.txt', 'r', encoding='utf-8') as f:
    requirements = f.read().splitlines()

model_dir = 'Qwen3-Embedding-0.6B-ONNX'
if not os.path.exists(model_dir):
    os.makedirs(model_dir, exist_ok=True)

setup(
    name="ftk-embedding-service",
    version="1.0.0",
    description="FTK Embedding Service with ONNX support",
    author="FTK Team",
    author_email="",
    packages=find_packages(),
    include_package_data=True,
    data_files=[
        ('', ['requirements.txt']),
        ('Qwen3-Embedding-0.6B-ONNX', [
            'Qwen3-Embedding-0.6B-ONNX/model_int8.onnx'
        ]),
        ('Qwen3-Embedding-0.6B-ONNX/tokenizer', [
            'Qwen3-Embedding-0.6B-ONNX/tokenizer/tokenizer_config.json',
            'Qwen3-Embedding-0.6B-ONNX/tokenizer/vocab.txt'
        ])
    ],
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'ftk-embed = app.main:run'
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
)
