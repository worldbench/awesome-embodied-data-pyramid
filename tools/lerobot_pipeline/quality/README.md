# 清洗实现

统一使用仓库根目录的入口运行转换和清洗；本目录是其内部清洗包。

- `src/lerobot_quality/adapters/profiles/`：当前发布范围内的 19 种本体/格式契约。
- `configs/`：14 种可比较格式共用的 12 套 FK 配置，引用随仓库提供的 URDF。
- `robot_models/`：当前 FK 配置需要的 10 份运动学模型。
- `tests/`：观测数据回归、基础检查、缺失信号、逐帧导出和跨文件边界检查。

所有输入、输出、运行目录均由调用者提供，模型路径相对于配置文件解析。此包目前面向源码仓库运行或 editable 安装，模型资源必须与源码一起保留。

## 数据行为

`export_repo` 保留所有源行、所有原字段和视频时间索引，仅向训练数据添加布尔列 `quality.valid`。`False` 只表示该帧未通过本次适用检查，不扩散到整个 episode。元数据会增加对应统计，`videos` 软链接指向调用者指定源仓库的视频。

检查包括有限数值、有效位姿的四元数、mask 是否为 0/1、帧索引连续性、相邻帧突变和已配置的 FK 对比。默认阈值沿用历史发布：关节步长 0.35、位置步长 0.10、旋转步长 30 度；源单位不做重写。FK 比较阈值为位置 0.01 米、旋转 2 度。

FK 只比较有效观测 `state.qpos` 与 `state.ee`。缺少任一字段、EE mask 为 0 或当前本体没有有效的模型/坐标标定时，不将未执行检查判为通过或失败。InternData 三个实机仓库与 Tienkung 14 个仓库的跳过原因保存在报告中；这些数据仍执行所有适用的基础检查。不会用 FK 生成 EE 再自行验证。

输出的 `quality/summary.json`、`quality/episodes.json`、`quality/frames.parquet` 和 `quality/signal/` 保存检查明细、覆盖范围及跳过原因。`fk_checked` 只存在于报告，训练数据不增加 `quality.fk_checked`。训练仍须显式使用原有 action/EE mask。

## 内部接口

```python
from pathlib import Path
from lerobot_quality.export import export_repo

export_repo(Path('data/converted/repository'),
            Path('data/cleaned/repository'),
            adapter='beta_a2d_gripper')
```

批量入口为 `python -m lerobot_quality.batch_export --plan plan.json --run-dir runs/clean --workers 16`；plan 必须由根目录入口生成并约束到发布清单。已有输出只有在来源、数量与导出规则一致时才可恢复，不覆盖不匹配目录。

FK 结果中的 Split Aloha 和部分 Beta 异常在旧发布中仍待复核；本次整理保持原始阈值与结果，不把待复核误差自动宣称为源数据损坏。
