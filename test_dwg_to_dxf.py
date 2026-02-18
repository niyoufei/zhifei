from pathlib import Path
from ezdxf.addons import odafc

def main() -> None:
    # 1）配置 ODA File Converter 的可执行文件路径（务必保持此行为一整行）
    oda_path = "/Applications/ODAFileConverter.app/Contents/MacOS/ODAFileConverter"

    print("【调试】准备设置 unix_exec_path =", repr(oda_path))
    odafc.unix_exec_path = oda_path

    # 打印当前 odafc 状态
    print("【调试】odafc.unix_exec_path =", repr(odafc.unix_exec_path))
    try:
        installed = odafc.is_installed()
    except Exception as e:
        print("【调试】调用 odafc.is_installed() 出错：", repr(e))
        installed = False
    print("【调试】odafc.is_installed() =", installed)
    print("-" * 60)

    # 2）输入 / 输出路径
    home = Path.home()
    input_path = home / "DWG_test" / "test.dwg"
    output_path = home / "DWG_test" / "test_converted.dxf"

    print("Input DWG:", input_path)
    print("Output DXF:", output_path)

    if not input_path.exists():
        print("找不到输入 DWG，请确保已创建 ~/DWG_test/test.dwg")
        return

    # 3）执行 DWG → DXF 转换
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
