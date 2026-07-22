# 变更日志

## V0.2.0 (2026-07-22)

### 变更 — CSV V2 格式适配 (固件 K64 主动上报)

**破坏性变更** — 不再兼容旧 V1 CSV 格式（tc/val 列）。

#### CSV 列变更
- 类型编码列: `tc` → `tp`，新增 `func` 功能组列 (RPTCURR/RPTTEMP/RPTREGS)
- 值列: `val` → `val_float`
- 自动过滤 `func=RPTREGS` 行（寄存器读响应，非测量数据）
- 必需列: 6 列 (uptime, node_id, slot, func, tp, val_float)

#### 物理量映射
- 键: `int(tc)` → `tuple[str, int](func, tp)` 组合键，消除二义性
- 新增 TP: 0(C_RAW), 11(P_LD), 12(V_DRIVE), 13(V_VCE), 22(T2), 23(T3), 25(TEC_I), 26(TEC_V), 27(TEC_P)
- 默认名称更新: T_ACTUAL_1 → T1_ACTUAL, PWR_mW → P_SUMP

#### 标注模型
- Annotation: 新增 `func_group` 字段，`tc` 重命名为 `tp`
- 标注键: `(node_id, slot, func_group, tp)` 四元组
- 标注面板: 支持用户自定义名称(如 LD2_C_ACTUAL)区分不同通道

#### 导出
- 偏差配对: 改为基于数据类型(ACTUAL↔TARGET)配对，支持自定义名称

#### 设备树
- 叶子节点: `tc=N` → `{func_group} tp={N}` 格式

#### 测试
- 44 个 pytest 测试全部通过

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
