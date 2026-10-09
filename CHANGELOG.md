# v1.0.0 — 2026-10-09

首次整理发布 Surface Studio Windows 便携版及配套 Blender 插件。

## 本版内容

- 本地材质索引、搜索、分类、收藏、最近浏览、集合和双材质对比。
- 固定搜索筛选栏，紧凑 / 标准 / 大图 / 列表浏览，独立字号设置。
- 青灰磨砂玻璃图标、浅色 / 深色界面、一体化无边框桌面窗口。
- 顶部拖动、双击最大化 / 还原、窗口按钮与边缘缩放。
- Blender PBR 材质导入、选中对象或选中面赋材质。
- 源码默认路径与构建脚本不再依赖开发电脑盘符。

## 下载哪个文件

- **SurfaceStudio-v1.0.0-Windows-x64.zip**：SS 软件便携包。解压后运行 Surface Studio.exe，在材质库设置中选择自己的目录。
- **surface_studio_bridge.zip**：可选的 Blender 4.2+ 连接插件。在 Blender 插件设置中“从磁盘安装”，启用后设置 SS 程序路径。
- **SHA256SUMS.txt**：下载文件的 SHA-256 校验值。

## 运行与更新

需要 Windows 10 / 11 x64 与 Microsoft Edge WebView2 Runtime；无需安装 Python。程序包不含材质、收藏和个人配置。更新前退出旧 SS 后台，只替换 EXE，保留原 data 文件夹。

关闭窗口后本地服务仍在后台运行。界面使用已有预览图，不提供实时材质球渲染。没有 Revit / SketchUp 直接赋材质插件。

## 验证范围

服务与 Blender 消息邮箱的 14 项自动化测试通过。开发期间完成界面与原生窗口控制检查，Blender 联动在 4.2.4 LTS 和 5.1.2 验证过。其他 Windows 环境与 Blender 版本仍需使用者验证。
