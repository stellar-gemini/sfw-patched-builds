# SFW Windows x64 私有构建

这是基于官方 sing-box 发布版的自用 Windows 客户端，包含 [SagerNet/tailscale PR #12](https://github.com/SagerNet/tailscale/pull/12) 的 UDP 绑定恢复修复。

[下载页面](https://github.com/stellar-gemini/sfw-patched-builds/releases)随官方稳定版更新。GitHub Actions 每 6 小时检查一次。也可以在 [Actions](https://github.com/stellar-gemini/sfw-patched-builds/actions/workflows/windows.yml) 手动运行，填写一个已有官方 x64 安装包的版本标签（例如 `v1.15.0-alpha.13`）。手动构建官方预览版会在本仓库标为预发布版。

下载 `SFW-<版本>-x64-pr12.exe`。首次安装前，将发行页的 `SFW-Patched-Code-Signing.cer` 的 SHA-256 与下文指纹比较，确认一致后，将此公钥证书导入 Windows **本地计算机 → 受信任的根证书颁发机构**。后续同一证书签名的版本可以复用这个信任。安装前也可用 `Get-AuthenticodeSignature -FilePath <安装包>` 核对签名状态和签名者。客户端内置的官方更新入口已关闭，升级时使用本仓库的发行页。

构建使用官方标签锁定的 GUI、dashboard 和 Go 依赖。流水线比对 `go.sum`，在该版本实际使用的 Tailscale 依赖上应用已固定的 PR 补丁，再运行 UDP 恢复回归测试。补丁冲突、测试失败、签名无效或 daemon 没有使用补丁后的依赖时，构建失败且不会发布。已有同版本、同官方提交、同补丁的成功产物时，定时任务跳过构建。

每个发行版包含安装包、证书公钥、`SHA256SUMS.txt` 及 `build-info.json`。清单记录上游源码提交、补丁校验值和构建记录。私钥只用于该仓库的 Actions Secrets。GitHub 保存的产物属于个人构建，使用仓库访问权限管理。

专用证书 SHA-256：`4880F36AE06B4E32E8A7C563628EC532FF7923AF38F2DE6B462888F638047C54`
