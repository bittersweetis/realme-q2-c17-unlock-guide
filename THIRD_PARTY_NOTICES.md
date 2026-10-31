# 第三方来源与许可

本项目自己的文档、配置和辅助脚本按 AGPL-3.0-only 发布，保留来源与本许可证。`q2_tools.py` 中 preloader 布局算法由下列上游方法改写。

| 项目 | 来源 | 处理方式 |
|---|---|---|
| preloader 算法 / 固定脚本 | https://github.com/Shocked-Cat/oppo-mtk-fastboot-unlock ，脚本署名 Dev. Max_Goblin | 原脚本不改动，SHA-256 f9308e21b65be38dca9fe46e86373690c709a42807612bc493f608e38fe61d7f；保留 AGPL-3.0 许可证 |
| MTKClient | https://github.com/bkerler/mtkclient/releases/tag/v2.1.4.1 | Windows 包从干净原始 ZIP 提取；保留原项目 GPL 许可证及原始版权，源码包由安装脚本从官方固定标签取得 |
| Python | https://www.python.org/ | Windows 包保留 PSF 等许可于 runtime/LICENSE.txt；本机版本 3.13.15 x64 |
| Python 依赖 | requirements-cli.txt；Windows 包另保留安装时的全部 dist-info / LICENSE | 各依赖仍按其原有许可证提供，没有改为本项目的许可 |
| Android platform-tools | https://developer.android.com/tools/releases/platform-tools | Windows 包保留 NOTICE；工具不是本项目原创代码 |
| UsbDk | https://github.com/daynix/UsbDk/releases/tag/v1.00-22 | 官方签名 x64 安装包；源代码和许可由原项目提供 |
| MediaTek Fastboot 驱动 | https://www.catalog.update.microsoft.com/ScopedViewInline.aspx?updateid=67446b50-e7f8-454a-9155-f48ddf362d01 | 原始 CAB、INF、CAT 及附属 DLL；厂商驱动不因本项目而变为开源 |

Windows 配套包是这些原始依赖和本项目的集合，顶层 AGPL 许可证不覆盖各独立依赖的不同许可。再次分发应保留各自条款；若仅托管开源代码，上传源码包即可，依赖可由官方来源取得。

本地完整配套文件夹可以另存实测厂商回退原包于 `firmware/`，它不是本项目开源代码，不适用顶层 AGPL，默认排除在 Git 提交之外。固件取得方式和系统兼容性仍须由使用者确认。不包含个人手机备份或提取出的手机刷机镜像。
