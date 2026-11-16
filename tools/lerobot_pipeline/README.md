# LeRobot Release Pipeline


开源整理版：转换、四项清洗、断点恢复与验收。快速开始使用 `configs/example.alpha10.json`；旧规则仍可显式使用 `configs/example.json`。

- [使用示例](docs/QUICKSTART.md) · [模型资源](docs/ASSETS.md) · [第三方说明](THIRD_PARTY_NOTICES.md)
- [历史验证](VALIDATION.md) · [本次发布检查](docs/RELEASE_VALIDATION.md)

从原始数据重建当前使用的 **1,721 个 LeRobot v3 仓库**，再执行本体适配与逐帧质量检查。转换和清洗各有独立入口，也可以一条命令串联。所有数据位置来自配置，仓库不绑定某台机器或某个挂载路径。

本仓库保留当前版本的数据语义及异常处理，不借重构改变关节顺序、单位、EE 定义、腰部字段或清洗阈值。输入必须是同一版本的完整原始目录，包括配套索引、说明和标注文件。`manifests/repositories.json` 是精确范围：少一个、多一个、帧数或字段不符都会校验失败。它不是“处理任何版本原始数据都固定得到这个数量”的工具。

## 范围与输出

| 家族 | 仓库数 | 轨迹数 | 数据小时数 | 清洗说明 |
|---|---:|---:|---:|---|
| AgiBot Beta | 202 | 153,689 | 2,539.82 | gripper / dexhand 按 task_id 分仓，包含腰部 |
| ABC-130k | 2 | 107,648 | 2,716.32 | train / val 分仓；只对有效 EE 做 FK |
| AgiBotWorld2026 | 4 | 31,017 | 621.92 | 四种已发布 schema 分仓 |
| Galaxea Lite / Pro | 2 | 19,105 | 462.33 | state.waist；Lite 另含 action.waist_velocity |
| InternData A1 | 1,476 | 593,663 | 3,701.47 | 仿真 1,473 + 实机 3；实机跳过不可用 FK |
| RoboMIND | 35 | 67,202 | 165.70 | Franka、FR3 Dual、UR、Tienkung；Tienkung 无观测 EE，跳过 FK |
| **总计** | **1,721** | **972,324** | **10,207.57** | **1,077,451,809 帧** |

不包含 RoboMIND AgileX、RoboMIND 仿真及其他数据家族的转换/清洗策略。转换过程中明确排除的损坏源或未发布任务也不会悄悄补进当前版本。

```text
lerobot_release_pipeline/
├── pipeline.py                 # 唯一对外入口
├── pipeline/                   # 参数、生命周期、范围校验和阶段编排
├── configs/
│   ├── example.json            # 路径与并行度示例
│   ├── release.json            # 六个家族的版本与异常策略
│   └── runtime-versions.json   # 历史成功运行环境的观测版本
├── manifests/
│   └── repositories.json       # 1,721 个仓库相对路径、计数及去重 schema
├── converters/                # 六家转换引擎及必要共享模块
│   ├── abc130k2lerobot/
│   ├── agibotworld_beta_2lerobot/
│   ├── agibotworld2026_2lerobot/
│   ├── interndata_a1_2lerobot/
│   ├── opengalaxea2lerobot/
│   ├── robomind2lerobot/
│   ├── agibot2lerobot/         # Beta 使用的共用读取/写入层
│   └── generic_converter/     # 分块、视频与任务汇总
├── quality/                   # adapter → 共用检查 → 标记导出
│   ├── src/lerobot_quality/
│   ├── configs/               # 已启用的 FK 配置
│   ├── robot_models/          # 本地导入的 FK 模型（不纳入 Git）
│   └── tests/
└── tests/                     # 转换、编排和复现边界测试
```

引擎保留内部模块名，是为了保留已经验证的数据映射和恢复行为；使用者只需要根目录入口。

## 环境与路径

推荐使用 Linux、Python 3.12、FFmpeg 7，并准备 `ffmpeg`、`ffprobe`、`bash`、`flock`。TorchCodec 还需要可动态链接的 FFmpeg 库，只有静态 `ffmpeg` 可执行文件并不足够。

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-runtime.txt
python -m pip install -r requirements-test.txt
cp configs/example.alpha10.json configs/local.json
```

`requirements-runtime.txt` 固定的是此前成功运行环境观测到的包版本，不是对所有操作系统都验证过的依赖锁文件。无需安装旧仓库；FK 模型不包含在公开源码中；先按 `docs/ASSETS.md` 导入具有使用权限的模型。

编辑 `configs/local.json`：

```json
{
  "raw_root": "../data/raw",
  "converted_root": "../data/converted",
  "cleaned_root": "../data/cleaned",
  "work_root": "../data/work",
  "conversion_workers": 8,
  "cleaning_workers": 16,
  "ffmpeg": "ffmpeg",
  "batch_size": 65536
}
```

所有相对数据路径均相对于**配置文件所在目录**，与启动时的工作目录无关。四个根目录必须互不重叠。默认使用运行入口的 Python；如需指定其他解释器，可增加 `python` 字段。FFmpeg 可填写 PATH 中的命令名或配置文件相对路径。运行生成的日志、清单、软链接会记录实际解析的路径；这些运行产物不属于可移植源码。

原始目录应具有以下结构，保留各数据集内配套文件：

```text
raw/
├── AgiBot-World-Beta/           # task_info、parameters、HDF5/RGB 归档等
├── ABC-130k/                   # train/val 原始 MCAP
├── AgiBotWorld2026/            # ImitationLearning / RL / RichInteraction / simulation
├── Galaxea-Open-World-Dataset/  # lerobot_opensource 中原始归档
├── InternData-A1/              # 原始仿真/实机目录及其元数据
└── RoboMIND-v1.2/              # 归档 + static 指令/语言标注/允许修复列表
```

RoboMIND 的 `static` 配套标注参与任务名称、split 和相机修复，不能仅复制 HDF5。Beta 会重新检查缺失文件、空文件及 LFS 占位文件，生成准备审计。

## 从原始数据开始

先检查依赖，再查看计划。以下两步不启动转换或清洗：

```bash
python pipeline.py doctor --config configs/local.json
python pipeline.py plan --config configs/local.json
```

一条命令完成转换、版本校验、清洗和清洗输出校验：

```bash
python pipeline.py run --config configs/local.json --execute
```

后台运行：

```bash
tmux new -s lerobot-release
python pipeline.py run --config configs/local.json --execute
# 按 Ctrl-b 再按 d，离开会话；任务继续执行。
```

分阶段或只执行某个家族：

```bash
python pipeline.py convert --config configs/local.json --dataset beta --execute
python pipeline.py clean --config configs/local.json --dataset beta --execute --resume
```

家族名为 `beta`、`abc`、`agibot2026`、`galaxea`、`interndata`、`robomind`；默认 `all`。`convert`、`clean`、`run` 不带 `--execute` 时只打印计划。

断点续跑使用同一配置并加 `--resume`：

```bash
python pipeline.py run --config configs/local.json --execute --resume
```

入口仅写入新的目录或自身创建且运行身份一致的目录，拒绝覆盖非空的未知输出。原始数据只读。配置中的根路径、复现策略或清单发生变化时，应使用新输出/工作目录。执行失败会保留检查点和审计；未知源错误会使阶段失败，不会自动扩大跳过范围。清洗以完整仓库为恢复单位：已成功输出直接校验复用，失败仓库重跑，暂存目录不会冒充完成结果。

## 清洗语义

流程为：转换结果 → 本体 adapter → 基础检查 → 可执行的 FK 对比 → `quality.valid`。

- 基础检查包含 NaN/Inf、有效 EE 的数值与四元数、mask 是否为 0/1、附加字段、帧索引连续性及相邻帧突变。
- 突变阈值沿用原版本：关节差 0.35、EE 位置差 0.10、旋转差 30°。数值保留源尺度，未按 FPS 重标定阈值。
- FK 仅在 joint、有效 EE、已验证模型和坐标映射都具备时参与判定；位置阈值 0.01 m、旋转阈值 2°。某侧 mask 为 0 则跳过该侧。没有观测 EE 的仓库记录跳过原因，不判成失败或通过。
- 不强制要求每帧 action 或 EE 都可用；训练仍应使用原始 action/EE mask。
- 不删除帧，不修改原字段、轨迹索引、时间戳和视频偏移。训练数据只新增布尔列 **`quality.valid`**，不新增 `quality.fk_checked`。
- 视频目录软链接到转换输出。原转换目录需保持可访问；移动数据时需要一并维护软链接。

Split Aloha 三个连续抓放仿真仓库及部分 Beta 仓库存在高 FK 失败率，仍待复核模型/坐标定义。本次重构保持原判定；不可把所有 FK 失败直接当成已确认坏数据。

## 输出、异常策略与验收

```text
converted/                     # manifests 中的相对仓库路径
cleaned/                       # 相同相对仓库路径
  <repository>/
    data/                      # 原列 + quality.valid
    meta/                      # v3 元数据与质量标记统计
    quality/                   # 逐帧/逐轨迹报告、覆盖范围和跳过原因
    videos -> converted 中对应的 videos
work/
  conversion/                  # 源审计、临时分块、转换日志及完成标记
  cleaning/<family-selection>/ # plan.json、status.json、results.jsonl、jobs/
```

沿用的异常策略：

| 家族 | 必须保留的处理 |
|---|---|
| Beta | 缺失/空/LFS 源审计；保留仅全零的空索引末端动作并置 mask=0；空任务跳过；按 task_id 汇总；腰部不丢失 |
| ABC | 对齐校验及跳过报告；缺 EE 填有限占位并置 mask=0；train/val 分离；未完成汇总先保留备份再续跑 |
| AgiBot2026 | 保持 fast 收集、schema 分组和视频兼容层；不导出旧版本未使用的深度覆盖图 |
| Galaxea | 显式排除烧水时间戳异常包；Lite/Pro 精确来源选择；保留腰部/腰部速度 |
| InternData | 两个失败 job 排除；第三个失败 job 仅保留 basket/bowl/dish/flower_pot 四个已发布子集 |
| RoboMIND | 七种本体白名单；已知截断源任务排除；相机修复、split 映射、单包故障隔离；其他失败不当作成功 |

只读校验：

```bash
python pipeline.py verify --config configs/local.json --kind converted
python pipeline.py verify --config configs/local.json --kind cleaned
python -m pytest
```

校验依据清单中的相对路径、schema、轨迹数、帧数、FPS、发布标记；清洗还检查完成报告和视频链接。它不逐帧解码所有视频，也不宣称视频字节完全一致。若只读核对混放其他数据的既有目录，可在 `verify` 时显式加 `--allow-extra`；该选项不能用于执行写入。

验证记录及有限样本覆盖范围见 `VALIDATION.md`。本次整理不重跑全量生产数据。

## 四项逐帧清洗（alpha10）

旧版规则仍是默认行为；新版配置在 `configs/four_rules.json`。单仓库运行：

```bash
PYTHONPATH=quality/src python -m lerobot_quality.export \
  --repo "$CONVERTED_REPO" --output "$NEW_CLEANED_REPO" \
  --four-rules-config configs/four_rules.json
```

统一入口的运行配置可以添加 `"four_rules": {}` 使用新版默认参数，或把
`configs/four_rules.json` 的内容填入该对象来覆盖参数。批处理 plan 同样支持顶层
`four_rules` 对象。没有该字段时维持旧规则；新版输出的续跑必须匹配全部新版参数。
**alpha10 的独立全量清洗已完成：1721 个仓库，清洗与验收退出码均为 0。旧 α=5 输出保留。**

四类检查均只将命中帧的 `quality.valid` 设为 false，不删帧、不改视频索引、不重编码。
视频目录软链接到输入仓库；输入仓库必须保留。原有数值、mask 和索引检查继续作为
基础有效性检查，另增加 timestamp 有限且 episode 内递增检查。

| 检查 | 新版规则 |
|---|---|
| 相邻帧突变 | 用真实 timestamp 计算一阶速度和二阶加速度；非等间隔的加速度用两段速度的时间中点差。各仓库、各通道的绝对速度/加速度独立取 q01/q99，上界为 q99 + motion_alpha × (q99−q01)，默认 10。episode 首帧、断帧、无效 mask 不跨越求差。 |
| FK 一致性 | 沿用本体模型及坐标配置，位置 1 cm、旋转 2°；缺少 joint/EE 或 EE mask 无效则跳过，并在报告记录覆盖，不新增数据列 `quality.fk_checked`。 |
| 极值过滤 | 每仓库、每通道对有限且 mask 有效的样本求精确线性插值 q01/q99，边界严格为 [q01−α×(q99−q01), q99+α×(q99−q01)]，α 默认 10；等于边界保留，不附加 margin。 |
| State–Action | 比较同一顺序的 state/action 机械臂关节位置；5 帧中心均值平滑后求速度，episode 内搜索 ±15 帧，选整体方向一致率最高的延迟。某帧至少 2 个关节在两端都超过 0.01 rad/s 时才比较，方向一致率低于 0.5 标记该 action 时刻帧无效。缺失、静止、平滑窗口边缘或 mask 无效时跳过。 |

极值检查覆盖机械臂关节、EE xyz 及腰部/附加数值字段；不对夹爪、灵巧手和四元数分量
使用关节极值规则。旋转突变采用最短弧旋转向量，四元数 q/−q 等价；角速度在观测
公共坐标系中计算。原生速度字段只检查数值/极值，不将其当位置再次求速度。
Galaxea 的 `state.waist[4]` 与 `action.waist_velocity[6]` 不做 State–Action 配对。

这些默认值是本项目的候选实现参数，**不是论文全部算法的逐项复现**：未加入论文的
整 episode 拒绝、边界静止裁剪或短轨迹移除。极值公式按用户确认实现；速度/加速度
分位数阈值和逐帧方向判定已用于本项目 alpha10 输出，但并不保证适用于任意数据集。

`quality/signal/frames.parquet` 保存四项非 FK 子检查及覆盖标记；
`quality/frames.parquet` 保存合并结果和 FK 明细。
`quality/signal/bounds.json` 保存每通道样本数、分位数和上下界；
`quality/signal/state_action_episodes.json` 保存延迟选择及跳过原因。
`quality/summary.json` 保存新版参数和 FK 命中数。
各算子命中可能重叠，不能相加当作最终过滤率。

精确分位数用磁盘临时通道文件，不随机抽样；每次只加载一个通道分区计算。
临时数据放在新输出 staging 内，成功校准后删除。最大单通道内存约为有效帧数 × 8 bytes，
并行数需据此控制；完整 episode 在内存处理，超过 200 万帧时报错，不发布不完整输出。
该流程读取源 Parquet 四次（基础检查、统计、应用规则、输出/FK），不可沿用旧两遍流程的 ETA。

2026-11-03：按用户要求将 `alpha` 与 `motion_alpha` 同时改为 10；FK 和 State–Action 参数不变。2026-11-02 smoke 报告仍记录当时 α=5 的历史结果，不能作为 α=10 的命中统计。
