from pathlib import Path
from androbuilder import Builder

def test_builder_build():
    builder = Builder(
        path="./tests/testapp",
        sdk="28",
        versioncode=1,
        versionname="1.0",
        verbose=True,
        proguard=False,
        sign=False,
        buildtools="33.0.2",
    )
    result_path = builder.build("./tests/output")
