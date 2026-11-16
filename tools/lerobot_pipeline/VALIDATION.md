# 验证记录 — 2026-10-26

本次重构以原转换主仓库提交 `9d82954` 和当前工作树中的清洗实现为基线。旧仓库和生产数据未修改，未重跑全量转换或清洗。

## 已执行的验证

- Linux/Python 3.12 实际 LeRobot 运行环境：整套 `pytest` **226 项通过，另有 8 个 subtests 通过**。
- 其中转换回归 88 项、清洗 122 项、统一入口 16 项。
- 六类转换 CLI、清洗 CLI、FFmpeg、ffprobe 的 `doctor` 检查通过。
- 已有正式转换和清洗输出的只读校验通过：**1,721 仓库 / 972,324 轨迹 / 1,077,451,809 帧**。
- 校验具体相对路径、26种 schema、轨迹/帧数、FPS、发布标记；清洗还检查完成报告和视频软链接目标。
- 已测规划不写入、未知非空目录拒绝、首次运行、匹配身份续跑、不同工作目录争用同一输出的锁、错误 schema/数量和错误视频链接拒绝。
- Python/JSON 语法、ABC Bash 语法检查通过；代码/配置未包含机器绑定的绝对数据路径。

## 真实原始样本端到端验证

这些样本经过新仓库的转换引擎和新清洗包。不是直接拿旧的转换输出跳过转换步骤。

| 原始样本 | 轨迹 | 帧数 | FK 受检帧 | FK 失败帧 | quality.valid=false |
|---|---:|---:|---:|---:|---:|
| Beta task_327：原始 tar → prepare_raw → 按 task 汇总 | 1 | 1,307 | 1,307 | 0 | 0 |
| ABC：arrange_the_flowers_into_the_vase，单 MCAP | 1 | 3,329 | 0 | 0 | 0 |
| Galaxea R1-Lite：原始格式样本 | 1 | 132 | 132 | 0 | 0 |
| Galaxea R1-Pro：原始格式样本 | 1 | 469 | 469 | 0 | 0 |
| AgiBotWorld2026：RL task_6671 | 1 | 394 | 394 | 0 | 0 |
| InternData Franka：close_the_washingmachine_left | 107 | 32,774 | 32,774 | 0 | 24 |
| RoboMIND UR：put_bread_in_pot，最小包中单条轨迹 | 1 | 209 | 209 | 0 | 0 |
| **合计** | **113** | **38,614** | **35,285** | **0** | **24** |

ABC 样本的 EE mask 无效，因此 FK 跳过而不误判失败。InternData 的 24 帧来自原有突变规则，不是执行错误。小样本验证不等于整个数据集的 FK 全部通过。

各输出验证帧数和 episode 数不变、仅新增 `quality.valid`、视频软链接正确。Beta/ABC/Galaxea 检查清洗前后全部原列相等；另三家检查原列前128帧相等。随后使用 `LeRobotDataset(video_backend="pyav")` 分别读取7份清洗样本的首、中、末帧及其所有视频通道，全部通过。G2 原版本深度字段缺少 depth_unit 元数据，读取器按源值返回；本次未改动其单位语义。

## 可移植性与边界

跨 Mac/Linux 传输发现过 AppleDouble 隐藏旁车文件混入 JSON 配置目录，已清理交付内容、禁止打包这些文件，并添加忽略隐藏 profile 文件的回归测试。

清单中少数 InternData 历史仓库名包含 `mnt` 或 `home` 中间目录成分，完整保留的是**相对仓库标识**，不是机器路径配置；它们仍解析到用户指定的 converted/cleaned 根目录下。

安装版本来自此前成功运行环境。尚未在全新空白系统中重新安装所有依赖，也没有从空目录重新计算10,207小时数据，因此不宣称全量重建或视频字节级一致已再次实测。已保留的复现保证是：同版本原始数据、适配运行环境、原数据映射与异常边界、精确范围/数量/schema门禁，以及上述真实样本链路。

Split Aloha 连续抓放三仓库及部分 Beta 高 FK 失败率仍需模型/坐标复核。重构未放宽阈值，也未擅自把这些帧改判通过。

## 2026-11-02: four-rule candidate cleaning smoke

No full-release cleaning was started. Existing data and cleaned outputs were preserved. The source repository was archived before editing.

Local quality/pipeline suite: 170 passed. Remote full suite: 239 tests and 8 subtests passed before the final 19-profile parameterized addition; the final dedicated four-rule suite (32 tests, including all 19 profiles) also passed remotely.

Real smoke: seven repositories, 113 episodes, 38,614 frames. All original Parquet columns compared equal; row counts/indexes retained and each video directory verified as a symlink to its input. Total export wall time across sequential jobs: 20.93 seconds; small warm-cache fixtures are not a full-release throughput benchmark.

| Adapter | Frames | Range failures | Velocity failures | Acceleration failures | State–Action failures | FK failures | Union invalid |
|---|---:|---:|---:|---:|---:|---:|---:|
| abc_yam_bimanual_2x6dof | 3329 | 0 | 0 | 0 | 2 | 0 | 2 |
| galaxea_r1lite | 132 | 0 | 0 | 0 | 1 | 0 | 1 |
| galaxea_r1pro | 469 | 0 | 0 | 0 | 0 | 0 | 0 |
| beta_a2d_gripper | 1307 | 0 | 0 | 0 | 0 | 0 | 0 |
| agibot2026_g2a | 394 | 1 | 5 | 0 | 4 | 0 | 9 |
| interndata_franka | 32774 | 0 | 76 | 239 | 0 | 0 | 239 |
| robomind_ur_1rgb | 209 | 0 | 0 | 0 | 0 | 0 | 0 |

Union: 251 invalid frames (0.6500%). Operator counts overlap. ABC has no valid EE in this fixture, so FK was skipped; the UR fixture had no jointly moving valid state/action joint pairs, so State–Action was skipped. Neither is reported as a passed comparison. All 19 adapter formats were covered by synthetic export regression tests; only the seven listed formats were exercised on these real smoke datasets. Bounds fit on smoke data differ from future full-repository bounds.

Machine-independent numeric results: `quality/references/four_rules_smoke_20261102.json`. The candidate parameters and policy limitations are documented in README. No commit or full-release launch was performed.
