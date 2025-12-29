from unittest.mock import patch
from androbuilder import Builder

@patch('androbuilder.sdk_manager.subprocess.run')
def test_builder_build(mock_run):
    mock_run.return_value.returncode = 0

    builder = Builder(
        path="./tests/testapp",
        sdk="28",
        versioncode=1,
        versionname="1.0",
        verbose=False,
        proguard=False,
        sign=False,
        buildtools="33.0.2",
    )

    result_path = builder.build("./tests/output")
    assert result_path.endswith(".apk")
