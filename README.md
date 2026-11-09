# Surge tvOS public rule shards

为 Surge tvOS 外部资源校验/索引问题准备的小体积分片，只包含公开规则与构建代码。

| 上游 | 分片数 | 策略 | 来源 |
|---|---:|---|---|
| ChinaMax_Domain | 8 | DIRECT,extended-matching | blackmatrix7/ios_rule_script |
| Sukka reject domainset | 16 | REJECT | SukkaW/Surge |

每片必须小于 500,000 字节；这是本仓库的保守工程上限，不是对 tvOS 5.23.0 限制的官方声明。实际电视能否成功更新须在设备上确认。

## 使用

`surge-snippet.conf` 是用于替换原两个 DOMAIN-SET 引用的公开片段，不是完整配置。

- 将广告分片放在原广告域名集的位置。
- 将 ChinaMax 分片放在原 ChinaMax_Domain 的位置，保留 ChinaMax_Resolve 引用。
- 删除对应两个原始大型 DOMAIN-SET 引用，避免再次下载它们。
- iPhone Surge → 更多 → Surge tvOS，向目标 Apple TV 重新部署修改后的配置。仅修改 iCloud 文件不足以更新电视配置。
- 然后在 Apple TV 远程控制的外部资源中更新，并验证新分片成功。

分片延续原 exact / leading-dot suffix 格式。文件头注释保留上游声明。构建时对原始有效条目与分片并集使用 Counter 精确比较，重复条目也保留。按条目 SHA-256 分桶，原有条目不会因为其他条目的增删跨片移动。

## 更新

GitHub Actions 每日 UTC 20:23（北京时间次日 04:23）运行，也可手动运行。GitHub 调度可能延迟；公共仓库长期无活动时计划任务可能被暂停，需在 Actions 页面重新启用。

```sh
python3 scripts/update_rules.py
```

仅使用 Python 标准库。网络异常、UTF-8/格式异常、条目数量明显缩水或分片超限时不发布。两个源均校验成功后，工作流用一次 Git 提交发布。`manifest.json` 包含源及分片 SHA-256、字节数和实际条目数量；`sources/` 保存对应原始公开快照。

客户端各分片默认每天更新；跨文件不具备客户端事务原子性，更新期间可能短暂混用新旧快照。未来任一分片超限时任务会失败并保留上一版，需增加分片数并同步修改配置；不会静默截断。

## 许可证与来源

- ChinaMax: https://github.com/blackmatrix7/ios_rule_script ，GPL-2.0，详见 `licenses/ChinaMax-GPL-2.0.txt`。
- 广告规则: https://github.com/SukkaW/Surge ，AGPL-3.0，详见 `licenses/Sukka-AGPL-3.0.txt`。各源文件中的其他来源声明一并保留。
- 分片生成器、工作流和本文档采用 AGPL-3.0；规则数据分别保留上游许可证。本仓库不宣称改变上游数据的许可。

修改说明：将域名集按 SHA-256 分成固定小文件，规范行尾并排序，保持有效条目的多重集合不变；附加来源与分片注释。不存放个人完整 Surge 配置、节点订阅或 MITM 证书。
