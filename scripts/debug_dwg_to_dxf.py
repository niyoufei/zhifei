from pathlib import Path

from ezdxf.addons import odafc


def main() -> None:
    # Manual ODA-based DWG -> DXF conversion probe for local debugging.
    oda_path = "/Applications/ODAFileConverter.app/Contents/MacOS/ODAFileConverter"

    print("【调试】准备设置 unix_exec_path =", repr(oda_path))
    odafc.unix_exec_path = oda_path

    print("【调试】odafc.unix_exec_path =", repr(odafc.unix_exec_path))
    try:
        installed = odafc.is_installed()
    except Exception as e:
        print("【调试】调用 odafc.is_installed() 出错：", repr(e))
        installed = False
    print("【调试】odafc.is_installed() =", installed)
    print("-" * 60)

    home = Path.home()
    input_path = home / "DWG_test" / "test.dwg"
    output_path = home / "DWG_test" / "test_converted.dxf"

    print("Input DWG:", input_path)
    print("Output DXF:", output_path)

    if not input_path.exists():
        print("找不到输入 DWG，请确保已创建 ~/DWG_test/test.dwg")
        return

    try:
        odafc.convert(
            source=str(input_path),
            dest=str(output_path),
            version="R2018",
            audit=True,
            replace=True,
        )
        print("转换成功：请检查 ~/DWG_test/test_converted.dxf")
    except Exception as e:
        print("转换失败，错误如下：")
        print(repr(e))


if __name__ == "__main__":
    main()
