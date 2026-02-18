from setuptools import setup, find_packages
from ftk_claw_bot.constants import VERSION

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="ftkclawbot",
    version=VERSION,
    author="FTK Team",
    author_email="zeusftk@gmail.com",
    description="Windows桌面应用，用于管理WSL2中的clawbot助手，并扩展clawbot对windows的操作",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/zeusftk/FTK_Claw_Bot",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: System :: Systems Administration",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: Microsoft :: Windows",
    ],
    python_requires=">=3.10",
    install_requires=[
        "PyQt6>=6.5.0",
        "psutil>=5.9.0",
        "pyautogui>=0.9.54",
        "pywinauto>=0.6.8",
        "Pillow>=10.0.0",
        "cryptography>=41.0.0",
        "pywin32>=306",
        "watchdog>=3.0.0",
    ],
    entry_points={
        "console_scripts": [
            "ftkclawbot=ftk_claw_bot.main:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
