# CAN 采集 CSV 格式变更 — 上位机适配需求

> 固件版本: `main` 分支 commit (待烧录)
> 上位机: `/home/johnny/Projects/laser-daq-tool`

---

## 1. 背景

固件 `can_collect` 模块架构从"轮询读寄存器"改为"配置 K64 主动上报"。
CSV 窄表格式随之变化。**旧格式的 CSV 不再产生**，上位机必须适配新格式。

---

## 2. 新旧 CSV 格式对比

### 旧格式 (已废弃)
```
uptime,node_id,slot,func,tc,opcode,val_float,val_hex
12345,2,0,RPTCURR,2,8,998.5000,0x44799A00
```
- `tc` 列含义**二义性**: tc=2 在 func=RPTCURR 下是"电流实际值"，在 func=RPTTEMP 下是"温度实际值"
- `func` 列已在旧格式中存在但未被上位机使用
- 主要数据来源是 RPTREGS 响应 (opcode=6/8)

### 新格式 (当前固件)
```
uptime,node_id,slot,func,tp,tp_name,opcode,val_float,val_hex
12345,4,0,RPTCURR,8,I_ACT,0,998.5000,0x44799A00
12345,2,0,RPTTEMP,21,T1,0,25.1000,0x41C8CCCD
12345,2,0,RPTTEMP,24,TEC_DUTY,0,0.7500,0x3F400000
```

### 关键差异

| 项目 | 旧格式 | 新格式 |
|------|--------|--------|
| 类型编码列名 | `tc` | `tp` |
| 值列名 | `val` | `val_float` |
| **类型编码含义** | tc=1~5, 21/24/31/32/33 (二义性) | TP=0~27 (唯一) |
| func 列重要性 | 可选 (有歧义) | **必要** (与 tp 一起唯一确定物理量) |
| tp_name 列 | 无 | `I_ACT`, `T1`, `TEC_DUTY`... (人类可读) |
| 数据来源 | RPTREGS 读响应 (opcode=6/8) | RPTCURR/RPTTEMP **主动上报** (opcode=0) |
| opcode 列 | 6/8 有意义 | 主动上报为 0，RPTREGS 为 6/8 |

### 新增 `tp_name` 列含义
该列**仅供参考/调试**。物理量识别应使用 `func` + `tp` 组合，不依赖 `tp_name` 字符串匹配。

---

## 3. TP 类型码完整映射表

### RPTCURR (func=5) — 电流类主动上报

| TP | tp_name | 含义 | 建议名称 | 建议单位 | 类型 |
|:--:|---------|------|----------|----------|------|
| 0 | RAW | 电流原始值 | C_RAW | mA | ACTUAL |
| 8 | I_ACT | LD 电流采样值 | C_ACTUAL | mA | ACTUAL |
| 9 | LDV | LD 电压 | V_ACTUAL | mV | ACTUAL |
| 10 | PSUMP | 功率 I×V | P_SUMP | mW | ACTUAL |
| 11 | LDP | LD 光功率 | P_LD | mW | ACTUAL |
| 12 | DRIV | 驱动电压 | V_DRIVE | mV | ACTUAL |
| 13 | VCE | VCE 电压 | V_VCE | mV | ACTUAL |
| 14 | I_TGT | 电流目标值 | C_TARGET | mA | TARGET |

### RPTTEMP (func=7) — 温度类主动上报

| TP | tp_name | 含义 | 建议名称 | 建议单位 | 类型 |
|:--:|---------|------|----------|----------|------|
| 0 | RAW | 温度原始值 | T_RAW | C | ACTUAL |
| 21 | T1 | T1 温度采样值 | T1_ACTUAL | C | ACTUAL |
| 22 | T2 | T2 温度/湿度 | T2_ACTUAL | C | ACTUAL |
| 23 | T3 | T3 温度 | T3_ACTUAL | C | ACTUAL |
| 24 | TEC_DUTY | TEC 占空比 | TEC_PWM | (无量纲) | OTHER |
| 25 | TEC_I | TEC 电流 | TEC_I | mA | ACTUAL |
| 26 | TEC_V | TEC 电压 | TEC_V | mV | ACTUAL |
| 27 | TEC_P | TEC 功率 | TEC_P | mW | ACTUAL |

### RPTREGS (func=9, opcode≠0) — 寄存器读响应
这是配置读回的响应，`tp` 列存的是**寄存器地址** (100-107)，不是 TP 类型码。
上位机可**直接过滤掉 func=RPTREGS 的行**，只保留主动上报数据用于标注和训练。

---

## 4. 需要修改的文件

### 4.1 `constants.py` — 常量定义

**REQUIRED_COLUMNS** 改为:
```python
REQUIRED_COLUMNS = ["uptime", "node_id", "slot", "func", "tp", "val_float"]
```

**KNOWN_QUANTITIES** 改为用 `(func, tp)` 作为键:
```python
KNOWN_QUANTITIES: dict[tuple[str, int], KnownQuantity] = {
    ("RPTCURR", 8):  KnownQuantity(8,  "C_ACTUAL",  "mA", DataType.ACTUAL,
                                    func_group="RPTCURR", description="LD电流采样值"),
    ("RPTCURR", 9):  KnownQuantity(9,  "V_ACTUAL",  "mV", DataType.ACTUAL,
                                    func_group="RPTCURR", description="LD电压"),
    ("RPTCURR", 10): KnownQuantity(10, "P_SUMP",    "mW", DataType.ACTUAL,
                                    func_group="RPTCURR", description="功率I×V"),
    ("RPTCURR", 14): KnownQuantity(14, "C_TARGET",  "mA", DataType.TARGET,
                                    func_group="RPTCURR", description="电流目标值"),
    ("RPTTEMP", 21): KnownQuantity(21, "T1_ACTUAL", "C",  DataType.ACTUAL,
                                    func_group="RPTTEMP", description="T1温度采样值"),
    ("RPTTEMP", 24): KnownQuantity(24, "TEC_PWM",   "",   DataType.OTHER,
                                    func_group="RPTTEMP", description="TEC占空比"),
    # ... 按需补充 TP 11,12,13,22,23,25,26,27
}
```

**DEVICE_SIGNATURES** 改为用 `(func, tp)` 签名:
```python
DEVICE_SIGNATURES: dict[frozenset[tuple[str, int]], tuple[str, str]] = {
    frozenset({("RPTTEMP", 21), ("RPTTEMP", 24)}):
        ("S001_Seed_Source", "种子源（温度+TEC）"),
    frozenset({("RPTCURR", 8), ("RPTCURR", 9), ("RPTCURR", 10)}):
        ("BC01_Current_Board", "电流板（电流+电压+功率I×V）"),
    frozenset({("RPTCURR", 8), ("RPTCURR", 9), ("RPTCURR", 10), ("RPTCURR", 14)}):
        ("BC01_Current_Board", "电流板（含目标电流）"),
}
```

### 4.2 `import_worker.py` — 导入解析

- `REQUIRED_COLUMNS` 自动跟 `constants.py` 走，无需改
- `pd.to_numeric` 的列名: `"tc"` → `"tp"`
- `val` → `val_float`
- 增加 `func` 列保留为字符串（不过滤，保留 RPTCURR/RPTTEMP/RPTREGS）
- **建议过滤**: 丢弃 `func == "RPTREGS"` 的行（那些是配置读回，不是测量数据）

```python
# 新增: 过滤掉 RPTREGS 读响应
df = df[df["func"] != "RPTREGS"]
```

### 4.3 `data_model.py` — 数据模型

- `raw_df` 的列注释更新: `tp` 替代 `tc`
- `get_unique_combinations()`: `groupby(["node_id", "slot", "func", "tp"])`
- `get_tc_signature()`: 返回 `frozenset[tuple[str, int]]` (func, tp 对)
- `get_slot_data()`: 增加 `func` 筛选参数（可选）

### 4.4 `device_type.py` — 设备类型发现

- `TypeDetector.discover()`: 构建签名时用 `(func, tp)` 对
- `TypeDetector.classify()`: 签名类型从 `frozenset[int]` 改为 `frozenset[tuple[str, int]]`
- 代码改动示意:
  ```python
  # 旧
  tc_set = frozenset(group["tc"].unique())
  # 新: 过滤掉 RPTREGS 后构建 (func, tp) 签名
  active = group[group["func"] != "RPTREGS"]
  tp_pairs = list(zip(active["func"], active["tp"]))
  signature = frozenset(tp_pairs)
  ```

### 4.5 `annotation.py` — 标注模型

- `Annotation` 类: `tc` 字段重命名为 `tp`，新增 `func_group: str = ""` 字段
- `QuantityCatalog.get_default_annotation(tc)` → `get_default_annotation(func, tp)`
- `target_for_actual()`: 逻辑不变 ("ACTUAL" → "TARGET")，不影响
- `all_names()` / `units_for()`: 更新对 `KNOWN_QUANTITIES` 的遍历

### 4.6 `export_controller.py` — 宽表导出

- `build_wide_table()`: 
  - pivot 时用 `columns=["func", "tp"]` 替代 `columns="tc"`
  - 或者直接只 pivot `"tp"`（因为 func 已经通过过滤保证了）
  - 推荐: 函数入口处 `slot_df = slot_df[slot_df["func"] != "RPTREGS"]` 确保只有主动上报数据

### 4.7 视图层 (低优先级)

- `preview_table.py`: 列名引用更新
- `main_window.py` / `annotation` 面板: 如涉及 `tc` 列名索引，需同步更新

---

## 5. 兼容性建议

导入时对旧格式 CSV 做兼容检测：

```python
def detect_format(df: pd.DataFrame) -> str:
    if "tc" in df.columns and "val" in df.columns:
        return "v1_old"
    elif "tp" in df.columns and "val_float" in df.columns:
        return "v2_new"
    else:
        raise ValueError("Unknown CSV format")
```

如果保留 `v1_old` 兼容，只需做一个适配函数把旧列名映射到新列名并补充 `func` 默认值。

---

## 6. 测试数据

新固件烧录后，MCXN947 连接 K64 设备运行，生成的 CSV 示例:

```csv
uptime,node_id,slot,func,tp,tp_name,opcode,val_float,val_hex
5234,2,0,RPTTEMP,21,T1,0,25.1000,0x41C8CCCD
5234,2,0,RPTTEMP,24,TEC_DUTY,0,0.7500,0x3F400000
5734,4,0,RPTCURR,8,I_ACT,0,998.5000,0x44799A00
5734,4,0,RPTCURR,9,LDV,0,2450.0000,0x45192000
5734,4,0,RPTCURR,10,PSUMP,0,2445.0000,0x4518D000
5734,4,0,RPTCURR,14,I_TGT,0,1000.0000,0x447A0000
```

完整的 `/NAND:/collect/` 可通过 USB MSC 挂载后获取。
