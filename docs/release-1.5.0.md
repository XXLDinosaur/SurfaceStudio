# Surface Studio 1.5.0 · Blender 双向材质库与自动更新

配套 Blender 插件 **1.2.2**。首次安装或从 1.4.0 升级，请下载 **SurfaceStudio-v1.5.0-Windows-x64-with-Blender.zip**，解压后运行安装器。Source code ZIP 是源码，不是软件安装包。

## 与 1.4.0 相比

- **Blender → SS 一键入库**：在 Blender 点击“添加到 SS”，保存到 SS 指定目录，默认与当前材质库一致。保留静态节点组和内嵌贴图，生成预览，自动进入置顶的“未分类”。整包保留后，重装软件重新添加目录即可使用。
- **重命名更直接**：右键菜单支持重命名，双击名称原位编辑；回车或失焦保存，Esc 取消。同步修改材质文件夹名，独立法线修改图片文件名；保留收藏和分类。其他工程引用旧路径时需要重新定位。
- **连接更直接**：顶部 Blender 按钮请求连接正在运行且启用了插件的 Blender。
- **GitHub 更新检查**：启动后自动检查正式 Release，可在设置中关闭或手动检查。发现新版时左下角显示“更新”；下载经过签名和完整性校验，确认后安装并重启。旧版用户必须先手动安装 1.5.0，才有此功能。
- **界面整理**：移除精选展示和“我的集合”入口，备份恢复移入材质库设置，删除重复的路径容量入口；修复 Ctrl+A 整页蓝色选中及小窗口设置入口被裁切，调整设置按钮间距。
- **更多 Blender 版本**：新增验证 4.4.3、4.5.15 LTS、5.0.1，并开放 4.4、4.5、5.0 系列自动安装。

## 使用说明

1. 保存工程、关闭 Blender，运行安装器并选择原 SS 安装位置；保留原 data 文件夹。
2. 安装器会检测兼容的 Blender；便携版或自定义路径可手动选择 blender.exe。
3. 进入 SS 材质库设置，选择素材库及 Blender 添加材质的保存位置。
4. 在 Blender 的 N 侧栏 → Surface Studio → 添加到 SS 保存活动材质，或从 SS 赋予到 Blender。

自动安装支持 Windows x64 下的 Blender 4.2、4.3、4.4、4.5 LTS、5.0、5.1、5.2 正式版系列。未验证版本暂不自动安装。原生节点材质不能导入比保存时主次版本更低的 Blender；动态或依赖外部场景的材质不在当前保存范围。

## 验证范围

54 项回归测试通过。新增三个版本均通过隔离环境下的安装启用、重启、偏好保留、失败回退、PBR 赋材质、原生材质往返与拖放处理测试。完整跨窗口鼠标拖拽仅在之前的 4.2.4 由用户人工验收，未声称所有版本均完成该手势测试。不同机器的 1080p/DPI 显示仍欢迎反馈。

软件更新已覆盖模拟新版、断网、错误签名、损坏下载、确认安装、安装器交接及数据保留；从本版向下一正式版的完整线上升级需后续版本发布后复验。

详细指南：[材质目录与格式](https://github.com/XXLDinosaur/SurfaceStudio/blob/main/docs/import-materials.md) · [Blender 自制材质](https://github.com/XXLDinosaur/SurfaceStudio/blob/main/docs/blender-material-export.md) · [版本兼容性](https://github.com/XXLDinosaur/SurfaceStudio/blob/main/docs/blender-compatibility.md) · [软件更新](https://github.com/XXLDinosaur/SurfaceStudio/blob/main/docs/auto-update.md)

下载合集已包含安装器、单独的 Blender 插件 ZIP、中文使用说明及上述指南。素材资源不随软件提供。
