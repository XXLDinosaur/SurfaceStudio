# Blender 兼容性补测

测试日期：2026-10-27。SS 1.5.0，连接插件 1.2.2，Windows x64。

## 新增验证

| 官方便携版 | 安装/启用/重启 | 更新修复/失败回退 | PBR 赋材质 | 原生材质往返 | 拖放处理 |
| --- | --- | --- | --- | --- | --- |
| 4.4.3 | 通过 | 通过 | 通过 | 通过 | 通过 |
| 4.5.15 LTS | 通过 | 通过 | 通过 | 通过 | 通过 |
| 5.0.1 | 通过 | 通过 | 通过 | 通过 | 通过 |

安装器已开放 4.4、4.5、5.0 正式版系列，与之前的 4.2、4.3、5.1、5.2 一起支持。测试点为表中的具体补丁版本，不表示每个历史补丁均单独测试过。低于 4.2 的版本仍不在当前插件支持范围。

安装测试使用独立的配置、脚本、数据与扩展目录，验证重复安装、程序路径变更、偏好设置保留和损坏插件回退。未修改用户现有 Blender 配置。

PBR 测试包含对象和选中面赋材质、共享网格隔离、UV、颜色空间、法线/粗糙度/AO、材质复用、消息处理及撤销。原生材质测试包含静态节点组、内嵌图片、CPU 预览渲染，删除原贴图并移动材质库后重新读取、赋予模型，以及拒绝外部对象依赖。

拖放测试验证插件的文件载荷和目标赋材质逻辑；这些新增版本尚未逐一人工完成从 SS 到视口的真实鼠标拖拽验收，不将后台测试等同于完整桌面交互测试。不同显卡、Windows DPI 和特殊节点组合仍可能存在环境差异。

## 来源与复验

便携包来自 [Blender 官方下载档案](https://download.blender.org/release/)，下载后按各版本官方 SHA-256 清单校验。

运行 `python test_installer_blender.py <blender.exe>` 检查安装及 PBR；使用独立 `BLENDER_USER_CONFIG`、`BLENDER_USER_SCRIPTS`、`BLENDER_USER_DATAFILES`、`BLENDER_USER_EXTENSIONS`，以 `--background --factory-startup --disable-autoexec --python-exit-code 1 --python` 分别运行 `test_native_material_blender.py` 和 `test_blender_drag.py`。不要针对用户正在使用的配置执行测试。

本轮验证结果随 1.5.0 发布。
