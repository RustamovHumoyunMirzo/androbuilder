from androbuilder import Builder

def test_builder_build():
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

    result_path = builder.build("./output")

    assert isinstance(result_path, str), "Expected build result path as a string"
    assert result_path.endswith(".apk"), "Expected output file to be an APK"
