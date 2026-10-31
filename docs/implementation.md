# 原理、失败经过和验证边界

## BL 解锁：修改有效配置，不是改一个字节

本机 seccfg 为 V4：前 28 字节是头部，后接 32 字节经 SEJ 处理的 SHA-256 校验，结构共 60 字节。锁定头部字段为 `1/0`，解锁目标为 `lock_state=3`、`critical_lock_state=1`。

实测纯软件路径不匹配，连接手机后用硬件 SEJ 成功匹配 MTKClient 内部名为 V4、`legacy=True` 的变体。候选经独立对象解析验证，只替换原件前 60 字节，保留同一 4 KiB 块中其余内容，实际只写这一个块。完整 8 MiB seccfg 读回必须等于候选首块加原始尾部。

`check_seccfg.py` 公开了只读预检和候选生成的实现；闪存写入由命令清单中明确列出的 MTKClient 手动命令执行。该公开版没有本机私有原型的自动写后回退机制，验证状态见 README。

## 为什么记录清数据

第一次只改 seccfg，写后校验正确，也出现解锁提示，但等待约 8～10 分钟仍卡启动。恢复前发现启动过程在首块内新增包含 `avb.managed_verity_mode` 的持久化记录，脚本停止并重新审查；随后确认启动镜像仍为原厂，再恢复原件，手机正常开机。

第二次候选配置相同，增加了 metadata、userdata、md_udc 的配套清除，最终解锁并正常启动。这支持数据重置与成功有关，未证明具体根因，也未逐个确定三分区的必要性。

上游文档依据：[MTKClient v2.1.4.1，Unlock bootloader](https://github.com/bkerler/mtkclient/blob/v2.1.4.1/README-USAGE.md#unlock-bootloader)。

## Fastboot：调整 preloader 布局及标志

方法来源：[Shocked-Cat / oppo-mtk-fastboot-unlock](https://github.com/Shocked-Cat/oppo-mtk-fastboot-unlock)，脚本署名 Dev. Max_Goblin。

本机 4 MiB BOOT_1：COMBO_BOOT 头、BRLYT 在 `0x200`，代码起点 `0x1000`，ROMINFO 标记在 `0x131C`。

本次固定算法：

1. 将 `[0x1000 : 文件末尾-0x3000]` 原样搬到 `0x2000`。
2. BRLYT 的 `0x20D、0x21D` 写 `0x20`；`0x211、0x212、0x221、0x222` 写 `0x10`。
3. 将原 ROMINFO 的 120 字节复制到 `0x1000`，副本的 `0x104C` 标志写 0。
4. 保持文件 4 MiB，被搬移的原始代码逐字节不变；被舍弃的末尾 12 KiB 必须全零。

因此不是把一个 0x22 改成 0。`q2_tools.py` 先独立计算，再在临时目录运行固定哈希的上游脚本，逐字节比对，并检查最终候选摘要。未知原件和非空尾部均拒绝，没有 force 参数。

本机只写 BOOT_1；BOOT_2、LK、boot、vbmeta、seccfg 保持原样。随后正常 Android 和 Bootloader Fastboot 都验证成功。没有写熔丝，没有实施 LK 修补，也没有进行完整引导链动态追踪。

## 验证结果

```text
Android: RMX2117CN / RMX2117_11_C.17 / Android 11
flash.locked: 0
vbmeta.device_state: unlocked
verifiedbootstate: orange
bootmode: normal
boot_completed: 1

Fastboot version: 0.5
product: oppo6853
unlocked: yes
is-userspace: no
```

连续 6 次版本查询成功。Fastboot reboot 返回 OKAY 后进入关机充电，手动开机恢复桌面。Fastboot 刷分区、Root、UI1.0、其他固件及 OTA 后状态均未验证。

## 公开配置为什么严格

`profiles/RMX2117CN_C17.json` 只包含分区名称/范围、容量和已审查原厂启动文件的摘要，不含 NV 内容、设备唯一标识或本机 seccfg 摘要。它不是每台手机都可刷入的镜像。

其他设备不匹配时，应保留脱敏证据、重新研究，不能通过修改白名单把 STOP 变成 PASS。GUI 显示已连接、USB 有响声和出现英文提示都不能代替真实读回及启动验收。
