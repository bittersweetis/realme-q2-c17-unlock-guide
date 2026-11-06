# C.17 回退包（与开源代码分开）

从 [GitHub Releases 下载两份附件](https://github.com/bittersweetis/realme-q2-c17-unlock-guide/releases/tag/firmware-c17-rollback)，按发布页命令合并成 `oplus_ota_downgrade.zip`。合并后核对下方大小和 SHA-256。

本地完整配套目录保存 `oplus_ota_downgrade.zip`。它是实测 UI3 → UI2 外层原包的原样复制，仅改名，并非新压缩文件或本项目编写的代码。

原始文件名：`realme UI3.0 真我Q2降级2.0回退包.zip`。

- 大小：3,997,003,120 字节。
- SHA-256：`1313770a2618a2b4037e8b1e297cbc07a07790a7fe838fa957f85a2294add646`。
- 实测：RMX2117CN / F.12 / Android 12 → C.17 / Android 11。
- 放到手机时：`/sdcard/oplus_ota_downgrade.zip`，使用完整外层 ZIP。

先按 [详细降级教程](../docs/rollback.md)核对和操作。

固件属于厂商文件，不适用项目的 AGPL 许可。Git 默认排除本目录除 README 外的文件。
