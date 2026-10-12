# Surface Studio 安装与 Blender 自动连接

当前本地构建：SS 1.1.2 + Blender 插件 1.1.0。更新后支持将材质球从 Windows 桌面客户端拖到 Blender 视口中的网格上；需要对象模式，可 Ctrl+Z 撤销。只更新 EXE 不更新插件，无法使用拖放；本安装器会一起更新。

本版已在 Blender 4.2.4 LTS 完成用户手动跨窗口拖放验收；目标模型赋予、撤销和视口落点检测已做分项测试。其他版本完整手势尚未逐一手测。网页访问不支持原生拖出。

运行 `SurfaceStudio-Setup.exe`，选择软件位置。安装器会检查常见安装目录、Windows 注册记录及运行中的 Blender；便携版、自定义路径可点击“手动选择”，指定 `blender.exe`。

勾选需要连接的兼容版本，保存工作并关闭 Blender，然后点击“安装并连接”。安装器会：

1. 安装 SS，并添加开始菜单快捷方式；保留软件目录中原有的 data。
2. 读取各 Blender 实际使用的用户插件和偏好设置目录。
3. 备份原有 SS 插件及偏好设置，安装、启用插件并写入 SS 程序路径。
4. 再次后台启动 Blender，确认插件自动启用、路径已保存。失败时恢复此次操作前的插件及偏好设置。

当前自动安装针对 Blender 4.2、4.3、5.1、5.2 正式版系列；其他版本显示为未验证，不自动安装。不同补丁版本如果共享同一用户配置，仅安装一次。每个版本的结果分别显示，某个版本失败不会阻止其他版本或 SS 独立使用。

安装完成后打开 Blender，3D 视图按 N → Surface Studio，选中网格模型并点击“打开材质库”。在 SS 的材质库设置中选择自己的素材目录，选择材质并点击“赋予到 Blender”。对象模式作用于选中模型，编辑模式只作用于选中的面；Ctrl+Z 可撤销。

没有 Blender 时也可安装 SS。后来新增 Blender，或移动了 SS 目录，可重新运行安装器，选择当前 SS 文件夹并安装连接。未完成的插件安装可以关闭 Blender 后重试。软件仍支持在 Blender 中手动安装旁边的 surface_studio_bridge.zip。

更新已有 SS 前，请关闭窗口并退出任务管理器中的 Surface Studio.exe 后台进程。安装器不会强行结束 SS 或 Blender。安装目录需可写，不要放在需要管理员权限的 Program Files 中。默认安装在当前用户的 LocalAppData/Programs/SurfaceStudio。

备份保存在软件目录的 data/installer-backups，结果保存在 data/installer-report.json。保留这些文件以便回退。分享软件时不要打包个人 data。

需要 Windows 10 / 11 x64 和 Microsoft Edge WebView2 Runtime；无需安装 Python。WebView2 下载：https://developer.microsoft.com/microsoft-edge/webview2/ 。本安装器不包含 WebView2 或材质资源。

安装器只配置当前 Windows 用户。它不更改 Blender 程序文件、不打开或保存用户工程，也不会自动把贴图打包进 blend。已启用的其他 Blender 插件在后台验证时仍会随 Blender 正常加载。

1.1.1 修复：拖到 Blender 以外的位置松开会取消，禁止 SS 网页接收拖放并跳转。插件版本仍为 1.1.0。
