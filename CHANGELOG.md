# 变更日志

## V0.1.0 (2026-07-22)

### 新增
- CSV 导入（拖拽 + 浏览），自动验证 5 列结构 (uptime, node_id, slot, tc, val)
- QTableView 预览前 100 行数据
- 三级设备树（设备类型 → Slot → TC），带颜色标注状态圆点
- 设备自动发现：TC 签名匹配 → S001 种子源 / BC01 电流板
- 标注面板：物理量名称下拉（10 个已知量 + PD_PWR）、单位选择、actual/target/other 类型、训练标记勾选
- "Apply to All Matching" 批量标注功能
- 宽表导出：pivot TC 行为标注列、自动计算 actual−target 偏差列、PD_PWR_mW 预留列（NaN）、目标值前向填充
- 三栏 Qt 布局（左:导入+设备树 / 中:预览+图表+统计 / 右:标注）
- 菜单栏（文件/模板/视图）、工具栏、状态栏含进度条
- 样本 CSV 数据 (sample_mixed.csv)
- 39 个 pytest 单元测试
- VS Code 调试配置 (launch.json)
- PyInstaller 打包配置 (laser_daq.spec)
- Linux/Windows 构建脚本
