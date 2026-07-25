# Awesome Embodied Data [![Awesome](https://cdn.rawgit.com/sindresorhus/awesome/d7305f38d29fed78fa85652e3a63e154dd8e8829/media/badge.svg)](https://github.com/sindresorhus/awesome) [![PR's Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat)](#)

<p align="center">
  <img src="assets/data_pyramid.png" alt="Embodied Data Pyramid" width="100%">
  <br>
  <a href="assets/data_pyramid.pdf">High-resolution PDF</a>
</p>

This repository accompanies a survey on the **data pyramid** for robotics and embodied AI. It curates the datasets, data-collection paradigms, simulators, and data-hungry model families reviewed in the survey — spanning **real-robot data**, **UMI (in-the-wild) data**, **egocentric / ego-exo human data**, **simulation data**, and broad **general (web-scale) data** — together with the **VLA / world-action / embodied-VLM** models that consume them. Each entry links to its paper, project page, and code where available.

> If you have suggestions for new resources, improvements to methodologies, or corrections for broken links, please don't hesitate to open an issue or submit a pull request. Contributions of all kinds are welcome and greatly appreciated.

## Table of Contents

<details open>
<summary><strong>Data Sources</strong></summary>

- [The Data Pyramid: Data Sources](#the-data-pyramid-data-sources)

<details open>
<summary>Real-Robot Data</summary>

- [Section: Real-Robot Data](#real-robot-data)
- [Table: Recent real-robot datasets](#table-real-robot-recent)
- [Table: Real-robot datasets (2024 and earlier)](#table-real-robot-2024-and-earlier)

</details>

<details open>
<summary>UMI Data</summary>

- [Section: UMI Data](#umi-data)
- [Table: UMI-style robot-free and cross-embodiment datasets](#table-umi-data)

</details>

<details open>
<summary>Egocentric & Ego-Exo Data</summary>

- [Section: Egocentric & Ego-Exo Data](#egocentric--ego-exo-data)
- [Table: Recent egocentric and ego-exo datasets](#table-egocentric-ego-exo-recent)
- [Table: Egocentric and ego-exo datasets (2024 and earlier)](#table-egocentric-ego-exo-2024-and-earlier)

</details>

<details open>
<summary>Simulation Data</summary>

- [Section: Simulation Data](#simulation-data)
- [Table: 3D assets and scene datasets](#table-simulation-assets-scenes)
- [Table: Simulation and rendering backends](#table-simulation-rendering-backends)
- [Table: Simulation benchmarks](#table-simulation-benchmarks)
- [Table: Simulation/synthetic datasets and data-generation systems](#table-simulation-synthetic-datasets)
- [Table: World models as simulators](#table-world-models-as-simulators)

</details>

<details open>
<summary>General Data</summary>

- [Section: General Data](#general-data)
- [Table: Visual data](#table-general-visual-data)
- [Table: Segmentation and localization data](#table-general-segmentation-localization)
- [Table: Video and temporal data](#table-general-video-temporal)
- [Table: Planning and task decomposition data](#table-general-planning-task-decomposition)
- [Table: Grasp data](#table-general-grasp-data)

</details>

</details>

<details open>
<summary><strong>Embodied Foundation Models</strong></summary>

- [Section: Embodied Foundation Models](#embodied-foundation-models)
- [Table: Representative VLA and WAM methods](#table-embodied-foundation-models-vla-wam)

</details>

- [Contributing](#contributing)

## The Data Pyramid: Data Sources

### Real-Robot Data

<details open id="table-real-robot-recent">
<summary>Table: Recent real-robot datasets</summary>

| Year | Dataset | Paper | Scale | Venue | Project | Repo@GitHub |
|------|---------|-------|-------|-------|---------|-------------|
| 2026 | ABC-130K | [Scalable Behavior Cloning with Open Data, Training, and Evaluation](https://arxiv.org/pdf/2606.27375) | 130.7K trajectories |  | [![link](https://img.shields.io/badge/Website-9cf)](https://abc.bot/) | [![GitHub](https://img.shields.io/badge/GitHub-ABC--130K-ff8800?logo=github)](https://github.com/amazon-far/abc) |
| 2026 | AgiBot World 2026 | AgiBot World 2026: Real-World Embodied Intelligence Dataset |  |  | [![link](https://img.shields.io/badge/Website-9cf)](https://huggingface.co/datasets/agibot-world/AgiBotWorld2026) |  |
| 2026 | DECO-50 | [DECO: Decoupled Multimodal Diffusion Transformer for Bimanual Dexterous Manipulation with a Plugin Tactile Adapter](https://arxiv.org/abs/2602.05513) | 8K trajectories | ICML | [![link](https://img.shields.io/badge/Website-9cf)](https://baai-humanoid.github.io/DECO-webpage/) | [![GitHub](https://img.shields.io/badge/GitHub-DECO-ff8800?logo=github)](https://github.com/BAAI-Humanoid/DECO) |
| 2026 | Dexora | [Dexora: Open-source VLA for High-DoF Bimanual Dexterity](https://arxiv.org/abs/2605.18722) | 12.2K trajectories | ICRA |  | [![GitHub](https://img.shields.io/badge/GitHub-Dexora-ff8800?logo=github)](https://github.com/ZZongzheng0918/Dexora) |
| 2026 | HapTile | [HapTile: A Haptic-Informed Vision-Tactile-Language-Action Dataset for Contact-Rich Imitation Learning](https://arxiv.org/abs/2606.04825) | 1.7K trajectories | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://haptile-dataset.github.io) |  |
| 2026 | LET-Base-Dataset | LET-Base-Dataset: LET Basic Operation Dataset | 92.6K trajectories |  | [![link](https://img.shields.io/badge/Website-9cf)](https://www.modelscope.cn/datasets/lejurobot/LET-Base-Dataset) |  |
| 2026 | MolmoAct2-BimanualYAM  | [MolmoAct2: Action Reasoning Models for Real-world Deployment](https://arxiv.org/abs/2605.02881) | 34.5K trajectories | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://huggingface.co/datasets/allenai/MolmoAct2-BimanualYAM-Dataset) | [![GitHub](https://img.shields.io/badge/GitHub-MolmoAct2-ff8800?logo=github)](https://github.com/allenai/molmoact2) |
| 2026 | MolmoAct2-SO100/101  | [MolmoAct2: Action Reasoning Models for Real-world Deployment](https://arxiv.org/abs/2605.02881) | 38K trajectories | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://huggingface.co/datasets/allenai/MolmoAct2-SO100_101-Dataset) | [![GitHub](https://img.shields.io/badge/GitHub-MolmoAct2-ff8800?logo=github)](https://github.com/allenai/molmoact2) |
| 2026 | OmniViTac | [OmniVTA: Visuo-Tactile World Modeling for Contact-Rich Robotic Manipulation](https://arxiv.org/abs/2603.19201) | 21.9K trajectories | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://mrsecant.github.io/OmniVTA/) | [![GitHub](https://img.shields.io/badge/GitHub-OmniVTA-ff8800?logo=github)](https://github.com/MrSecant/OmniVTA) |
| 2026 | Open-H-Embodiment | [Open-H-Embodiment: A Large-Scale Dataset for Enabling Foundation Models in Medical Robotics](https://arxiv.org/abs/2604.21017) | 125.8K trajectories | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://open-h.github.io/open-h-embodiment/) | [![GitHub](https://img.shields.io/badge/GitHub-Open--H--Embodiment-ff8800?logo=github)](https://github.com/open-h/open-h-embodiment) |
| 2026 | Baihu-VTouch | [VTouch++: A Multimodal Dataset with Vision-Based Tactile Enhancement for Bimanual Manipulation](https://arxiv.org/abs/2604.20444) |  | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://www.modelscope.cn/datasets/OpenLoong-Community/visuo-tactile) |  |
| 2026 | Unitree UnifoLM-WBT | UniFoLM-WBT-Dataset |  |  | [![link](https://img.shields.io/badge/Website-9cf)](https://huggingface.co/collections/unitreerobotics/unifolm-wbt-dataset) |  |
| 2025 | Aist-Bimanual | AIST Bimanual Manipulation Dataset | 10.7K trajectories |  | [![link](https://img.shields.io/badge/Website-9cf)](https://aistairc.github.io/aist_bimanip_site/) |  |
| 2025 | PH2D | [Humanoid Policy ~ Human Policy](https://arxiv.org/abs/2503.13441) | 1.6K trajectories | CoRL | [![link](https://img.shields.io/badge/Website-9cf)](https://human-as-robot.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-PH2D-ff8800?logo=github)](https://github.com/RogerQi/human-policy) |
| 2025 | ActionNet | ActionNet: A Dataset for Dexterous Bimanual Manipulation | 30K trajectories |  | [![link](https://img.shields.io/badge/Website-9cf)](https://action-net.org/) | [![GitHub](https://img.shields.io/badge/GitHub-ActionNet-ff8800?logo=github)](https://github.com/FFTAI/fourier-lerobot) |
| 2025 | AgiBot World Beta | [AgiBot World Colosseo: A Large-scale Manipulation Platform for Scalable and Intelligent Embodied Systems](https://arxiv.org/abs/2503.06669) | 1M trajectories | IROS | [![link](https://img.shields.io/badge/Website-9cf)](https://agibot-world.com/) | [![GitHub](https://img.shields.io/badge/GitHub-AgiBot--World-ff8800?logo=github)](https://github.com/OpenDriveLab/AgiBot-World) |
| 2025 | Open Galaxea | [Galaxea Open-World Dataset and G0 Dual-System VLA Model](https://arxiv.org/abs/2509.00576) | 100K trajectories | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://opengalaxea.github.io/GalaxeaVLA/) | [![GitHub](https://img.shields.io/badge/GitHub-Open_Galaxea-ff8800?logo=github)](https://github.com/OpenGalaxea/GalaxeaVLA) |
| 2025 | Humanoid Everyday | [Humanoid Everyday: A Comprehensive Robotic Dataset for Open-World Humanoid Manipulation](https://arxiv.org/abs/2510.08807) | 10.3K trajectories | ICRA | [![link](https://img.shields.io/badge/Website-9cf)](https://humanoideveryday.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-Humanoid_Everyday-ff8800?logo=github)](https://github.com/physical-superintelligence-lab/Humanoid-Everyday) |
| 2025 | MotionTrans | [MotionTrans: Human VR Data Enable Motion-Level Learning for Robotic Manipulation Policies](https://arxiv.org/abs/2509.17759) | 1.5K trajectories | ICRA | [![link](https://img.shields.io/badge/Website-9cf)](https://motiontrans.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-MotionTrans-ff8800?logo=github)](https://github.com/michaelyuancb/motiontrans) |
| 2025 | RealSource-World | RealSource-World: A Large-Scale Real-World Dual-Arm Manipulation Dataset | 11.4K trajectories |  | [![link](https://img.shields.io/badge/Website-9cf)](https://realmanrobot.github.io/real_source_dataset) |  |
| 2025 | REASSEMBLE | [REASSEMBLE: A Multimodal Dataset for Contact-rich Robotic Assembly and Disassembly](https://arxiv.org/abs/2502.05086) | 4.6K trajectories | RSS | [![link](https://img.shields.io/badge/Website-9cf)](https://tuwien-asl.github.io/REASSEMBLE_page/) | [![GitHub](https://img.shields.io/badge/GitHub-REASSEMBLE-ff8800?logo=github)](https://github.com/TUWIEN-ASL/REASSEMBLE) |
| 2025 | RoboCOIN | [RoboCOIN: An Open-Sourced Bimanual Robotic Data Collection for Integrated Manipulation](https://arxiv.org/abs/2511.17441) | 180K trajectories | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://flagopen.github.io/RoboCOIN/) | [![GitHub](https://img.shields.io/badge/GitHub-RoboCOIN-ff8800?logo=github)](https://github.com/FlagOpen/RoboCOIN) |
| 2025 | RoboMIND 2.0 | [RoboMIND 2.0: A Multimodal, Bimanual Mobile Manipulation Dataset for Generalizable Embodied Intelligence](https://arxiv.org/abs/2512.24653) | 310K trajectories | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://modelscope.cn/datasets/X-Humanoid/RoboMIND2.0/) | [![GitHub](https://img.shields.io/badge/GitHub-RoboMIND_2.0-ff8800?logo=github)](https://github.com/x-humanoid-robomind/x-humanoid-robomind.github.io) |

</details>

<details open id="table-real-robot-2024-and-earlier">
<summary>Table: Real-robot datasets (2024 and earlier)</summary>

| Year | Dataset | Paper | Scale | Venue | Project | Repo@GitHub |
|------|---------|-------|-------|-------|---------|-------------|
| 2024 | FMB | [FMB: a Functional Manipulation Benchmark for Generalizable Robotic Learning](https://arxiv.org/abs/2401.08553) | 22.6K trajectories | IJRR | [![link](https://img.shields.io/badge/Website-9cf)](https://functional-manipulation-benchmark.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-FMB-ff8800?logo=github)](https://github.com/rail-berkeley/fmb) |
| 2024 | ALOHA Unleashed | [ALOHA Unleashed: A Simple Recipe for Robot Dexterity](https://arxiv.org/abs/2410.13126) | 26.2K trajectories | CoRL | [![link](https://img.shields.io/badge/Website-9cf)](https://aloha-unleashed.github.io/) |  |
| 2024 | DROID | [DROID: A Large-Scale In-The-Wild Robot Manipulation Dataset](https://arxiv.org/abs/2403.12945) | 76K trajectories | RSS | [![link](https://img.shields.io/badge/Website-9cf)](https://droid-dataset.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-DROID-ff8800?logo=github)](https://github.com/droid-dataset/droid_policy_learning) |
| 2024 | HumanPlus | [HumanPlus: Humanoid Shadowing and Imitation from Humans](https://arxiv.org/abs/2406.10454) | 240 trajectories | CoRL | [![link](https://img.shields.io/badge/Website-9cf)](https://humanoid-ai.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-HumanPlus-ff8800?logo=github)](https://github.com/MarkFzp/humanplus) |
| 2024 | Mobile ALOHA | [Mobile ALOHA: Learning Bimanual Mobile Manipulation with Low-Cost Whole-Body Teleoperation](https://arxiv.org/abs/2401.02117) | 276 trajectories | CoRL | [![link](https://img.shields.io/badge/Website-9cf)](https://mobile-aloha.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-Mobile_ALOHA-ff8800?logo=github)](https://github.com/MarkFzp/mobile-aloha) |
| 2024 | OmniH2O | [OmniH2O: Universal and Dexterous Human-to-Humanoid Whole-Body Teleoperation and Learning](https://arxiv.org/abs/2406.08858) |  | CoRL | [![link](https://img.shields.io/badge/Website-9cf)](https://omni.human2humanoid.com/) | [![GitHub](https://img.shields.io/badge/GitHub-OmniH2O-ff8800?logo=github)](https://github.com/LeCAR-Lab/human2humanoid) |
| 2024 | Open X-Embodiment | [Open X-Embodiment: Robotic Learning Datasets and RT-X Models](https://arxiv.org/abs/2310.08864) | 2.4M trajectories | ICRA | [![link](https://img.shields.io/badge/Website-9cf)](https://robotics-transformer-x.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-Open_X--Embodiment-ff8800?logo=github)](https://github.com/google-deepmind/open_x_embodiment) |
| 2024 | RoboMIND | [RoboMIND: Benchmark on Multi-embodiment Intelligence Normative Data for Robot Manipulation](https://arxiv.org/abs/2412.13877) | 107K trajectories | RSS | [![link](https://img.shields.io/badge/Website-9cf)](https://x-humanoid-robomind.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-RoboMIND-ff8800?logo=github)](https://github.com/x-humanoid-robomind/x-humanoid-robomind.github.io) |
| 2023 | ALOHA | [Learning Fine-Grained Bimanual Manipulation with Low-Cost Hardware](https://arxiv.org/abs/2304.13705) | 300 trajectories | RSS | [![link](https://img.shields.io/badge/Website-9cf)](https://tonyzhaozh.github.io/aloha/) | [![GitHub](https://img.shields.io/badge/GitHub-act-ff8800?logo=github)](https://github.com/tonyzhaozh/act) |
| 2023 | RH20T | [RH20T: A Comprehensive Robotic Dataset for Learning Diverse Skills in One-Shot](https://arxiv.org/abs/2307.00595) | 110K trajectories | ICRA | [![link](https://img.shields.io/badge/Website-9cf)](https://rh20t.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-rh20t_api-ff8800?logo=github)](https://github.com/rh20t/rh20t_api) |
| 2023 | RoboSet | [RoboAgent: Generalization and Efficiency in Robot Manipulation via Semantic Augmentations and Action Chunking](https://arxiv.org/abs/2309.01918) | 98.5K trajectories | ICRA | [![link](https://img.shields.io/badge/Website-9cf)](https://robopen.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-RoboSet-ff8800?logo=github)](https://github.com/robopen/roboagent) |
| 2023 | BridgeData V2 | [BridgeData V2: A Dataset for Robot Learning at Scale](https://arxiv.org/abs/2308.12952) | 60.1K trajectories | CoRL | [![link](https://img.shields.io/badge/Website-9cf)](https://rail-berkeley.github.io/bridgedata/) | [![GitHub](https://img.shields.io/badge/GitHub-BridgeData_V2-ff8800?logo=github)](https://github.com/rail-berkeley/bridge_data_v2) |
| 2023 | FurnitureBench | [FurnitureBench: Reproducible Real-World Benchmark for Long-Horizon Complex Manipulation](https://arxiv.org/abs/2305.12821) | 5.1K trajectories | RSS | [![link](https://img.shields.io/badge/Website-9cf)](https://clvrai.github.io/furniture-bench/) | [![GitHub](https://img.shields.io/badge/GitHub-FurnitureBench-ff8800?logo=github)](https://github.com/clvrai/furniture-bench) |
| 2022 | BC-Z | [BC-Z: Zero-Shot Task Generalization with Robotic Imitation Learning](https://arxiv.org/abs/2202.02005) | 26K trajectories | CoRL | [![link](https://img.shields.io/badge/Website-9cf)](https://sites.google.com/view/bc-z/home) | [![GitHub](https://img.shields.io/badge/GitHub-BC--Z-ff8800?logo=github)](https://github.com/google-research/tensor2robot/tree/master/research/bcz) |
| 2022 | RT-1 | [RT-1: Robotics Transformer for Real-World Control at Scale](https://arxiv.org/abs/2212.06817) | 130K trajectories | RSS | [![link](https://img.shields.io/badge/Website-9cf)](https://robotics-transformer1.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-RT--1-ff8800?logo=github)](https://github.com/google-research/robotics_transformer) |
| 2021 | MT-Opt | [MT-Opt: Continuous Multi-Task Robotic Reinforcement Learning at Scale](https://arxiv.org/abs/2104.08212) | 800K trajectories | CoRL | [![link](https://img.shields.io/badge/Website-9cf)](https://karolhausman.github.io/mt-opt/) | [![GitHub](https://img.shields.io/badge/GitHub-MT--Opt-ff8800?logo=github)](https://github.com/KarolHausman/mt-opt) |
| 2021 | BridgeData | [Bridge Data: Boosting Generalization of Robotic Skills with Cross-Domain Datasets](https://arxiv.org/abs/2109.13396) | 7.2K trajectories | RSS | [![link](https://img.shields.io/badge/Website-9cf)](https://sites.google.com/view/bridgedata) | [![GitHub](https://img.shields.io/badge/GitHub-BridgeData-ff8800?logo=github)](https://github.com/yanlai00/bridge_data_imitation_learning) |
| 2019 | RoboNet | [RoboNet: Large-Scale Multi-Robot Learning](https://arxiv.org/abs/1910.11215) | 162K trajectories | CoRL | [![link](https://img.shields.io/badge/Website-9cf)](https://www.robonet.wiki/) | [![GitHub](https://img.shields.io/badge/GitHub-RoboNet-ff8800?logo=github)](https://github.com/SudeepDasari/RoboNet) |
| 2018 | DAML | [One-Shot Imitation from Observing Humans via Domain-Adaptive Meta-Learning](https://arxiv.org/abs/1802.01557) | 2.9K trajectories | RSS | [![link](https://img.shields.io/badge/Website-9cf)](https://sites.google.com/view/daml) | [![GitHub](https://img.shields.io/badge/GitHub-DAML-ff8800?logo=github)](https://github.com/tianheyu927/mil) |
| 2018 | MIME | [Multiple Interactions Made Easy (MIME): Large Scale Demonstrations Data for Imitation](https://arxiv.org/abs/1810.07121) | 8.3K trajectories | CoRL | [![link](https://img.shields.io/badge/Website-9cf)](https://sites.google.com/view/mimedataset) |  |
| 2018 | QT-Opt | [QT-Opt: Scalable Deep Reinforcement Learning for Vision-Based Robotic Manipulation](https://arxiv.org/abs/1806.10293) | 580K trajectories | CoRL | [![link](https://img.shields.io/badge/Website-9cf)](https://sites.google.com/view/qtopt/home) | [![GitHub](https://img.shields.io/badge/GitHub-Qt--Opt-ff8800?logo=github)](https://github.com/google-research/tensor2robot/tree/master/research/qtopt) |
| 2018 | RoboTurk | [RoboTurk: A Crowdsourcing Platform for Robotic Skill Learning through Imitation](https://arxiv.org/abs/1811.02790) | 2.1K trajectories | CoRL | [![link](https://img.shields.io/badge/Website-9cf)](https://roboturk.stanford.edu/) | [![GitHub](https://img.shields.io/badge/GitHub-RoboTurk-ff8800?logo=github)](https://github.com/RoboTurk-Platform/roboturk_real_dataset) |
| 2015 | Pinto and Gupta | [Supersizing Self-supervision: Learning to Grasp from 50K Tries and 700 Robot Hours](https://arxiv.org/abs/1509.06825) | 50K trajectories | ICRA | [![link](https://img.shields.io/badge/Website-9cf)](https://www.lerrelpinto.com/publication/supersizing/) |  |

</details>

### UMI Data

<details open id="table-umi-data">
<summary>Table: UMI-style robot-free and cross-embodiment datasets</summary>

| Year | Dataset | Paper | Scale | Venue | Project | Repo@GitHub |
|------|---------|-------|-------|-------|---------|-------------|
| 2026 | HuMI | [Humanoid Manipulation Interface: Humanoid Whole-Body Manipulation from Robot-Free Demonstrations](https://arxiv.org/abs/2602.06643) | 827 trajectories | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://humanoid-manipulation-interface.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-HuMI-ff8800?logo=github)](https://github.com/Richard-coder-Nai/HuMI) |
| 2026 | RealOmni | RealOmni-Open DataSet | 13,000+ hours; 5M+ clips (snapshot: 2026-07-24) |  | [![link](https://img.shields.io/badge/Website-9cf)](https://www.genrobot.ai/data/open-dataset/) | [![GitHub](https://img.shields.io/badge/GitHub-das--datakit-ff8800?logo=github)](https://github.com/genrobot-ai/das-datakit) |
| 2026 | UMI-3D | [UMI-3D: Extending Universal Manipulation Interface from Vision-Limited to 3D Spatial Perception](https://arxiv.org/abs/2604.14089) | 4609 trajectories | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://umi-3d.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-UMI--3D-ff8800?logo=github)](https://github.com/hku-mars/UMI-3D) |
| 2026 | TAMEn | [TAMEn: Tactile-Aware Manipulation Engine for Closed-Loop Data Collection in Contact-Rich Tasks](https://arxiv.org/abs/2604.07335) | 724 trajectories | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://opendrivelab.com/TAMEn) | [![GitHub](https://img.shields.io/badge/GitHub-TAMEn-ff8800?logo=github)](https://github.com/OpenDriveLab/TAMEn) |
| 2026 | Daimon-Infinity | Daimon-Infinity | 274669 trajectories |  | [![link](https://img.shields.io/badge/Website-9cf)](https://modelscope.cn/datasets/daimonrobotics/Daimon-Infinity) |  |
| 2025 | Data Scaling Laws | [Data Scaling Laws in Imitation Learning for Robotic Manipulation](https://arxiv.org/abs/2410.18647) | 24098 trajectories | ICLR | [![link](https://img.shields.io/badge/Website-9cf)](https://data-scaling-laws.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-Data_Scaling_Laws-ff8800?logo=github)](https://github.com/Fanqi-Lin/Data-Scaling-Laws) |
| 2025 | LEGATO | [LEGATO: Cross-Embodiment Imitation Using a Grasping Tool](https://arxiv.org/abs/2411.03682) | 900 trajectories | RA-L | [![link](https://img.shields.io/badge/Website-9cf)](https://ut-hcrl.github.io/LEGATO/) | [![GitHub](https://img.shields.io/badge/GitHub-LEGATO-ff8800?logo=github)](https://github.com/ut-hcrl/LEGATO) |
| 2025 | ViTaMIn | [ViTaMIn: Learning Contact-Rich Tasks Through Robot-Free Visuo-Tactile Manipulation Interface](https://arxiv.org/abs/2504.06156) | 841 trajectories | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://chuanyune.github.io/ViTaMIn_page/) |  |
| 2025 | DexWild | [DexWild: Dexterous Human Interactions for In-the-Wild Robot Policies](https://arxiv.org/abs/2505.07813) | 9,290 demonstrations; 93 environments | RSS | [![link](https://img.shields.io/badge/Website-9cf)](https://dexwild.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-DexWild-ff8800?logo=github)](https://github.com/dexwild/dexwild) |
| 2025 | DexUMI | [DexUMI: Using Human Hand as the Universal Manipulation Interface for Dexterous Manipulation](https://arxiv.org/abs/2505.21864) | 1792 trajectories | CoRL | [![link](https://img.shields.io/badge/Website-9cf)](https://dex-umi.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-DexUMI-ff8800?logo=github)](https://github.com/real-stanford/DexUMI) |
| 2025 | FreeTacMan | [FreeTacMan: Robot-free Visuo-Tactile Data Collection System for Contact-rich Manipulation](https://arxiv.org/abs/2506.01941) | >10,000 trajectories; 50 tasks | ICRA | [![link](https://img.shields.io/badge/Website-9cf)](https://opendrivelab.com/FreeTacMan) | [![GitHub](https://img.shields.io/badge/GitHub-FreeTacMan-ff8800?logo=github)](https://github.com/OpenDriveLab/FreeTacMan) |
| 2025 | Touch in the Wild | [Touch in the Wild: Learning Fine-Grained Manipulation with a Portable Visuo-Tactile Gripper](https://arxiv.org/abs/2507.15062) | 2737 trajectories | NeurIPS | [![link](https://img.shields.io/badge/Website-9cf)](https://binghao-huang.github.io/touch_in_the_wild/) | [![GitHub](https://img.shields.io/badge/GitHub-touch_in_the_wild-ff8800?logo=github)](https://github.com/YolandaXinyueZhu/touch_in_the_wild) |
| 2025 | exUMI | [exUMI: Extensible Robot Teaching System with Action-aware Task-agnostic Tactile Representation](https://arxiv.org/abs/2509.14688) | 1660 trajectories | CoRL | [![link](https://img.shields.io/badge/Website-9cf)](https://silicx.github.io/exUMI/) | [![GitHub](https://img.shields.io/badge/GitHub-exUMI-ff8800?logo=github)](https://github.com/silicx/exUMI) |
| 2025 | MV-UMI | [MV-UMI: A Scalable Multi-View Interface for Cross-Embodiment Learning](https://arxiv.org/abs/2509.18757) | 1370 trajectories | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://mv-umi.github.io/) |  |
| 2025 | ManipForce | [ManipForce: Force-Guided Policy Learning with Frequency-Aware Representation for Contact-Rich Manipulation](https://arxiv.org/abs/2509.19047) | 597 trajectories | ICRA | [![link](https://img.shields.io/badge/Website-9cf)](https://sites.google.com/view/manipforce/%ED%99%88) | [![GitHub](https://img.shields.io/badge/GitHub-ManipForce-ff8800?logo=github)](https://github.com/gist-ailab/ManipForce) |
| 2025 | FastUMI-100K | [FastUMI-100K: Advancing Data-driven Robotic Manipulation with a Large-scale UMI-style Dataset](https://arxiv.org/abs/2510.08022) | 100K trajectories | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://huggingface.co/datasets/IPEC-COMMUNITY/FastUMI_100k_lerobot) | [![GitHub](https://img.shields.io/badge/GitHub-FastUMI--100K-ff8800?logo=github)](https://github.com/MrKeee/FastUMI-100K) |
| 2025 | ViTaMIn-B | [ViTaMIn-B: A Reliable and Efficient Visuo-Tactile Bimanual Manipulation Interface](https://arxiv.org/abs/2511.05858) | 844 demonstrations | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://chuanyune.github.io/ViTaMIn-B_page/) | [![GitHub](https://img.shields.io/badge/GitHub-ViTaMIn--B-ff8800?logo=github)](https://github.com/chuanyune/ViTaMIn-B_code) |
| 2024 | UMI | [Universal Manipulation Interface: In-The-Wild Robot Teaching Without In-The-Wild Robots](https://arxiv.org/abs/2402.10329) | 2543 trajectories | RSS | [![link](https://img.shields.io/badge/Website-9cf)](https://umi-gripper.github.io) | [![GitHub](https://img.shields.io/badge/GitHub-UMI-ff8800?logo=github)](https://github.com/real-stanford/universal_manipulation_interface) |
| 2024 | ManiWAV | [ManiWAV: Learning Robot Manipulation from In-the-Wild Audio-Visual Data](https://arxiv.org/abs/2406.19464) | 1014 trajectories | CoRL | [![link](https://img.shields.io/badge/Website-9cf)](https://maniwav.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-ManiWAV-ff8800?logo=github)](https://github.com/real-stanford/maniwav) |
| 2024 | UMI-on-Legs | [UMI on Legs: Making Manipulation Policies Mobile with Manipulation-Centric Whole-body Controllers](https://openreview.net/forum?id=3i7j8ZPnbm) | 514 trajectories | CoRL | [![link](https://img.shields.io/badge/Website-9cf)](https://umi-on-legs.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-UMI--on--Legs-ff8800?logo=github)](https://github.com/real-stanford/umi-on-legs) |
| 2024 | FastUMI | [FastUMI: A Scalable and Hardware-Independent Universal Manipulation Interface with Dataset](https://proceedings.mlr.press/v305/zhaxizhuoma25a.html) | >15,000 demonstrations; 24 tasks | CoRL | [![link](https://img.shields.io/badge/Website-9cf)](https://www.fastumi.com/FastUMI/index.html) | [![GitHub](https://img.shields.io/badge/GitHub-FastUMI-ff8800?logo=github)](https://github.com/zxzm-zak/FastUMI_Data) |

</details>


### Egocentric & Ego-Exo Data

<details open id="table-egocentric-ego-exo-recent">
<summary>Table: Recent egocentric and ego-exo datasets</summary>

| Year | Acronym | Paper | Venue | Project | Repo@GitHub |
|------|---------|-------|-------|---------|-------------|
| 2026 | Open-AoE | [Open-AoE: An Open Egocentric Manipulation Dataset and Toolchain for Embodied Learning](https://arxiv.org/abs/2607.14183) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://huggingface.co/datasets/inclusionAI/OpenAoE-2000h) |  |
| 2026 | EgoTactile | [EgoTactile: Learning Grasp Pressure for Everyday Objects from Egocentric Video](https://arxiv.org/abs/2606.09243) | ICML | [![link](https://img.shields.io/badge/Website-9cf)](https://egotactile.github.io/) |  |
| 2026 | EgoEMG | [EgoEMG: A Multimodal Egocentric Dataset with Bilateral EMG and Vision for Hand Pose Estimation](https://arxiv.org/abs/2605.05712) | arXiv |  | [![GitHub](https://img.shields.io/badge/GitHub-EgoEMG-ff8800?logo=github)](https://github.com/zhenqis123/EgoEMG) |
| 2026 | EgoEVHands | [EgoEV-HandPose: Egocentric 3D Hand Pose Estimation and Gesture Recognition with Stereo Event Cameras](https://arxiv.org/abs/2605.12297) | arXiv |  | [![GitHub](https://img.shields.io/badge/GitHub-EgoEV--HandPose-ff8800?logo=github)](https://github.com/ZJUWang01/EgoEV-HandPose) |
| 2026 | EgoSPT | [Spatially Prompted Visual Trajectory Prediction for Egocentric Manipulation](https://arxiv.org/abs/2605.20085) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://huggingface.co/datasets/JackYFL233/EgoSPT) |  |
| 2026 | EgoTraj | [EgoTraj: Real-World Egocentric Human Trajectory Dataset for Multimodal Prediction](https://arxiv.org/abs/2605.19004) | arXiv |  | [![GitHub](https://img.shields.io/badge/GitHub-EgoTraj-ff8800?logo=github)](https://github.com/yehiahmad/EgoTraj) |
| 2026 | HumanEgo | [HumanEgo: Zero-Shot Robot Learning from Minutes of Human Egocentric Videos](https://arxiv.org/abs/2605.24934) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://humanego-ai.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-HumanEgo-ff8800?logo=github)](https://github.com/TX-Leo/HumanEgo) |
| 2026 | MobileEgo Anywhere | [MobileEgo Anywhere: Open Infrastructure for long horizon egocentric data on commodity hardware](https://arxiv.org/abs/2605.05945) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://huggingface.co/datasets/fpvlabs/stera-10m) | [![GitHub](https://img.shields.io/badge/GitHub-stera--sdk-ff8800?logo=github)](https://github.com/fpv-labs/stera-sdk) |
| 2026 | EgoTouch | [TouchAnything: A Dataset and Framework for Bimanual Tactile Estimation from Egocentric Video](https://arxiv.org/abs/2605.13083) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://jianyi2004.github.io/TouchAnything-Website/) | [![GitHub](https://img.shields.io/badge/GitHub-TouchAnything-ff8800?logo=github)](https://github.com/Jianyi2004/TouchAnything) |
| 2026 | ChildLens | [ChildLens: An egocentric video dataset for activity analysis in children](https://link.springer.com/article/10.3758/s13428-026-02982-6) | Behavior Research Methods | [![link](https://img.shields.io/badge/Website-9cf)](https://www.eva.mpg.de/comparative-cultural-psychology/technical-development/childlens/) |  |
| 2026 | EgoFun3D | [EgoFun3D: Modeling Interactive Objects from Egocentric Videos using Function Templates](https://arxiv.org/abs/2604.11038) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://3dlg-hcvc.github.io/EgoFun3D/) | [![GitHub](https://img.shields.io/badge/GitHub-EgoFun3D-ff8800?logo=github)](https://github.com/3dlg-hcvc/EgoFun3D) |
| 2026 | EgoLive | [EgoLive: A Large-Scale Egocentric Dataset from Real-World Human Tasks](https://arxiv.org/abs/2604.23570) | arXiv |  |  |
| 2026 | EgoMAGIC | [EgoMAGIC: An Egocentric Video Field Medicine Dataset for Training Perception Algorithms](https://arxiv.org/abs/2604.22036) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://zenodo.org/records/19239155) |  |
| 2026 | EgoVerse | [EgoVerse: An Egocentric Human Dataset for Robot Learning from Around the World](https://arxiv.org/abs/2604.07607) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://egoverse.ai/) | [![GitHub](https://img.shields.io/badge/GitHub-EgoVerse-ff8800?logo=github)](https://github.com/GaTech-RL2/EgoVerse) |
| 2026 | Ego-1K | [Ego-1K -- A Large-Scale Multiview Video Dataset for Egocentric Vision](https://arxiv.org/abs/2603.13741) | CVPR | [![link](https://img.shields.io/badge/Website-9cf)](https://huggingface.co/datasets/facebook/ego-1k) |  |
| 2026 | EgoXtreme | [EgoXtreme: A Dataset for Robust Object Pose Estimation in Egocentric Views under Extreme Conditions](https://arxiv.org/abs/2603.25135) | CVPR | [![link](https://img.shields.io/badge/Website-9cf)](https://taegyoun88.github.io/EgoXtreme/) | [![GitHub](https://img.shields.io/badge/GitHub-EgoXtreme-ff8800?logo=github)](https://github.com/taegyoun88/EgoXtreme) |
| 2026 | FEEL | [FEEL (Force-Enhanced Egocentric Learning): A Dataset for Physical Action Understanding](https://arxiv.org/abs/2603.15847) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://www.cs.umd.edu/~edessale/feel) |  |
| 2026 | Xperience-10M | Xperience-10M: Ropedia Dataset Release |  | [![link](https://img.shields.io/badge/Website-9cf)](https://huggingface.co/datasets/ropedia-ai/xperience-10m) |  |
| 2025 | Ego-EXTRA | [Ego-EXTRA: video-language Egocentric Dataset for EXpert-TRAinee assistance](https://arxiv.org/abs/2512.13238) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://fpv-iplab.github.io/Ego-EXTRA/) |  |
| 2025 | Egocentric-100K | Egocentric-100K Dataset Release |  | [![link](https://img.shields.io/badge/Website-9cf)](https://huggingface.co/datasets/builddotai/Egocentric-100K) |  |
| 2025 | World In Your Hands | [World In Your Hands: A Large-Scale and Open-source Ecosystem for Learning Human-centric Manipulation in the Wild](https://arxiv.org/abs/2512.24310) | arXiv |  | [![GitHub](https://img.shields.io/badge/GitHub-World_In_Your_Hands-ff8800?logo=github)](https://github.com/tars-robotics/World-In-Your-Hands) |
| 2025 | IndEgo | [IndEgo: A Dataset of Industrial Scenarios and Collaborative Work for Egocentric Assistants](https://arxiv.org/abs/2511.19684) | NeurIPS | [![link](https://img.shields.io/badge/Website-9cf)](https://vivekchavan.com/IndEgo/) | [![GitHub](https://img.shields.io/badge/GitHub-IndEgo-ff8800?logo=github)](https://github.com/Vivek9Chavan/IndEgo) |
| 2025 | OpenEgo | [OpenEgo: A Large-Scale Multimodal Egocentric Dataset for Dexterous Manipulation](https://arxiv.org/abs/2509.05513) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://www.openegocentric.com/) | [![GitHub](https://img.shields.io/badge/GitHub-openego-ff8800?logo=github)](https://github.com/ahadjawaid/openego) |
| 2025 | EgoDex | [EgoDex: Learning Dexterous Manipulation from Large-Scale Egocentric Video](https://arxiv.org/abs/2505.11709) | ICLR | [![link](https://img.shields.io/badge/Website-9cf)](https://machinelearning.apple.com/research/egodex-learning-dexterous-manipulation) | [![GitHub](https://img.shields.io/badge/GitHub-ml--egodex-ff8800?logo=github)](https://github.com/apple/ml-egodex) |
| 2025 | EgoExOR | [EgoExOR: An Ego-Exo-Centric Operating Room Dataset for Surgical Activity Understanding](https://arxiv.org/abs/2505.24287) | NeurIPS |  | [![GitHub](https://img.shields.io/badge/GitHub-EgoExOR-ff8800?logo=github)](https://github.com/ardamamur/EgoExOR) |
| 2025 | EgoLife | [EgoLife: Towards Egocentric Life Assistant](https://arxiv.org/abs/2503.03803) | CVPR | [![link](https://img.shields.io/badge/Website-9cf)](https://egolife-ai.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-EgoLife-ff8800?logo=github)](https://github.com/EvolvingLMMs-Lab/EgoLife) |
| 2025 | TASTE-Rob | [TASTE-Rob: Advancing Video Generation of Task-Oriented Hand-Object Interaction for Generalizable Robotic Manipulation](https://arxiv.org/abs/2503.11423) | CVPR | [![link](https://img.shields.io/badge/Website-9cf)](https://taste-rob.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-TASTE--Rob-ff8800?logo=github)](https://github.com/GAP-LAB-CUHK-SZ/TASTE-Rob) |
| 2025 | HD-EPIC | [HD-EPIC: A Highly-Detailed Egocentric Video Dataset](https://arxiv.org/abs/2502.04144) | CVPR | [![link](https://img.shields.io/badge/Website-9cf)](https://hd-epic.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-hd--epic--annotations-ff8800?logo=github)](https://github.com/hd-epic/hd-epic-annotations) |
| 2025 | EgoMe | [EgoMe: A New Dataset and Challenge for Following Me via Egocentric View in Real World](https://arxiv.org/abs/2501.19061) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://huggingface.co/datasets/HeqianQiu/EgoMe) |  |

</details>

<details open id="table-egocentric-ego-exo-2024-and-earlier">
<summary>Table: Egocentric and ego-exo datasets (2024 and earlier)</summary>

| Year | Acronym | Paper | Venue | Project | Repo@GitHub |
|------|---------|-------|-------|---------|-------------|
| 2024 | EgoVid-5M | [EgoVid-5M: A Large-Scale Video-Action Dataset for Egocentric Video Generation](https://arxiv.org/abs/2411.08380) | NeurIPS | [![link](https://img.shields.io/badge/Website-9cf)](https://egovid.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-EgoVid-ff8800?logo=github)](https://github.com/JeffWang987/EgoVid) |
| 2024 | EgoMimic | [EgoMimic: Scaling Imitation Learning via Egocentric Video](https://arxiv.org/abs/2410.24221) | ICRA | [![link](https://img.shields.io/badge/Website-9cf)](https://egomimic.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-EgoMimic-ff8800?logo=github)](https://github.com/SimarKareer/EgoMimic) |
| 2024 | EgoOops | [EgoOops: A Dataset for Mistake Action Detection from Egocentric Videos Referring to Procedural Texts](https://arxiv.org/abs/2410.05343) | ICCV Workshops | [![link](https://img.shields.io/badge/Website-9cf)](https://y-haneji.github.io/EgoOops-project-page/) | [![GitHub](https://img.shields.io/badge/GitHub-EgoOops--annotations-ff8800?logo=github)](https://github.com/Y-Haneji/EgoOops-annotations/) |
| 2024 | EgoPressure | [EgoPressure: A Dataset for Hand Pressure and Pose Estimation in Egocentric Vision](https://arxiv.org/abs/2409.02224) | CVPR | [![link](https://img.shields.io/badge/Website-9cf)](https://yiming-zhao.github.io/EgoPressure/) |  |
| 2024 | EgoExo-Fitness | [EgoExo-Fitness: Towards Egocentric and Exocentric Full-Body Action Understanding](https://arxiv.org/abs/2406.08877) | ECCV |  | [![GitHub](https://img.shields.io/badge/GitHub-EgoExo--Fitness-ff8800?logo=github)](https://github.com/iSEE-Laboratory/EgoExo-Fitness) |
| 2024 | HOT3D | [HOT3D: Hand and Object Tracking in 3D from Egocentric Multi-View Videos](https://arxiv.org/abs/2411.19167) | CVPR | [![link](https://img.shields.io/badge/Website-9cf)](https://facebookresearch.github.io/hot3d/) | [![GitHub](https://img.shields.io/badge/GitHub-hot3d-ff8800?logo=github)](https://github.com/facebookresearch/hot3d) |
| 2024 | Nymeria | [Nymeria: A Massive Collection of Multimodal Egocentric Daily Motion in the Wild](https://arxiv.org/abs/2406.09905) | ECCV | [![link](https://img.shields.io/badge/Website-9cf)](https://www.projectaria.com/datasets/nymeria/) | [![GitHub](https://img.shields.io/badge/GitHub-nymeria_dataset-ff8800?logo=github)](https://github.com/facebookresearch/nymeria_dataset) |
| 2024 | EgoSurgery | [EgoSurgery-Phase: A Dataset of Surgical Phase Recognition from Egocentric Open Surgery Videos](https://arxiv.org/abs/2405.19644) | MICCAI |  | [![GitHub](https://img.shields.io/badge/GitHub-EgoSurgery-ff8800?logo=github)](https://github.com/Fujiry0/EgoSurgery) |
| 2024 | EgoExoLearn | [EgoExoLearn: A Dataset for Bridging Asynchronous Ego- and Exo-centric View of Procedural Activities in Real World](https://arxiv.org/abs/2403.16182) | CVPR | [![link](https://img.shields.io/badge/Website-9cf)](https://huggingface.co/datasets/hyf015/EgoExoLearn) | [![GitHub](https://img.shields.io/badge/GitHub-EgoExoLearn-ff8800?logo=github)](https://github.com/OpenGVLab/EgoExoLearn) |
| 2024 | AEA | [Aria Everyday Activities Dataset](https://arxiv.org/abs/2402.13349) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://www.projectaria.com/datasets/aea/) |  |
| 2023 | CaptainCook4D | [CaptainCook4D: A Dataset for Understanding Errors in Procedural Activities](https://arxiv.org/abs/2312.14556) | NeurIPS | [![link](https://img.shields.io/badge/Website-9cf)](https://captaincook4d.github.io/captain-cook/) | [![GitHub](https://img.shields.io/badge/GitHub-CaptainCook4D-ff8800?logo=github)](https://github.com/CaptainCook4D/CaptainCook4D) |
| 2023 | Ego-Exo4D | [Ego-Exo4D: Understanding Skilled Human Activity from First- and Third-Person Perspectives](https://arxiv.org/abs/2311.18259) | IJCV | [![link](https://img.shields.io/badge/Website-9cf)](https://ego-exo4d-data.org/) | [![GitHub](https://img.shields.io/badge/GitHub-Ego4d-ff8800?logo=github)](https://github.com/facebookresearch/Ego4d) |
| 2023 | PVSG | [Panoptic Video Scene Graph Generation](https://arxiv.org/abs/2311.17058) | CVPR | [![link](https://img.shields.io/badge/Website-9cf)](https://jingkangyang.com/PVSG/) | [![GitHub](https://img.shields.io/badge/GitHub-OpenPVSG-ff8800?logo=github)](https://github.com/LilyDaytoy/OpenPVSG) |
| 2023 | IndustReal | [IndustReal: A Dataset for Procedure Step Recognition Handling Execution Errors in Egocentric Videos in an Industrial-Like Setting](https://arxiv.org/abs/2310.17323) | WACV | [![link](https://img.shields.io/badge/Website-9cf)](https://timschoonbeek.github.io/industreal.html) | [![GitHub](https://img.shields.io/badge/GitHub-IndustReal-ff8800?logo=github)](https://github.com/TimSchoonbeek/IndustReal) |
| 2023 | EgoObjects | [EgoObjects: A Large-Scale Egocentric Dataset for Fine-Grained Object Understanding](https://arxiv.org/abs/2309.08816) | ICCV | [![link](https://img.shields.io/badge/Website-9cf)](https://ai.meta.com/datasets/egoobjects-downloads/) | [![GitHub](https://img.shields.io/badge/GitHub-EgoObjects-ff8800?logo=github)](https://github.com/facebookresearch/EgoObjects) |
| 2023 | ENIGMA-51 | [ENIGMA-51: Towards a Fine-Grained Understanding of Human-Object Interactions in Industrial Scenarios](https://arxiv.org/abs/2309.14809) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://iplab.dmi.unict.it/ENIGMA-51) | [![GitHub](https://img.shields.io/badge/GitHub-ENIGMA--51-ff8800?logo=github)](https://github.com/fpv-iplab/ENIGMA-51) |
| 2023 | HoloAssist | [HoloAssist: an Egocentric Human Interaction Dataset for Interactive AI Assistants in the Real World](https://arxiv.org/abs/2309.17024) | ICCV | [![link](https://img.shields.io/badge/Website-9cf)](https://holoassist.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-holoassist--release-ff8800?logo=github)](https://github.com/Ember-HoloAssist/holoassist-release) |
| 2023 | ADT | [Aria Digital Twin: A New Benchmark Dataset for Egocentric 3D Machine Perception](https://arxiv.org/abs/2306.06362) | ICCV | [![link](https://img.shields.io/badge/Website-9cf)](https://www.projectaria.com/datasets/adt/) |  |
| 2023 | AssemblyHands | [AssemblyHands: Towards Egocentric Activity Understanding via 3D Hand Pose Estimation](https://arxiv.org/abs/2304.12301) | CVPR | [![link](https://img.shields.io/badge/Website-9cf)](https://assemblyhands.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-assemblyhands--toolkit-ff8800?logo=github)](https://github.com/facebookresearch/assemblyhands-toolkit) |
| 2023 | WEAR | [WEAR: An Outdoor Sports Dataset for Wearable and Egocentric Activity Recognition](https://arxiv.org/abs/2304.05088) | IMWUT | [![link](https://img.shields.io/badge/Website-9cf)](https://mariusbock.github.io/wear/) | [![GitHub](https://img.shields.io/badge/GitHub-wear-ff8800?logo=github)](https://github.com/mariusbock/wear) |
| 2022 | Touch and Go | [Touch and Go: Learning from Human-Collected Vision and Touch](https://arxiv.org/abs/2211.12498) | NeurIPS | [![link](https://img.shields.io/badge/Website-9cf)](https://touch-and-go.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-Touch--and--Go-ff8800?logo=github)](https://github.com/fredfyyang/Touch-and-Go) |
| 2022 | EgoHOS | [Fine-Grained Egocentric Hand-Object Segmentation: Dataset, Model, and Applications](https://arxiv.org/abs/2208.03826) | ECCV |  | [![GitHub](https://img.shields.io/badge/GitHub-EgoHOS-ff8800?logo=github)](https://github.com/owenzlz/EgoHOS) |
| 2022 | ARCTIC | [ARCTIC: A Dataset for Dexterous Bimanual Hand-Object Manipulation](https://arxiv.org/abs/2204.13662) | CVPR | [![link](https://img.shields.io/badge/Website-9cf)](https://arctic.is.tue.mpg.de/) | [![GitHub](https://img.shields.io/badge/GitHub-arctic-ff8800?logo=github)](https://github.com/zc-alexfan/arctic) |
| 2022 | Assembly101 | [Assembly101: A Large-Scale Multi-View Video Dataset for Understanding Procedural Activities](https://arxiv.org/abs/2203.14712) | CVPR | [![link](https://img.shields.io/badge/Website-9cf)](https://assembly-101.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-assembly101--download--scripts-ff8800?logo=github)](https://github.com/assembly-101/assembly101-download-scripts) |
| 2022 | EgoPAT3D | [Egocentric Prediction of Action Target in 3D](https://arxiv.org/abs/2203.13116) | CVPR |  | [![GitHub](https://img.shields.io/badge/GitHub-EgoPAT3D-ff8800?logo=github)](https://github.com/ai4ce/EgoPAT3D) |
| 2022 | HOI4D | [HOI4D: A 4D Egocentric Dataset for Category-Level Human-Object Interaction](https://arxiv.org/abs/2203.01577) | CVPR | [![link](https://img.shields.io/badge/Website-9cf)](https://hoi4d.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-HOI4D--Instructions-ff8800?logo=github)](https://github.com/leolyliu/HOI4D-Instructions) |
| 2021 | EgoBody | [EgoBody: Human Body Shape and Motion of Interacting People from Head-Mounted Devices](https://arxiv.org/abs/2112.07642) | ECCV | [![link](https://img.shields.io/badge/Website-9cf)](https://egobody.ethz.ch/) | [![GitHub](https://img.shields.io/badge/GitHub-EgoBody-ff8800?logo=github)](https://github.com/sanweiliti/EgoBody) |
| 2021 | Ego-Deliver | [Ego-Deliver: A Large-Scale Dataset for Egocentric Video Analysis](https://dl.acm.org/doi/10.1145/3474085.3475336) | ACM MM | [![link](https://img.shields.io/badge/Website-9cf)](https://egodeliver.github.io/EgoDeliver_Dataset/) |  |
| 2021 | Ego4D | [Ego4D: Around the World in 3,000 Hours of Egocentric Video](https://arxiv.org/abs/2110.07058) | CVPR | [![link](https://img.shields.io/badge/Website-9cf)](https://ego4d-data.org/) | [![GitHub](https://img.shields.io/badge/GitHub-Ego4d-ff8800?logo=github)](https://github.com/facebookresearch/Ego4d) |
| 2021 | H2O | [H2O: Two Hands Manipulating Objects for First Person Interaction Recognition](https://arxiv.org/abs/2104.11181) | ICCV | [![link](https://img.shields.io/badge/Website-9cf)](https://taeinkwon.com/projects/h2o/) | [![GitHub](https://img.shields.io/badge/GitHub-h2odataset-ff8800?logo=github)](https://github.com/taeinkwon/h2odataset) |
| 2020 | MECCANO | [The MECCANO Dataset: Understanding Human-Object Interactions from Egocentric Videos in an Industrial-Like Domain](https://arxiv.org/abs/2010.05654) | WACV | [![link](https://img.shields.io/badge/Website-9cf)](https://iplab.dmi.unict.it/MECCANO/) | [![GitHub](https://img.shields.io/badge/GitHub-MECCANO-ff8800?logo=github)](https://github.com/fpv-iplab/MECCANO) |
| 2020 | LEMMA | [LEMMA: A Multi-View Dataset for Learning Multi-Agent Multi-Task Activities](https://arxiv.org/abs/2007.15781) | ECCV | [![link](https://img.shields.io/badge/Website-9cf)](https://sites.google.com/view/lemma-activity) | [![GitHub](https://img.shields.io/badge/GitHub-LEMMA-ff8800?logo=github)](https://github.com/Buzz-Beater/LEMMA) |
| 2020 | EPIC-KITCHENS-100 | [Rescaling Egocentric Vision: Collection, Pipeline and Challenges for EPIC-KITCHENS-100](https://doi.org/10.1007/s11263-021-01531-2) | IJCV | [![link](https://img.shields.io/badge/Website-9cf)](https://epic-kitchens.github.io) | [![GitHub](https://img.shields.io/badge/GitHub-epic--kitchens--100--annotations-ff8800?logo=github)](https://github.com/epic-kitchens/epic-kitchens-100-annotations) |
| 2020 | EGO-CH | [EGO-CH: Dataset and Fundamental Tasks for Visitors Behavioral Understanding Using Egocentric Vision](https://arxiv.org/abs/2002.00899) | PRL |  |  |
| 2020 | EgoCom | [EgoCom: A Multi-Person Multi-Modal Egocentric Communications Dataset](https://doi.org/10.1109/TPAMI.2020.3025105) | TPAMI |  | [![GitHub](https://img.shields.io/badge/GitHub-EgoCom--Dataset-ff8800?logo=github)](https://github.com/facebookresearch/EgoCom-Dataset) |
| 2019 | You2Me | [You2Me: Inferring Body Pose in Egocentric Video via First and Second Person Interactions](https://arxiv.org/abs/1904.09882) | CVPR | [![link](https://img.shields.io/badge/Website-9cf)](https://vision.cs.utexas.edu/projects/you2me/) | [![GitHub](https://img.shields.io/badge/GitHub-you2me-ff8800?logo=github)](https://github.com/facebookresearch/you2me) |
| 2018 | Charades-Ego | [Charades-Ego: A Large-Scale Dataset of Paired Third and First Person Videos](https://arxiv.org/abs/1804.09626) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://prior.allenai.org/projects/charades-ego) | [![GitHub](https://img.shields.io/badge/GitHub-charades--algorithms-ff8800?logo=github)](https://github.com/gsig/charades-algorithms) |
| 2018 | EPIC-KITCHENS | [Scaling Egocentric Vision: The EPIC-KITCHENS Dataset](https://arxiv.org/abs/1804.02748) | ECCV | [![link](https://img.shields.io/badge/Website-9cf)](https://epic-kitchens.github.io/2018) | [![GitHub](https://img.shields.io/badge/GitHub-epic--kitchens--55--annotations-ff8800?logo=github)](https://github.com/epic-kitchens/epic-kitchens-55-annotations) |
| 2018 | EgoCart | [Egocentric Shopping Cart Localization](https://iplab.dmi.unict.it/fpv/publications/spera2018egocentric.pdf) | ICPR | [![link](https://img.shields.io/badge/Website-9cf)](https://iplab.dmi.unict.it/legacy/EgocentricShoppingCartLocalization/) |  |
| 2018 | EgoGesture | [EgoGesture: A New Dataset and Benchmark for Egocentric Hand Gesture Recognition](https://nlpr.ia.ac.cn/iva/yfzhang/datasets/EgoGesture.pdf) | TMM | [![link](https://img.shields.io/badge/Website-9cf)](http://www.nlpr.ia.ac.cn/iva/yfzhang/datasets/egogesture.html) |  |
| 2018 | EGTEA Gaze+ | [In the Eye of the Beholder: Gaze and Actions in First Person Video](https://doi.org/10.1109/TPAMI.2021.3051319) | TPAMI | [![link](https://img.shields.io/badge/Website-9cf)](https://cbs.ic.gatech.edu/fpv/) |  |
| 2017 | FPHA | [First-Person Hand Action Benchmark with RGB-D Videos and 3D Hand Pose Annotations](https://arxiv.org/abs/1704.02463) | CVPR | [![link](https://img.shields.io/badge/Website-9cf)](https://guiggh.github.io/publications/first-person-hands/) | [![GitHub](https://img.shields.io/badge/GitHub-hand_pose_action-ff8800?logo=github)](https://github.com/guiggh/hand_pose_action) |
| 2017 | EgoDexter | [Real-time Hand Tracking under Occlusion from an Egocentric RGB-D Sensor](https://handtracker.mpi-inf.mpg.de/projects/OccludedHands/index.htm) | ICCV | [![link](https://img.shields.io/badge/Website-9cf)](https://handtracker.mpi-inf.mpg.de/projects/OccludedHands/EgoDexter.htm) |  |
| 2017 | THU-READ | [Action Recognition in RGB-D Egocentric Videos](https://doi.org/10.1109/ICIP.2017.8296915) | ICIP | [![link](https://img.shields.io/badge/Website-9cf)](https://ivg.au.tsinghua.edu.cn/dataset/THU_READ.php) |  |
| 2016 | EgoConvNet | [First Person Action Recognition Using Deep Learned Descriptors](https://openaccess.thecvf.com/content_cvpr_2016/html/Singh_First_Person_Action_CVPR_2016_paper.html) | CVPR | [![link](https://img.shields.io/badge/Website-9cf)](https://cvit.iiit.ac.in/research/projects/cvit-projects/first-person-action-recognition) | [![GitHub](https://img.shields.io/badge/GitHub-EgoConvNet-ff8800?logo=github)](https://github.com/suriyachaudary/EgoConvNet) |
| 2016 | KrishnaCam | [KrishnaCam: Using a Longitudinal, Single-Person, Egocentric Dataset for Scene Understanding Tasks](https://krsingh.cs.ucdavis.edu/krishna_files/papers/krishnacam/krishnacam_files/kcam_wacv16.pdf) | WACV | [![link](https://img.shields.io/badge/Website-9cf)](https://krsingh.cs.ucdavis.edu/krishna_files/papers/krishnacam/krishnacam.html) |  |
| 2016 | PEV | [Recognizing Micro-Actions and Reactions from Paired Egocentric Videos](https://openaccess.thecvf.com/content_cvpr_2016/html/Yonetani_Recognizing_Micro-Actions_and_CVPR_2016_paper.html) | CVPR |  |  |
| 2015 | EgoHands | [Lending A Hand: Detecting Hands and Recognizing Activities in Complex Egocentric Interactions](https://openaccess.thecvf.com/content_iccv_2015/html/Bambach_Lending_A_Hand_ICCV_2015_paper.html) | ICCV | [![link](https://img.shields.io/badge/Website-9cf)](http://vision.soic.indiana.edu/projects/egohands/) |  |
| 2008 | CMU-MMAC | [Guide to the Carnegie Mellon University Multimodal Activity (CMU-MMAC) Database](https://publications.ri.cmu.edu/guide-to-the-carnegie-mellon-university-multimodal-activity-cmu-mmac-database) | Technical Report | [![link](https://img.shields.io/badge/Website-9cf)](http://kitchen.cs.cmu.edu/) |  |

</details>

### Simulation Data

> **Curation note.** For peer-reviewed work, `Year` and `Publication / Type` use the formal publication year and venue. For arXiv-only work, `Year` is the first public preprint year. Software without a canonical paper is labeled `Software`. The sections below distinguish reusable 3D/scene assets, simulation backends, evaluation benchmarks, and both downloadable synthetic datasets and systems that generate such data.

#### 3D Assets & Scene Datasets

<details open id="table-simulation-assets-scenes">
<summary>Table: 3D assets and scene datasets</summary>

| Year | Resource / Acronym | Reference | Publication / Type | Project | Official Code |
|------|---------|-------|-------|---------|-------------|
| 2026 | ManiTwin-100K | [ManiTwin: Scaling Data-Generation-Ready Digital Object Dataset to 100K](https://arxiv.org/abs/2603.16866) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://manitwin.github.io/) |  |
| 2026 | PhysX-Mobility (dataset) | [PhysX-Anything: Simulation-Ready Physical 3D Assets from Single Image](https://arxiv.org/abs/2511.13648) | CVPR | [![link](https://img.shields.io/badge/Website-9cf)](https://physx-anything.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-PhysX--Anything-ff8800?logo=github)](https://github.com/ziangcao0312/PhysX-Anything) |
| 2026 | PhysXVerse (dataset) | [PhysX-Omni: Unified Simulation-Ready Physical 3D Generation for Rigid, Deformable, and Articulated Objects](https://arxiv.org/abs/2605.21572) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://physx-omni.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-PhysX--Omni-ff8800?logo=github)](https://github.com/physx-omni/PhysX-Omni) |
| 2025 | PhysXNet & PhysXNet-XL | [PhysX-3D: Physical-Grounded 3D Asset Generation](https://arxiv.org/abs/2507.12465) | NeurIPS | [![link](https://img.shields.io/badge/Website-9cf)](https://physx-3d.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-PhysX--3D-ff8800?logo=github)](https://github.com/ziangcao0312/PhysX-3D) |
| 2024 | HSSD-200 | [Habitat Synthetic Scenes Dataset (HSSD-200): An Analysis of 3D Scene Scale and Realism Tradeoffs for ObjectGoal Navigation](https://arxiv.org/abs/2306.11290) | CVPR | [![link](https://img.shields.io/badge/Website-9cf)](https://3dlg-hcvc.github.io/hssd/) | [![GitHub](https://img.shields.io/badge/GitHub-hssd-ff8800?logo=github)](https://github.com/3dlg-hcvc/hssd) |
| 2023 | Objaverse | [Objaverse: A Universe of Annotated 3D Objects](https://arxiv.org/abs/2212.08051) | CVPR | [![link](https://img.shields.io/badge/Website-9cf)](https://objaverse.allenai.org/) | [![GitHub](https://img.shields.io/badge/GitHub-objaverse-ff8800?logo=github)](https://github.com/allenai/objaverse) |
| 2023 | Objaverse-XL | [Objaverse-XL: A Universe of 10M+ 3D Objects](https://arxiv.org/abs/2307.05663) | NeurIPS | [![link](https://img.shields.io/badge/Website-9cf)](https://objaverse.allenai.org/) | [![GitHub](https://img.shields.io/badge/GitHub-objaverse--xl-ff8800?logo=github)](https://github.com/allenai/objaverse-xl) |
| 2023 | OmniObject3D | [OmniObject3D: Large-Vocabulary 3D Object Dataset for Realistic Perception, Reconstruction and Generation](https://arxiv.org/abs/2301.07525) | CVPR | [![link](https://img.shields.io/badge/Website-9cf)](https://omniobject3d.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-OmniObject3D-ff8800?logo=github)](https://github.com/omniobject3d/OmniObject3D) |
| 2023 | ScanNet++ | [ScanNet++: A High-Fidelity Dataset of 3D Indoor Scenes](https://arxiv.org/abs/2308.11417) | ICCV | [![link](https://img.shields.io/badge/Website-9cf)](https://kaldir.vc.in.tum.de/scannetpp/) | [![GitHub](https://img.shields.io/badge/GitHub-scannetpp-ff8800?logo=github)](https://github.com/scannetpp/scannetpp) |
| 2022 | ABO | [ABO: Dataset and Benchmarks for Real-World 3D Object Understanding](https://arxiv.org/abs/2110.06199) | CVPR | [![link](https://img.shields.io/badge/Website-9cf)](https://amazon-berkeley-objects.s3.amazonaws.com/index.html) | [![GitHub](https://img.shields.io/badge/GitHub-amazon--berkeley--objects-ff8800?logo=github)](https://github.com/jazcollins/amazon-berkeley-objects) |
| 2022 | GSO | [Google Scanned Objects: A High-Quality Dataset of 3D Scanned Household Items](https://arxiv.org/abs/2204.11918) | ICRA | [![link](https://img.shields.io/badge/Website-9cf)](https://research.google/blog/scanned-objects-by-google-research-a-dataset-of-3d-scanned-common-household-items/) |  |
| 2022 | ObjectFolder 2.0 | [ObjectFolder 2.0: A Multisensory Object Dataset for Sim2Real Transfer](https://arxiv.org/abs/2204.02389) | CVPR | [![link](https://img.shields.io/badge/Website-9cf)](https://ai.stanford.edu/~rhgao/objectfolder2.0/) | [![GitHub](https://img.shields.io/badge/GitHub-ObjectFolder-ff8800?logo=github)](https://github.com/rhgao/ObjectFolder) |
| 2022 | ProcTHOR | [ProcTHOR: Large-Scale Embodied AI Using Procedural Generation](https://arxiv.org/abs/2206.06994) | NeurIPS | [![link](https://img.shields.io/badge/Website-9cf)](https://procthor.allenai.org) | [![GitHub](https://img.shields.io/badge/GitHub-procthor-ff8800?logo=github)](https://github.com/allenai/procthor) |
| 2021 | 3D-FRONT | [3D-FRONT: 3D Furnished Rooms with layOuts and semaNTics](https://arxiv.org/abs/2011.09127) | ICCV | [![link](https://img.shields.io/badge/Website-9cf)](https://tianchi.aliyun.com/dataset/65347) |  |
| 2021 | HM3D | [Habitat-Matterport 3D Dataset (HM3D): 1000 Large-scale 3D Environments for Embodied AI](https://arxiv.org/abs/2109.08238) | NeurIPS | [![link](https://img.shields.io/badge/Website-9cf)](https://aihabitat.org/datasets/hm3d/) | [![GitHub](https://img.shields.io/badge/GitHub-habitat--matterport3d--dataset-ff8800?logo=github)](https://github.com/facebookresearch/habitat-matterport3d-dataset) |
| 2019 | Replica | [The Replica Dataset: A Digital Replica of Indoor Spaces](https://arxiv.org/abs/1906.05797) | arXiv |  | [![GitHub](https://img.shields.io/badge/GitHub-Replica--Dataset-ff8800?logo=github)](https://github.com/facebookresearch/Replica-Dataset) |
| 2017 | Matterport3D | [Matterport3D: Learning from RGB-D Data in Indoor Environments](https://arxiv.org/abs/1709.06158) | 3DV | [![link](https://img.shields.io/badge/Website-9cf)](https://niessner.github.io/Matterport/) | [![GitHub](https://img.shields.io/badge/GitHub-Matterport-ff8800?logo=github)](https://github.com/niessner/Matterport) |
| 2015 | ShapeNet | [ShapeNet: An Information-Rich 3D Model Repository](https://arxiv.org/abs/1512.03012) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://shapenet.org) |  |

</details>

#### Simulation & Rendering Backends

<details open id="table-simulation-rendering-backends">
<summary>Table: Simulation and rendering backends</summary>

| Year | Resource / Acronym | Reference | Publication / Type | Project | Official Code |
|------|---------|-------|-------|---------|-------------|
| 2026 | Genie Sim 3.0 | [Genie Sim 3.0: A High-Fidelity Comprehensive Simulation Platform for Humanoid Robot](https://arxiv.org/abs/2601.02078) | arXiv |  | [![GitHub](https://img.shields.io/badge/GitHub-genie_sim-ff8800?logo=github)](https://github.com/AgibotTech/genie_sim) |
| 2026 | Tac2Real | [Tac2Real: Reliable and GPU Visuotactile Simulation for Online Reinforcement Learning and Zero-Shot Real-World Deployment](https://arxiv.org/abs/2603.28475) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://ningyurichard.github.io/tac2real-project-page/) | [![GitHub](https://img.shields.io/badge/GitHub-Tac2Real-ff8800?logo=github)](https://github.com/InternRobotics/Tac2Real) |
| 2026 | UniVTAC | [UniVTAC: A Unified Simulation Platform for Visuo-Tactile Manipulation Data Generation, Learning, and Benchmarking](https://arxiv.org/abs/2602.10093) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://univtac.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-UniVTAC-ff8800?logo=github)](https://github.com/univtac/UniVTAC) |
| 2025 | GenManip | [GenManip: LLM-driven Simulation for Generalizable Instruction-Following Manipulation](https://arxiv.org/abs/2506.10966) | CVPR | [![link](https://img.shields.io/badge/Website-9cf)](https://genmanip.com/) | [![GitHub](https://img.shields.io/badge/GitHub-GenManip-ff8800?logo=github)](https://github.com/InternRobotics/GenManip) |
| 2025 | NVIDIA Isaac Sim | [Official software documentation](https://developer.nvidia.com/isaac/sim) | Software (open-source repository released in 2025) | [![link](https://img.shields.io/badge/Website-9cf)](https://developer.nvidia.com/isaac/sim) | [![GitHub](https://img.shields.io/badge/GitHub-IsaacSim-ff8800?logo=github)](https://github.com/isaac-sim/IsaacSim) |
| 2025 | ManiSkill3 | [ManiSkill3: GPU Parallelized Robotics Simulation and Rendering for Generalizable Embodied AI](https://arxiv.org/abs/2410.00425) | RSS | [![link](https://img.shields.io/badge/Website-9cf)](https://www.maniskill.ai/) | [![GitHub](https://img.shields.io/badge/GitHub-ManiSkill-ff8800?logo=github)](https://github.com/haosulab/ManiSkill) |
| 2025 | MuJoCo Playground | [MuJoCo Playground](https://arxiv.org/abs/2502.08844) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://playground.mujoco.org/) | [![GitHub](https://img.shields.io/badge/GitHub-mujoco_playground-ff8800?logo=github)](https://github.com/google-deepmind/mujoco_playground) |
| 2025 | Newton | [Open-source GPU-accelerated physics engine for robotics](https://newton-physics.github.io/newton/) | Software | [![link](https://img.shields.io/badge/Website-9cf)](https://newton-physics.github.io/newton/) | [![GitHub](https://img.shields.io/badge/GitHub-newton-ff8800?logo=github)](https://github.com/newton-physics/newton) |
| 2025 | RoboVerse | [RoboVerse: Towards a Unified Platform, Dataset and Benchmark for Scalable and Generalizable Robot Learning](https://arxiv.org/abs/2504.18904) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://roboverseorg.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-RoboVerse-ff8800?logo=github)](https://github.com/RoboVerseOrg/RoboVerse) |
| 2025 | Taccel | [Taccel: Scaling Up Vision-based Tactile Robotics via High-performance GPU Simulation](https://arxiv.org/abs/2504.12908) | NeurIPS | [![link](https://img.shields.io/badge/Website-9cf)](https://taccel-simulator.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-Taccel-ff8800?logo=github)](https://github.com/Taccel-Simulator/Taccel) |
| 2025 | TacFlex | [TacFlex: Multimode Tactile Imprints Simulation for Visuotactile Sensors With Coating Patterns](https://ieeexplore.ieee.org/document/11024236) | T-RO | [![link](https://img.shields.io/badge/Website-9cf)](https://sites.google.com/view/tacflex/) | [![GitHub](https://img.shields.io/badge/GitHub-TacFlex-ff8800?logo=github)](https://github.com/Zhang-Chaofan/TacFlex) |
| 2025 | TacSL | [TacSL: A Library for Visuotactile Sensor Simulation and Learning](https://arxiv.org/abs/2408.06506) | T-RO | [![link](https://img.shields.io/badge/Website-9cf)](https://iakinola23.github.io/tacsl/) | [![Code](https://img.shields.io/badge/Code-archived_preview-ff8800?logo=github)](https://github.com/isaac-sim/IsaacGymEnvs/blob/tacsl/isaacgymenvs/tacsl_sensors/install/tacsl_setup.md) |
| 2024 | DiffTactile | [DiffTactile: A Physics-based Differentiable Tactile Simulator for Contact-rich Robotic Manipulation](https://arxiv.org/abs/2403.08716) | ICLR | [![link](https://img.shields.io/badge/Website-9cf)](https://difftactile.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-DiffTactile-ff8800?logo=github)](https://github.com/Genesis-Embodied-AI/DiffTactile) |
| 2024 | Genesis | [Generative and universal physics engine for robotics and beyond](https://genesis-embodied-ai.github.io/) | Software | [![link](https://img.shields.io/badge/Website-9cf)](https://genesis-embodied-ai.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-Genesis-ff8800?logo=github)](https://github.com/Genesis-Embodied-AI/Genesis) |
| 2024 | Habitat 3.0 | [Habitat 3.0: A Co-Habitat for Humans, Avatars and Robots](https://arxiv.org/abs/2310.13724) | ICLR | [![link](https://img.shields.io/badge/Website-9cf)](https://aihabitat.org/habitat3/) | [![GitHub](https://img.shields.io/badge/GitHub-habitat--lab-ff8800?logo=github)](https://github.com/facebookresearch/habitat-lab) |
| 2024 | TacEx | [TacEx: GelSight Tactile Simulation in Isaac Sim -- Combining Soft-Body and Visuotactile Simulators](https://arxiv.org/abs/2411.04776) | CoRL 2024 Workshop / arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://sites.google.com/view/tacex) | [![GitHub](https://img.shields.io/badge/GitHub-TacEx-ff8800?logo=github)](https://github.com/DH-Ng/TacEx) |
| 2023 | Orbit | [Orbit: A Unified Simulation Framework for Interactive Robot Learning Environments](https://arxiv.org/abs/2301.04195) | RA-L | [![link](https://img.shields.io/badge/Website-9cf)](https://isaac-orbit.github.io/) | [![Successor](https://img.shields.io/badge/GitHub-IsaacLab_successor-ff8800?logo=github)](https://github.com/isaac-sim/IsaacLab) |
| 2023 | RoboHive | [RoboHive: A Unified Framework for Robot Learning](https://arxiv.org/abs/2310.06828) | NeurIPS | [![link](https://img.shields.io/badge/Website-9cf)](https://sites.google.com/view/robohive) | [![GitHub](https://img.shields.io/badge/GitHub-robohive-ff8800?logo=github)](https://github.com/vikashplus/robohive) |
| 2023 | Tacchi | [Tacchi: A Pluggable and Low Computational Cost Elastomer Deformation Simulator for Optical Tactile Sensors](https://arxiv.org/abs/2301.08343) | RA-L |  | [![GitHub](https://img.shields.io/badge/GitHub-Tacchi-ff8800?logo=github)](https://github.com/zixichen007115/Tacchi) |
| 2022 | Tactile Gym 2.0 | [Tactile Gym 2.0: Sim-to-Real Deep Reinforcement Learning for Comparing Low-Cost High-Resolution Robot Touch](https://arxiv.org/abs/2207.10763) | RA-L | [![link](https://img.shields.io/badge/Website-9cf)](https://sites.google.com/my.bristol.ac.uk/tactilegym2) | [![GitHub](https://img.shields.io/badge/GitHub-tactile_gym_2-ff8800?logo=github)](https://github.com/yijionglin/tactile_gym_2) |
| 2022 | Tacto | [TACTO: A Fast, Flexible, and Open-Source Simulator for High-Resolution Vision-Based Tactile Sensors](https://arxiv.org/abs/2012.08456) | RA-L | [![link](https://img.shields.io/badge/Website-9cf)](https://ai.meta.com/blog/teaching-robots-to-perceive-understand-and-interact-through-touch/) | [![GitHub](https://img.shields.io/badge/GitHub-tacto-ff8800?logo=github)](https://github.com/facebookresearch/tacto) |
| 2022 | Taxim | [Taxim: An Example-based Simulation Model for GelSight Tactile Sensors](https://arxiv.org/abs/2109.04027) | RA-L | [![link](https://img.shields.io/badge/Website-9cf)](https://publish.illinois.edu/robotouch/taxim-an-example-based-simulation-model-for-gelsight-tactile-sensors/) | [![GitHub](https://img.shields.io/badge/GitHub-Taxim-ff8800?logo=github)](https://github.com/Robo-Touch/Taxim) |
| 2021 | Brax | [Brax -- A Differentiable Physics Engine for Large Scale Rigid Body Simulation](https://arxiv.org/abs/2106.13281) | NeurIPS | [![link](https://img.shields.io/badge/Website-9cf)](https://research.google/blog/speeding-up-reinforcement-learning-with-a-new-physics-simulation-engine/) | [![GitHub](https://img.shields.io/badge/GitHub-brax-ff8800?logo=github)](https://github.com/google/brax) |
| 2021 | Habitat 2.0 | [Habitat 2.0: Training Home Assistants to Rearrange their Habitat](https://arxiv.org/abs/2106.14405) | NeurIPS | [![link](https://img.shields.io/badge/Website-9cf)](https://aihabitat.org/) | [![GitHub](https://img.shields.io/badge/GitHub-habitat--lab-ff8800?logo=github)](https://github.com/facebookresearch/habitat-lab) |
| 2021 | Isaac Gym | [Isaac Gym: High Performance GPU-Based Physics Simulation For Robot Learning](https://arxiv.org/abs/2108.10470) | NeurIPS | [![link](https://img.shields.io/badge/Website-9cf)](https://developer.nvidia.com/isaac-gym) | [![Environments](https://img.shields.io/badge/GitHub-official_environments_only-ff8800?logo=github)](https://github.com/isaac-sim/IsaacGymEnvs) |
| 2016 | PyBullet | [PyBullet](https://github.com/bulletphysics/bullet3#pybullet) | Software (official citation: 2016--2021) | [![link](https://img.shields.io/badge/Website-9cf)](https://pybullet.org) | [![GitHub](https://img.shields.io/badge/GitHub-bullet3-ff8800?logo=github)](https://github.com/bulletphysics/bullet3) |
| 2021 | ThreeDWorld (TDW) | [ThreeDWorld: A Platform for Interactive Multi-Modal Physical Simulation](https://arxiv.org/abs/2007.04954) | NeurIPS | [![link](https://img.shields.io/badge/Website-9cf)](https://www.threedworld.org/) | [![GitHub](https://img.shields.io/badge/GitHub-tdw-ff8800?logo=github)](https://github.com/threedworld-mit/tdw) |
| 2020 | SAPIEN | [SAPIEN: A SimulAted Part-based Interactive ENvironment](https://arxiv.org/abs/2003.08515) | CVPR | [![link](https://img.shields.io/badge/Website-9cf)](https://sapien.ucsd.edu/) | [![GitHub](https://img.shields.io/badge/GitHub-SAPIEN-ff8800?logo=github)](https://github.com/haosulab/SAPIEN) |
| 2019 | PyRep | [PyRep: Bringing V-REP to Deep Robot Learning](https://arxiv.org/abs/1906.11176) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://pyrep.readthedocs.io/en/latest/) | [![GitHub](https://img.shields.io/badge/GitHub-PyRep-ff8800?logo=github)](https://github.com/stepjam/PyRep) |
| 2013 | V-REP (now CoppeliaSim) | [V-REP: A Versatile and Scalable Robot Simulation Framework](https://doi.org/10.1109/IROS.2013.6696520) | IROS | [![link](https://img.shields.io/badge/Website-9cf)](https://www.coppeliarobotics.com/) |  |
| 2012 | MuJoCo | [MuJoCo: A physics engine for model-based control](https://ieeexplore.ieee.org/document/6386109) | IROS | [![link](https://img.shields.io/badge/Website-9cf)](https://mujoco.org) | [![GitHub](https://img.shields.io/badge/GitHub-mujoco-ff8800?logo=github)](https://github.com/google-deepmind/mujoco) |

</details>

#### Benchmarks

<details open id="table-simulation-benchmarks">
<summary>Table: Simulation benchmarks</summary>

| Year | Resource / Acronym | Reference | Publication / Type | Project | Official Code |
|------|---------|-------|-------|---------|-------------|
| 2026 | BiCoord | [BiCoord: A Bimanual Manipulation Benchmark towards Long-Horizon Spatial-Temporal Coordination](https://arxiv.org/abs/2604.05831) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://buaa-colalab.github.io/BiCoord/) | [![GitHub](https://img.shields.io/badge/GitHub-BiCoord--Bench-ff8800?logo=github)](https://github.com/buaa-colalab/BiCoord-Bench) |
| 2026 | DuoBench | [DuoBench: A Reproducible Benchmark for Bimanual Manipulation in Simulation and the Real World](https://arxiv.org/abs/2606.11901) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://duobench.github.io) | [![GitHub](https://img.shields.io/badge/GitHub-duobench-ff8800?logo=github)](https://github.com/RobotControlStack/duobench) |
| 2026 | MIKASA | [Memory, Benchmark & Robots: A Benchmark for Solving Complex Tasks with Reinforcement Learning](https://arxiv.org/abs/2502.10550) | ICLR | [![link](https://img.shields.io/badge/Website-9cf)](https://sites.google.com/view/memorybenchrobots/) | [![GitHub](https://img.shields.io/badge/GitHub-MIKASA--Robo-ff8800?logo=github)](https://github.com/CognitiveAISystems/MIKASA-Robo) |
| 2026 | REALM | [REALM: A Real-to-Sim Validated Benchmark for Generalization in Robotic Manipulation](https://arxiv.org/abs/2512.19562) | RA-L | [![link](https://img.shields.io/badge/Website-9cf)](https://martin-sedlacek.com/realm/) | [![GitHub](https://img.shields.io/badge/GitHub-REALM-ff8800?logo=github)](https://github.com/martin-sedlacek/REALM) |
| 2026 | RMBench | [RMBench: Memory-Dependent Robotic Manipulation Benchmark with Insights into Policy Design](https://arxiv.org/abs/2603.01229) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://rmbench.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-RMBench-ff8800?logo=github)](https://github.com/RoboTwin-Platform/RMBench) |
| 2026 | RoboCasa365 | [RoboCasa365: A Large-Scale Simulation Framework for Training and Benchmarking Generalist Robots](https://arxiv.org/abs/2603.04356) | ICLR | [![link](https://img.shields.io/badge/Website-9cf)](https://robocasa.ai/) | [![GitHub](https://img.shields.io/badge/GitHub-robocasa-ff8800?logo=github)](https://github.com/robocasa/robocasa) |
| 2026 | RoboDojo | [RoboDojo: A Unified Sim-and-Real Benchmark for Comprehensive Evaluation of Generalist Robot Manipulation Policies](https://arxiv.org/abs/2607.04434) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://robodojo-benchmark.com/) | [![GitHub](https://img.shields.io/badge/GitHub-RoboDojo-ff8800?logo=github)](https://github.com/RoboDojo-Benchmark/RoboDojo) |
| 2026 | RoboMemArena | [RoboMemArena: A Comprehensive and Challenging Robotic Memory Benchmark](https://arxiv.org/abs/2605.10921) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://robomemarena.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-RoboMemArena-ff8800?logo=github)](https://github.com/OpenHelix-Team/RoboMemArena) |
| 2026 | RoboMME | [RoboMME: Benchmarking and Understanding Memory for Robotic Generalist Policies](https://arxiv.org/abs/2603.04639) | ICML | [![link](https://img.shields.io/badge/Website-9cf)](https://robomme.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-robomme_benchmark-ff8800?logo=github)](https://github.com/RoboMME/robomme_benchmark) |
| 2026 | RobotArena ∞ | [RobotArena ∞: Scalable Robot Benchmarking via Real-to-Sim Translation](https://arxiv.org/abs/2510.23571) | ICLR | [![link](https://img.shields.io/badge/Website-9cf)](https://robotarenainf.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-RobotArena-ff8800?logo=github)](https://github.com/offjangir/RobotArena) |
| 2025 | ManiSkill-HAB | [ManiSkill-HAB: A Benchmark for Low-Level Manipulation in Home Rearrangement Tasks](https://arxiv.org/abs/2412.13211) | ICLR | [![link](https://img.shields.io/badge/Website-9cf)](https://arth-shukla.github.io/mshab/) | [![GitHub](https://img.shields.io/badge/GitHub-mshab-ff8800?logo=github)](https://github.com/arth-shukla/mshab) |
| 2025 | RoboCerebra | [RoboCerebra: A Large-scale Benchmark for Long-horizon Robotic Manipulation Evaluation](https://arxiv.org/abs/2506.06677) | NeurIPS | [![link](https://img.shields.io/badge/Website-9cf)](https://robocerebra.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-RoboCerebra-ff8800?logo=github)](https://github.com/qiuboxiang/RoboCerebra) |
| 2025 | RoboEval | [RoboEval: Where Robotic Manipulation Meets Structured and Scalable Evaluation](https://arxiv.org/abs/2507.00435) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://robo-eval.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-RoboEval-ff8800?logo=github)](https://github.com/Robo-Eval/RoboEval) |
| 2025 | RoboTwin 2.0 | [RoboTwin 2.0: A Scalable Data Generator and Benchmark with Strong Domain Randomization for Robust Bimanual Robotic Manipulation](https://arxiv.org/abs/2506.18088) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://robotwin-platform.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-RoboTwin-ff8800?logo=github)](https://github.com/RoboTwin-Platform/RoboTwin) |
| 2025 | VLABench | [VLABench: A Large-Scale Benchmark for Language-Conditioned Robotics Manipulation with Long-Horizon Reasoning Tasks](https://arxiv.org/abs/2412.18194) | ICCV | [![link](https://img.shields.io/badge/Website-9cf)](https://vlabench.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-VLABench-ff8800?logo=github)](https://github.com/OpenMOSS/VLABench) |
| 2024 | BEHAVIOR-1K | [BEHAVIOR-1K: A Human-Centered, Embodied AI Benchmark with 1,000 Everyday Activities and Realistic Simulation](https://arxiv.org/abs/2403.09227) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://behavior.stanford.edu) | [![GitHub](https://img.shields.io/badge/GitHub-BEHAVIOR--1K-ff8800?logo=github)](https://github.com/StanfordVL/BEHAVIOR-1K) |
| 2024 | BiGym | [BiGym: A Demo-Driven Mobile Bi-Manual Manipulation Benchmark](https://arxiv.org/abs/2407.07788) | CoRL | [![link](https://img.shields.io/badge/Website-9cf)](https://chernyadev.github.io/bigym/) | [![GitHub](https://img.shields.io/badge/GitHub-bigym-ff8800?logo=github)](https://github.com/chernyadev/bigym) |
| 2024 | GarmentLab | [GarmentLab: A Unified Simulation and Benchmark for Garment Manipulation](https://arxiv.org/abs/2411.01200) | NeurIPS | [![link](https://img.shields.io/badge/Website-9cf)](https://garmentlab.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-GarmentLab-ff8800?logo=github)](https://github.com/GarmentLab/GarmentLab) |
| 2024 | HumanoidBench | [HumanoidBench: Simulated Humanoid Benchmark for Whole-Body Locomotion and Manipulation](https://arxiv.org/abs/2403.10506) | RSS | [![link](https://img.shields.io/badge/Website-9cf)](https://humanoid-bench.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-humanoid--bench-ff8800?logo=github)](https://github.com/carlosferrazza/humanoid-bench) |
| 2024 | ManiSkill-ViTac 2025 | [ManiSkill-ViTac 2025: Challenge on Manipulation Skill Learning With Vision and Tactile Sensing](https://arxiv.org/abs/2411.12503) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://ai-workshops.github.io/maniskill-vitac-challenge-2025/) | [![GitHub](https://img.shields.io/badge/GitHub-ManiSkill--ViTac2025-ff8800?logo=github)](https://github.com/cyliizyz/ManiSkill-ViTac2025) |
| 2024 | RoboCasa | [RoboCasa: Large-Scale Simulation of Everyday Tasks for Generalist Robots](https://arxiv.org/abs/2406.02523) | RSS | [![link](https://img.shields.io/badge/Website-9cf)](https://robocasa.ai) | [![GitHub](https://img.shields.io/badge/GitHub-robocasa-ff8800?logo=github)](https://github.com/robocasa/robocasa) |
| 2024 | RoboTwin | [RoboTwin: Dual-Arm Robot Benchmark with Generative Digital Twins (early version)](https://arxiv.org/abs/2409.02920) | ECCV Workshop | [![link](https://img.shields.io/badge/Website-9cf)](https://robotwin-benchmark.github.io/early-version/) | [![GitHub](https://img.shields.io/badge/GitHub-RoboTwin-ff8800?logo=github)](https://github.com/TianxingChen/RoboTwin) |
| 2024 | SIMPLER | [Evaluating Real-World Robot Manipulation Policies in Simulation](https://arxiv.org/abs/2405.05941) | CoRL | [![link](https://img.shields.io/badge/Website-9cf)](https://simpler-env.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-SimplerEnv-ff8800?logo=github)](https://github.com/simpler-env/SimplerEnv) |
| 2024 | THE COLOSSEUM | [THE COLOSSEUM: A Benchmark for Evaluating Generalization for Robotic Manipulation](https://arxiv.org/abs/2402.08191) | RSS | [![link](https://img.shields.io/badge/Website-9cf)](https://robot-colosseum.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-robot--colosseum-ff8800?logo=github)](https://github.com/robot-colosseum/robot-colosseum) |
| 2023 | ARNOLD | [ARNOLD: A Benchmark for Language-Grounded Task Learning With Continuous States in Realistic 3D Scenes](https://arxiv.org/abs/2304.04321) | ICCV | [![link](https://img.shields.io/badge/Website-9cf)](https://arnold-benchmark.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-arnold-ff8800?logo=github)](https://github.com/arnold-benchmark/arnold) |
| 2023 | DaXBench | [DaXBench: Benchmarking Deformable Object Manipulation with Differentiable Physics](https://arxiv.org/abs/2210.13066) | ICLR | [![link](https://img.shields.io/badge/Website-9cf)](https://daxbench.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-DaXBench-ff8800?logo=github)](https://github.com/AdaCompNUS/DaXBench) |
| 2023 | DexArt | [DexArt: Benchmarking Generalizable Dexterous Manipulation with Articulated Objects](https://arxiv.org/abs/2305.05706) | CVPR | [![link](https://img.shields.io/badge/Website-9cf)](https://www.chenbao.tech/dexart/) | [![GitHub](https://img.shields.io/badge/GitHub-dexart--release-ff8800?logo=github)](https://github.com/Kami-code/dexart-release) |
| 2023 | LIBERO | [LIBERO: Benchmarking Knowledge Transfer for Lifelong Robot Learning](https://arxiv.org/abs/2306.03310) | NeurIPS | [![link](https://img.shields.io/badge/Website-9cf)](https://libero-project.github.io) | [![GitHub](https://img.shields.io/badge/GitHub-LIBERO-ff8800?logo=github)](https://github.com/Lifelong-Robot-Learning/LIBERO) |
| 2023 | ManiSkill2 | [ManiSkill2: A Unified Benchmark for Generalizable Manipulation Skills](https://arxiv.org/abs/2302.04659) | ICLR | [![link](https://img.shields.io/badge/Website-9cf)](https://maniskill2.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-ManiSkill2-ff8800?logo=github)](https://github.com/haosulab/ManiSkill2) |
| 2023 | VIMA | [VIMA: General Robot Manipulation with Multimodal Prompts](https://arxiv.org/abs/2210.03094) | ICML | [![link](https://img.shields.io/badge/Website-9cf)](https://vimalabs.github.io) | [![GitHub](https://img.shields.io/badge/GitHub-VIMA-ff8800?logo=github)](https://github.com/vimalabs/VIMA) |
| 2022 | Bi-DexHands | [Towards Human-Level Bimanual Dexterous Manipulation with Reinforcement Learning](https://arxiv.org/abs/2206.08686) | NeurIPS | [![link](https://img.shields.io/badge/Website-9cf)](https://pku-marl.github.io/DexterousHands/) | [![GitHub](https://img.shields.io/badge/GitHub-DexterousHands-ff8800?logo=github)](https://github.com/PKU-MARL/DexterousHands) |
| 2022 | CALVIN | [CALVIN: A Benchmark for Language-Conditioned Policy Learning for Long-Horizon Robot Manipulation Tasks](https://arxiv.org/abs/2112.03227) | RA-L | [![link](https://img.shields.io/badge/Website-9cf)](http://calvin.cs.uni-freiburg.de/) | [![GitHub](https://img.shields.io/badge/GitHub-calvin-ff8800?logo=github)](https://github.com/mees/calvin) |
| 2021 | PlasticineLab | [PlasticineLab: A Soft-Body Manipulation Benchmark with Differentiable Physics](https://arxiv.org/abs/2104.03311) | ICLR | [![link](https://img.shields.io/badge/Website-9cf)](http://plasticinelab.csail.mit.edu/) | [![GitHub](https://img.shields.io/badge/GitHub-PlasticineLab-ff8800?logo=github)](https://github.com/hzaskywalker/PlasticineLab) |
| 2020 | RLBench | [RLBench: The Robot Learning Benchmark & Learning Environment](https://arxiv.org/abs/1909.12271) | RA-L | [![link](https://img.shields.io/badge/Website-9cf)](https://sites.google.com/view/rlbench) | [![GitHub](https://img.shields.io/badge/GitHub-RLBench-ff8800?logo=github)](https://github.com/stepjam/RLBench) |
| 2020 | SoftGym | [SoftGym: Benchmarking Deep Reinforcement Learning for Deformable Object Manipulation](https://arxiv.org/abs/2011.07215) | CoRL | [![link](https://img.shields.io/badge/Website-9cf)](https://sites.google.com/view/softgym) | [![GitHub](https://img.shields.io/badge/GitHub-softgym-ff8800?logo=github)](https://github.com/Xingyu-Lin/softgym) |
| 2019 | Meta-World | [Meta-World: A Benchmark and Evaluation for Multi-Task and Meta Reinforcement Learning](https://arxiv.org/abs/1910.10897) | CoRL | [![link](https://img.shields.io/badge/Website-9cf)](https://meta-world.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-Metaworld-ff8800?logo=github)](https://github.com/Farama-Foundation/Metaworld) |

</details>

#### Simulation/Synthetic Datasets & Data-Generation Systems

<details open id="table-simulation-synthetic-datasets">
<summary>Table: Simulation/synthetic datasets and data-generation systems</summary>

| Year | Resource / Acronym | Reference | Publication / Type | Project | Official Code |
|------|---------|-------|-------|---------|-------------|
| 2026 | MolmoB0T data | [MolmoB0T: Large-Scale Simulation Enables Zero-Shot Manipulation](https://arxiv.org/abs/2603.16861) | arXiv / simulation dataset | [![link](https://img.shields.io/badge/Website-9cf)](https://allenai.github.io/MolmoBot/) | [![GitHub](https://img.shields.io/badge/GitHub-MolmoBot-ff8800?logo=github)](https://github.com/allenai/MolmoBot) |
| 2025 | Dex1B | [Dex1B: Learning with 1B Demonstrations for Dexterous Manipulation](https://arxiv.org/abs/2506.17198) | RSS / dataset | [![link](https://img.shields.io/badge/Website-9cf)](https://jianglongye.com/dex1b/) |  |
| 2025 | DexMimicGen | [DexMimicGen: Automated Data Generation for Bimanual Dexterous Manipulation via Imitation Learning](https://arxiv.org/abs/2410.24185) | ICRA / data-generation system | [![link](https://img.shields.io/badge/Website-9cf)](https://dexmimicgen.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-dexmimicgen-ff8800?logo=github)](https://github.com/NVlabs/dexmimicgen) |
| 2025 | DreamGen | [DreamGen: Unlocking Generalization in Robot Learning through Video World Models](https://arxiv.org/abs/2505.12705) | CoRL / world-model-generated data | [![link](https://img.shields.io/badge/Website-9cf)](https://research.nvidia.com/labs/gear/dreamgen/) | [![GitHub](https://img.shields.io/badge/GitHub-GR00T--Dreams-ff8800?logo=github)](https://github.com/NVIDIA/GR00T-Dreams) |
| 2025 | GR00T-X-Embodiment-Sim | [GR00T N1: An Open Foundation Model for Generalist Humanoid Robots](https://arxiv.org/abs/2503.14734) | arXiv / simulation dataset | [![link](https://img.shields.io/badge/Website-9cf)](https://huggingface.co/datasets/nvidia/PhysicalAI-Robotics-GR00T-X-Embodiment-Sim) | [![GitHub](https://img.shields.io/badge/GitHub-Isaac--GR00T-ff8800?logo=github)](https://github.com/NVIDIA/Isaac-GR00T) |
| 2025 | InternData-A1 | [InternData-A1: Pioneering High-Fidelity Synthetic Data for Pre-training Generalist Policy](https://arxiv.org/abs/2511.16651) | arXiv / synthetic dataset | [![link](https://img.shields.io/badge/Website-9cf)](https://huggingface.co/datasets/InternRobotics/InternData-A1) | [![GitHub](https://img.shields.io/badge/GitHub-InternManip-ff8800?logo=github)](https://github.com/InternRobotics/InternManip) |
| 2025 | SynGrasp-1B | [GraspVLA: a Grasping Foundation Model Pre-trained on Billion-scale Synthetic Action Data](https://arxiv.org/abs/2505.03233) | arXiv / synthetic dataset | [![link](https://img.shields.io/badge/Website-9cf)](https://pku-epic.github.io/GraspVLA-web/) | [![GitHub](https://img.shields.io/badge/GitHub-GraspVLA-ff8800?logo=github)](https://github.com/PKU-EPIC/GraspVLA) |
| 2024 | GenSim | [GenSim: Generating Robotic Simulation Tasks via Large Language Models](https://arxiv.org/abs/2310.01361) | ICLR / task-generation system | [![link](https://img.shields.io/badge/Website-9cf)](https://liruiw.github.io/gensim/) | [![GitHub](https://img.shields.io/badge/GitHub-GenSim-ff8800?logo=github)](https://github.com/liruiw/GenSim) |
| 2024 | GenSim2 | [GenSim2: Scaling Robot Data Generation with Multi-modal and Reasoning LLMs](https://arxiv.org/abs/2410.03645) | CoRL / data-generation framework | [![link](https://img.shields.io/badge/Website-9cf)](https://gensim2.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-GenSim2-ff8800?logo=github)](https://github.com/GenSim2/GenSim2) |
| 2024 | RoboGen | [RoboGen: Towards Unleashing Infinite Data for Automated Robot Learning via Generative Simulation](https://arxiv.org/abs/2311.01455) | ICML / generative simulation system | [![link](https://img.shields.io/badge/Website-9cf)](https://robogen-ai.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-RoboGen-ff8800?logo=github)](https://github.com/Genesis-Embodied-AI/RoboGen) |
| 2023 | DexGraspNet | [DexGraspNet: A Large-Scale Robotic Dexterous Grasp Dataset for General Objects Based on Simulation](https://arxiv.org/abs/2210.02697) | ICRA / dataset | [![link](https://img.shields.io/badge/Website-9cf)](https://pku-epic.github.io/DexGraspNet/) | [![GitHub](https://img.shields.io/badge/GitHub-DexGraspNet-ff8800?logo=github)](https://github.com/PKU-EPIC/DexGraspNet) |
| 2023 | MimicGen | [MimicGen: A Data Generation System for Scalable Robot Learning using Human Demonstrations](https://arxiv.org/abs/2310.17596) | CoRL / data-generation system | [![link](https://img.shields.io/badge/Website-9cf)](https://mimicgen.github.io) | [![GitHub](https://img.shields.io/badge/GitHub-mimicgen-ff8800?logo=github)](https://github.com/NVlabs/mimicgen) |
| 2021 | ACRONYM | [ACRONYM: A Large-Scale Grasp Dataset Based on Simulation](https://arxiv.org/abs/2011.09584) | ICRA / dataset | [![link](https://img.shields.io/badge/Website-9cf)](https://sites.google.com/nvidia.com/graspdataset) | [![GitHub](https://img.shields.io/badge/GitHub-acronym-ff8800?logo=github)](https://github.com/NVlabs/acronym) |
| 2021 | robomimic | [What Matters in Learning from Offline Human Demonstrations for Robot Manipulation](https://arxiv.org/abs/2108.03298) | CoRL / framework & simulated human demonstrations | [![link](https://img.shields.io/badge/Website-9cf)](https://robomimic.github.io/study/) | [![GitHub](https://img.shields.io/badge/GitHub-robomimic-ff8800?logo=github)](https://github.com/ARISE-Initiative/robomimic) |

</details>

#### World Models as Simulators

<details open id="table-world-models-as-simulators">
<summary>Table: World models as simulators</summary>

| Year | Acronym | Paper | Venue | Project | Repo@GitHub |
|------|---------|-------|-------|---------|-------------|
| 2026 |  | [World Model for Robot Learning: A Comprehensive Survey](https://arxiv.org/abs/2605.00080) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://ntumars.github.io/wm-robot-survey/) | [![GitHub](https://img.shields.io/badge/GitHub-Awesome--World--Model--for--Robotics--Policy-ff8800?logo=github)](https://github.com/NTUMARS/Awesome-World-Model-for-Robotics-Policy) |
| 2026 | GigaBrain-0.5M* | [GigaBrain-0.5M*: a VLA That Learns From World Model-Based Reinforcement Learning](https://arxiv.org/abs/2602.12099) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://gigabrain05m.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-giga--brain--0-ff8800?logo=github)](https://github.com/open-gigaai/giga-brain-0) |
| 2026 | PlayWorld | [PlayWorld: Learning Robot World Models from Autonomous Play](https://arxiv.org/abs/2603.09030) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://robot-playworld.github.io/) |  |
| 2026 | RehearseVLA | [RehearseVLA: Simulated Post-Training for VLAs with Physically-Consistent World Model](https://openaccess.thecvf.com/content/CVPR2026/html/Xiao_RehearseVLA_Simulated_Post-Training_for_VLAs_with_Physically-Consistent_World_Model_CVPR_2026_paper.html) | CVPR | [![link](https://img.shields.io/badge/Website-9cf)](https://isee-laboratory.github.io/world-env.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-world--env-ff8800?logo=github)](https://github.com/amap-cvlab/world-env) |
| 2026 | RISE | [RISE: Self-Improving Robot Policy with Compositional World Model](https://arxiv.org/abs/2602.11075) | RSS | [![link](https://img.shields.io/badge/Website-9cf)](https://opendrivelab.com/RISE/) | [![GitHub](https://img.shields.io/badge/GitHub-RISE-ff8800?logo=github)](https://github.com/OpenDriveLab/RISE) |
| 2026 | WMPO | [WMPO: World Model-based Policy Optimization for Vision-Language-Action Models](https://arxiv.org/abs/2511.09515) | ICLR | [![link](https://img.shields.io/badge/Website-9cf)](https://wm-po.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-WMPO-ff8800?logo=github)](https://github.com/WM-PO/WMPO) |
| 2026 | World-Gymnast | [World-Gymnast: Training Robots with Reinforcement Learning in a World Model](https://arxiv.org/abs/2602.02454) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://world-gymnast.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-world--gymnast-ff8800?logo=github)](https://github.com/world-gymnast/world-gymnast) |
| 2025 |  | [A Survey of Sim-to-Real Methods in RL: Progress, Prospects and Challenges with Foundation Models](https://arxiv.org/abs/2502.13187) | arXiv |  | [![GitHub](https://img.shields.io/badge/GitHub-AwesomeSim2Real-ff8800?logo=github)](https://github.com/LongchaoDa/AwesomeSim2Real) |
| 2025 |  | [Evaluating Gemini Robotics Policies in a Veo World Simulator](https://arxiv.org/abs/2512.10675) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://veo-robotics.github.io/) |  |
| 2025 | DiWA | [DiWA: Diffusion Policy Adaptation with World Models](https://arxiv.org/abs/2508.03645) | CoRL | [![link](https://img.shields.io/badge/Website-9cf)](https://imanema.com/publication/diwa/) | [![GitHub](https://img.shields.io/badge/GitHub-diwa-ff8800?logo=github)](https://github.com/acl21/diwa) |
| 2025 | DreamGen | [DreamGen: Unlocking Generalization in Robot Learning through Video World Models](https://arxiv.org/abs/2505.12705) | CoRL | [![link](https://img.shields.io/badge/Website-9cf)](https://research.nvidia.com/labs/gear/dreamgen/) | [![GitHub](https://img.shields.io/badge/GitHub-GR00T--Dreams-ff8800?logo=github)](https://github.com/NVIDIA/GR00T-Dreams) |
| 2025 | GigaWorld-0 | [GigaWorld-0: World Models as Data Engine to Empower Embodied AI](https://arxiv.org/abs/2511.19861) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://giga-world-0.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-giga--world--0-ff8800?logo=github)](https://github.com/open-gigaai/giga-world-0) |
| 2025 | ProphRL | [Reinforcing Action Policies by Prophesying](https://arxiv.org/abs/2511.20633) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://LogosRoboticsGroup.github.io/ProphRL) | [![GitHub](https://img.shields.io/badge/GitHub-ProphRL-ff8800?logo=github)](https://github.com/LogosRoboticsGroup/ProphRL) |
| 2025 | VLA-RFT | [VLA-RFT: Vision-Language-Action Reinforcement Fine-tuning with Verified Rewards in World Simulators](https://arxiv.org/abs/2510.00406) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://vla-rft.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-VLA--RFT-ff8800?logo=github)](https://github.com/OpenHelix-Team/VLA-RFT) |
| 2025 | World-Env | [World-Env: Leveraging World Model as a Virtual Environment for VLA Post-Training](https://arxiv.org/abs/2509.24948) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://isee-laboratory.github.io/world-env.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-world--env-ff8800?logo=github)](https://github.com/amap-cvlab/world-env) |
| 2025 | World4RL | [World4RL: Diffusion World Models for Policy Refinement with Reinforcement Learning for Robotic Manipulation](https://arxiv.org/abs/2509.19080) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://world4rl.github.io/) |  |
| 2025 | WorldEval | [WorldEval: World Model as Real-World Robot Policies Evaluator](https://arxiv.org/abs/2505.19017) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://worldeval.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-Worldeval-ff8800?logo=github)](https://github.com/liyaxuanliyaxuan/Worldeval) |
| 2025 | WorldGym | [WorldGym: World Model as An Environment for Policy Evaluation](https://arxiv.org/abs/2506.00613) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://world-model-eval.github.io) | [![GitHub](https://img.shields.io/badge/GitHub-world--model--eval-ff8800?logo=github)](https://github.com/world-model-eval/world-model-eval) |
| 2024 | 3DFF | [Sim-to-Real Transfer via 3D Feature Fields for Vision-and-Language Navigation](https://arxiv.org/abs/2406.09798) | CoRL |  | [![GitHub](https://img.shields.io/badge/GitHub-Sim2Real--VLN--3DFF-ff8800?logo=github)](https://github.com/MrZihan/Sim2Real-VLN-3DFF) |
| 2024 | UniSim | [Learning Interactive Real-World Simulators](https://arxiv.org/abs/2310.06114) | ICLR | [![link](https://img.shields.io/badge/Website-9cf)](https://universal-simulator.github.io/) |  |
| 2023 | DayDreamer | [DayDreamer: World Models for Physical Robot Learning](https://arxiv.org/abs/2206.14176) | CoRL | [![link](https://img.shields.io/badge/Website-9cf)](https://danijar.com/project/daydreamer/) | [![GitHub](https://img.shields.io/badge/GitHub-daydreamer-ff8800?logo=github)](https://github.com/danijar/daydreamer) |
| 2023 | DreamerV3 | [Mastering Diverse Domains through World Models](https://arxiv.org/abs/2301.04104) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://danijar.com/project/dreamerv3/) | [![GitHub](https://img.shields.io/badge/GitHub-dreamerv3-ff8800?logo=github)](https://github.com/danijar/dreamerv3) |
| 2020 | Dreamer | [Dream to Control: Learning Behaviors by Latent Imagination](https://arxiv.org/abs/1912.01603) | ICLR | [![link](https://img.shields.io/badge/Website-9cf)](https://danijar.com/project/dreamer/) | [![GitHub](https://img.shields.io/badge/GitHub-dreamer-ff8800?logo=github)](https://github.com/danijar/dreamer) |
| 2019 | PlaNet | [Learning Latent Dynamics for Planning from Pixels](https://arxiv.org/abs/1811.04551) | ICML | [![link](https://img.shields.io/badge/Website-9cf)](https://danijar.com/project/planet/) | [![GitHub](https://img.shields.io/badge/GitHub-planet-ff8800?logo=github)](https://github.com/google-research/planet) |
| 2018 | World Models | [Recurrent World Models Facilitate Policy Evolution](https://arxiv.org/abs/1809.01999) | NeurIPS | [![link](https://img.shields.io/badge/Website-9cf)](https://worldmodels.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-WorldModelsExperiments-ff8800?logo=github)](https://github.com/hardmaru/WorldModelsExperiments) |
| 2016 |  | [DeepMind Lab](https://arxiv.org/abs/1612.03801) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://deepmind.google/blog/open-sourcing-deepmind-lab/) | [![GitHub](https://img.shields.io/badge/GitHub-lab-ff8800?logo=github)](https://github.com/google-deepmind/lab) |

</details>


### General Data

#### Visual Data

<details open id="table-general-visual-data">
<summary>Table: Visual data</summary>

| Year | Acronym | Paper | Venue | Project | Repo@GitHub |
|------|---------|-------|-------|---------|-------------|
| 2025 | FiRE | [FiRE: Enhancing MLLMs with Fine-Grained Context Learning for Complex Image Retrieval](https://dl.acm.org/doi/10.1145/3726302.3729979) | SIGIR |  |  |
| 2025 | RoboAfford++ | [RoboAfford++: A Generative AI-Enhanced Dataset for Multimodal Affordance Learning in Robotic Manipulation and Navigation](https://arxiv.org/abs/2511.12436) | arXiv | [![link](https://img.shields.io/badge/Website-9cf)](https://roboafford-dataset.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-RoboAfford-ff8800?logo=github)](https://github.com/tyb197/RoboAfford) |
| 2024 | LLaVA-OneVision-SI | [LLaVA-OneVision: Easy Visual Task Transfer](https://arxiv.org/abs/2408.03326) | TMLR | [![link](https://img.shields.io/badge/Website-9cf)](https://huggingface.co/datasets/lmms-lab/LLaVA-OneVision-Data) | [![GitHub](https://img.shields.io/badge/GitHub-LLaVA--NeXT-ff8800?logo=github)](https://github.com/LLaVA-VL/LLaVA-NeXT) |
| 2024 | LLaVA-Video-178K | [LLaVA-Video-178K: Video Instruction Tuning With Synthetic Data](https://arxiv.org/abs/2410.02713) | TMLR | [![link](https://img.shields.io/badge/Website-9cf)](https://huggingface.co/datasets/lmms-lab/LLaVA-Video-178K) | [![GitHub](https://img.shields.io/badge/GitHub-LLaVA--NeXT-ff8800?logo=github)](https://github.com/LLaVA-VL/LLaVA-NeXT) |
| 2024 | MultiUI | [Harnessing Webpage UIs for Text-Rich Visual Understanding](https://arxiv.org/abs/2410.13824) | ICLR | [![link](https://img.shields.io/badge/Website-9cf)](https://neulab.github.io/MultiUI/) | [![GitHub](https://img.shields.io/badge/GitHub-MultiUI-ff8800?logo=github)](https://github.com/neulab/MultiUI) |
| 2024 | PixMo | [Molmo and PixMo: Open Weights and Open Data for State-of-the-Art Vision-Language Models](https://arxiv.org/abs/2409.17146) | CVPR | [![link](https://img.shields.io/badge/Website-9cf)](https://huggingface.co/collections/allenai/pixmo) | [![GitHub](https://img.shields.io/badge/GitHub-molmo-ff8800?logo=github)](https://github.com/allenai/molmo) |
| 2024 | PixMo-Points | [Molmo and PixMo: Open Weights and Open Data for State-of-the-Art Vision-Language Models](https://arxiv.org/abs/2409.17146) | CVPR | [![link](https://img.shields.io/badge/Website-9cf)](https://huggingface.co/datasets/allenai/pixmo-points) | [![GitHub](https://img.shields.io/badge/GitHub-molmo-ff8800?logo=github)](https://github.com/allenai/molmo) |
| 2024 | RoboPoint | [RoboPoint: A Vision-Language Model for Spatial Affordance Prediction for Robotics](https://arxiv.org/abs/2406.10721) | CoRL | [![link](https://img.shields.io/badge/Website-9cf)](https://huggingface.co/datasets/wentao-yuan/robopoint-data) | [![GitHub](https://img.shields.io/badge/GitHub-RoboPoint-ff8800?logo=github)](https://github.com/wentaoyuan/RoboPoint) |
| 2023 | PACO-LVIS | [PACO: Parts and Attributes of Common Objects](https://arxiv.org/abs/2301.01795) | CVPR | [![link](https://img.shields.io/badge/Website-9cf)](https://paco.csail.mit.edu/) | [![GitHub](https://img.shields.io/badge/GitHub-paco-ff8800?logo=github)](https://github.com/facebookresearch/paco) |
| 2023 | SA-1B | [Segment Anything (SA-1B dataset)](https://arxiv.org/abs/2304.02643) | ICCV | [![link](https://img.shields.io/badge/Website-9cf)](https://segment-anything.com) | [![GitHub](https://img.shields.io/badge/GitHub-segment--anything-ff8800?logo=github)](https://github.com/facebookresearch/segment-anything) |
| 2023 | ShareGPT4V | [ShareGPT4V: Improving Large Multi-Modal Models with Better Captions](https://arxiv.org/abs/2311.12793) | ECCV | [![link](https://img.shields.io/badge/Website-9cf)](https://sharegpt4v.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-ShareGPT4V-ff8800?logo=github)](https://github.com/ShareGPT4Omni/ShareGPT4V) |
| 2022 | ChartQA | [ChartQA: A Benchmark for Question Answering about Charts with Visual and Logical Reasoning](https://arxiv.org/abs/2203.10244) | ACL |  | [![GitHub](https://img.shields.io/badge/GitHub-ChartQA-ff8800?logo=github)](https://github.com/vis-nlp/ChartQA) |
| 2021 | Ego4D NLQ | [Ego4D: Around the World in 3,000 Hours of Egocentric Video](https://arxiv.org/abs/2110.07058) | CVPR | [![link](https://img.shields.io/badge/Website-9cf)](https://ego4d-data.org/) | [![GitHub](https://img.shields.io/badge/GitHub-Ego4d-ff8800?logo=github)](https://github.com/facebookresearch/Ego4d) |
| 2021 | TextOCR | [TextOCR: Towards Large-Scale End-to-End Reasoning for Arbitrary-Shaped Scene Text](https://arxiv.org/abs/2105.05486) | CVPR | [![link](https://img.shields.io/badge/Website-9cf)](https://textvqa.org/textocr/) |  |
| 2020 | DocVQA | [DocVQA: A Dataset for VQA on Document Images](https://arxiv.org/abs/2007.00398) | WACV | [![link](https://img.shields.io/badge/Website-9cf)](https://www.docvqa.org/) |  |
| 2017 | Visual Genome | [Visual Genome: Connecting Language and Vision Using Crowdsourced Dense Image Annotations](https://arxiv.org/abs/1602.07332) | IJCV | [![link](https://img.shields.io/badge/Website-9cf)](https://visualgenome.org/) | [![GitHub](https://img.shields.io/badge/GitHub-visual_genome_python_driver-ff8800?logo=github)](https://github.com/ranjaykrishna/visual_genome_python_driver) |
| 2016 | ADE20K | [Semantic Understanding of Scenes through the ADE20K Dataset](https://arxiv.org/abs/1608.05442) | IJCV | [![link](https://img.shields.io/badge/Website-9cf)](https://ade20k.csail.mit.edu/) | [![GitHub](https://img.shields.io/badge/GitHub-ADE20K-ff8800?logo=github)](https://github.com/CSAILVision/ADE20K) |
| 2016 | RefCOCO | [Modeling Context in Referring Expressions](https://arxiv.org/abs/1608.00272) | ECCV |  | [![GitHub](https://img.shields.io/badge/GitHub-refer-ff8800?logo=github)](https://github.com/lichengunc/refer) |
| 2015 | VQA | [VQA: Visual Question Answering](https://arxiv.org/abs/1505.00468) | ICCV | [![link](https://img.shields.io/badge/Website-9cf)](https://visualqa.org) | [![GitHub](https://img.shields.io/badge/GitHub-VQA-ff8800?logo=github)](https://github.com/GT-Vision-Lab/VQA) |
| 2014 | COCO | [Microsoft COCO: Common Objects in Context](https://arxiv.org/abs/1405.0312) | ECCV | [![link](https://img.shields.io/badge/Website-9cf)](https://cocodataset.org) | [![GitHub](https://img.shields.io/badge/GitHub-cocoapi-ff8800?logo=github)](https://github.com/cocodataset/cocoapi) |
| 2019 | Objects365 | [Objects365: A Large-Scale, High-Quality Dataset for Object Detection](https://ieeexplore.ieee.org/document/9009553) | ICCV | [![link](https://img.shields.io/badge/Website-9cf)](https://www.objects365.org/) |  |

</details>

#### Segmentation & Localization

<details open id="table-general-segmentation-localization">
<summary>Table: Segmentation and localization data</summary>

| Year | Acronym | Paper | Venue | Project | Repo@GitHub |
|------|---------|-------|-------|---------|-------------|
| 2025 | PTG-FSCIR | [Pseudo-triplet Guided Few-shot Composed Image Retrieval](https://arxiv.org/abs/2407.06001) | IJCNN |  |  |
| 2024 | MMScan | [MMScan: A Multi-Modal 3D Scene Dataset with Hierarchical Grounded Language Annotations](https://arxiv.org/abs/2406.09401) | NeurIPS | [![link](https://img.shields.io/badge/Website-9cf)](https://tai-wang.github.io/mmscan/) | [![GitHub](https://img.shields.io/badge/GitHub-EmbodiedScan-ff8800?logo=github)](https://github.com/OpenRobotLab/EmbodiedScan) |
| 2023 | VL-Grasp | [VL-Grasp: a 6-Dof Interactive Grasp Policy for Language-Oriented Objects in Cluttered Indoor Scenes](https://arxiv.org/abs/2308.00640) | IROS | [![link](https://img.shields.io/badge/Website-9cf)](https://luyh20.github.io/RoboRefIt.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-VL--Grasp-ff8800?logo=github)](https://github.com/luyh20/VL-Grasp) |
| 2022 | SQA3D | [SQA3D: Situated Question Answering in 3D Scenes](https://arxiv.org/abs/2210.07474) | ICLR | [![link](https://img.shields.io/badge/Website-9cf)](https://sqa3d.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-SQA3D-ff8800?logo=github)](https://github.com/SilongYong/SQA3D) |
| 2022 | VOST | [Breaking the "Object" in Video Object Segmentation](https://arxiv.org/abs/2212.06200) | CVPR | [![link](https://img.shields.io/badge/Website-9cf)](https://www.vostdataset.org/) |  |
| 2021 | ARKitScenes | [ARKitScenes: A Diverse Real-World Dataset for 3D Indoor Scene Understanding Using Mobile RGB-D Data](https://arxiv.org/abs/2111.08897) | NeurIPS | [![link](https://img.shields.io/badge/Website-9cf)](https://machinelearning.apple.com/research/arkitscenes) | [![GitHub](https://img.shields.io/badge/GitHub-ARKitScenes-ff8800?logo=github)](https://github.com/apple/ARKitScenes) |
| 2021 | ScanQA | [ScanQA: 3D Question Answering for Spatial Scene Understanding](https://arxiv.org/abs/2112.10482) | CVPR |  | [![GitHub](https://img.shields.io/badge/GitHub-ScanQA-ff8800?logo=github)](https://github.com/ATR-DBI/ScanQA) |
| 2020 | 3DSSG | [Learning 3D Semantic Scene Graphs from 3D Indoor Reconstructions](https://arxiv.org/abs/2004.03967) | CVPR | [![link](https://img.shields.io/badge/Website-9cf)](https://3dssg.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-3DSSG-ff8800?logo=github)](https://github.com/ShunChengWu/3DSSG) |
| 2019 | 3RScan | [RIO: 3D Object Instance Re-Localization in Changing Indoor Environments](https://arxiv.org/abs/1908.06109) | ICCV | [![link](https://img.shields.io/badge/Website-9cf)](https://waldjohannau.github.io/RIO/) | [![GitHub](https://img.shields.io/badge/GitHub-3RScan-ff8800?logo=github)](https://github.com/WaldJohannaU/3RScan) |
| 2019 | ALFRED | [ALFRED: A Benchmark for Interpreting Grounded Instructions for Everyday Tasks](https://arxiv.org/abs/1912.01734) | CVPR | [![link](https://img.shields.io/badge/Website-9cf)](https://askforalfred.com/) | [![GitHub](https://img.shields.io/badge/GitHub-alfred-ff8800?logo=github)](https://github.com/askforalfred/alfred) |
| 2019 | CLEVRER | [CLEVRER: Collision Events for Video Representation and Reasoning](https://arxiv.org/abs/1910.01442) | ICLR | [![link](https://img.shields.io/badge/Website-9cf)](http://clevrer.csail.mit.edu/) | [![GitHub](https://img.shields.io/badge/GitHub-CLEVRER-ff8800?logo=github)](https://github.com/chuangg/CLEVRER) |
| 2019 | LVIS | [LVIS: A Dataset for Large Vocabulary Instance Segmentation](https://arxiv.org/abs/1908.03195) | CVPR | [![link](https://img.shields.io/badge/Website-9cf)](https://www.lvisdataset.org) | [![GitHub](https://img.shields.io/badge/GitHub-lvis--api-ff8800?logo=github)](https://github.com/lvis-dataset/lvis-api) |
| 2016 | COLMAP | [Structure-from-Motion Revisited](https://openaccess.thecvf.com/content_cvpr_2016/html/Schonberger_Structure-From-Motion_Revisited_CVPR_2016_paper.html) | CVPR | [![link](https://img.shields.io/badge/Website-9cf)](https://colmap.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-colmap-ff8800?logo=github)](https://github.com/colmap/colmap) |
| 2015 | ORB-SLAM | [ORB-SLAM: A Versatile and Accurate Monocular SLAM System](https://arxiv.org/abs/1502.00956) | T-RO | [![link](https://img.shields.io/badge/Website-9cf)](https://webdiis.unizar.es/~raulmur/orbslam/) | [![GitHub](https://img.shields.io/badge/GitHub-ORB_SLAM-ff8800?logo=github)](https://github.com/raulmur/ORB_SLAM) |
| 2012 |  | [Indoor Segmentation and Support Inference from RGBD Images](https://link.springer.com/chapter/10.1007/978-3-642-33715-4_54) | ECCV | [![link](https://img.shields.io/badge/Website-9cf)](https://cs.nyu.edu/~silberman/projects/indoor_scene_seg_sup.html) |  |

</details>

#### Video & Temporal Data

<details open id="table-general-video-temporal">
<summary>Table: Video and temporal data</summary>

| Year | Acronym | Paper | Venue | Project | Repo@GitHub |
|------|---------|-------|-------|---------|-------------|
| 2026 | RoVid-X | [Rethinking Video Generation Model for the Embodied World](https://arxiv.org/abs/2601.15282) | ICML | [![link](https://img.shields.io/badge/Website-9cf)](https://huggingface.co/datasets/DAGroup-PKU/RoVid-X) | [![GitHub](https://img.shields.io/badge/GitHub-ReVidgen-ff8800?logo=github)](https://github.com/DAGroup-PKU/ReVidgen) |
| 2024 | Moment-10M | [Momentor: Advancing Video Large Language Model with Fine-Grained Temporal Reasoning](https://arxiv.org/abs/2402.11435) | ICML |  | [![GitHub](https://img.shields.io/badge/GitHub-Momentor-ff8800?logo=github)](https://github.com/DCDmllm/Momentor) |
| 2024 | RH20T-P | [RH20T-P: A Primitive-Level Robotic Manipulation Dataset Towards Composable Generalization Agents in Real-world Scenarios](https://doi.org/10.1109/iros60139.2025.11246228) | IROS | [![link](https://img.shields.io/badge/Website-9cf)](https://sites.google.com/view/rh20t-primitive/main) |  |
| 2023 | HiREST | [Hierarchical Video-Moment Retrieval and Step-Captioning](https://arxiv.org/abs/2303.16406) | CVPR | [![link](https://img.shields.io/badge/Website-9cf)](https://hirest-cvpr2023.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-HiREST-ff8800?logo=github)](https://github.com/j-min/HiREST) |
| 2023 | RoboFail | [REFLECT: Summarizing Robot Experiences for Failure Explanation and Correction (RoboFail dataset)](https://arxiv.org/abs/2306.15724) | CoRL | [![link](https://img.shields.io/badge/Website-9cf)](https://roboreflect.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-reflect-ff8800?logo=github)](https://github.com/real-stanford/reflect) |
| 2023 | RoboVQA | [RoboVQA: Multimodal Long-Horizon Reasoning for Robotics](https://arxiv.org/abs/2311.00899) | ICRA | [![link](https://img.shields.io/badge/Website-9cf)](https://robovqa.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-robovqa-ff8800?logo=github)](https://github.com/google-deepmind/robovqa) |
| 2019 | COIN | [COIN: A Large-scale Dataset for Comprehensive Instructional Video Analysis](https://arxiv.org/abs/1903.02874) | CVPR | [![link](https://img.shields.io/badge/Website-9cf)](https://coin-dataset.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-annotations-ff8800?logo=github)](https://github.com/coin-dataset/annotations) |
| 2019 | RoboNet | [RoboNet: Large-Scale Multi-Robot Learning](https://arxiv.org/abs/1910.11215) | CoRL | [![link](https://img.shields.io/badge/Website-9cf)](https://www.robonet.wiki/) | [![GitHub](https://img.shields.io/badge/GitHub-RoboNet-ff8800?logo=github)](https://github.com/SudeepDasari/RoboNet) |
| 2018 | IntPhys | [IntPhys: A Framework and Benchmark for Visual Intuitive Physics Reasoning](https://arxiv.org/abs/1803.07616) | TPAMI | [![link](https://img.shields.io/badge/Website-9cf)](https://intphys.cognitive-ml.fr/) | [![GitHub](https://img.shields.io/badge/GitHub-IntPhys--Baselines-ff8800?logo=github)](https://github.com/rronan/IntPhys-Baselines) |
| 2017 | Charades-STA | [TALL: Temporal Activity Localization via Language Query (Charades-STA dataset)](https://arxiv.org/abs/1705.02101) | ICCV |  | [![GitHub](https://img.shields.io/badge/GitHub-TALL-ff8800?logo=github)](https://github.com/jiyanggao/TALL) |
| 2017 | DiDeMo | [Localizing Moments in Video with Natural Language](https://arxiv.org/abs/1708.01641) | ICCV | [![link](https://img.shields.io/badge/Website-9cf)](https://people.eecs.berkeley.edu/~lisa_anne/didemo.html) | [![GitHub](https://img.shields.io/badge/GitHub-LocalizingMoments-ff8800?logo=github)](https://github.com/LisaAnne/LocalizingMoments) |
| 2017 | ScanNet | [ScanNet: Richly-annotated 3D Reconstructions of Indoor Scenes](https://arxiv.org/abs/1702.04405) | CVPR | [![link](https://img.shields.io/badge/Website-9cf)](http://www.scan-net.org/) | [![GitHub](https://img.shields.io/badge/GitHub-ScanNet-ff8800?logo=github)](https://github.com/ScanNet/ScanNet) |
| 2011 | Cornell Grasp Dataset | [Efficient Grasping from RGBD Images: Learning using a New Rectangle Representation](https://doi.org/10.1109/ICRA.2011.5980145) | ICRA | [![link](https://img.shields.io/badge/Website-9cf)](http://pr.cs.cornell.edu/grasping/rect_data/data.php) |  |
| 2022 | InfLevel | [Benchmarking Progress to Infant-Level Physical Reasoning in AI](https://openreview.net/forum?id=9NjqD9i48M) | TMLR |  | [![GitHub](https://img.shields.io/badge/GitHub-inflevel-ff8800?logo=github)](https://github.com/allenai/inflevel) |
| 2019 | OCR-VQA | [OCR-VQA: Visual Question Answering by Reading Text in Images](https://ieeexplore.ieee.org/document/8978122/) | ICDAR | [![link](https://img.shields.io/badge/Website-9cf)](https://ocr-vqa.github.io/) |  |
| 2025 | RobAVA | [RobAVA: A Large-scale Dataset and Baseline Towards Video-based Robotic Arm Action Understanding](https://openaccess.thecvf.com/content/ICCV2025/papers/Sun_RobAVA_A_Large-scale_Dataset_and_Baseline_Towards_Video_based_Robotic_ICCV_2025_paper.pdf) | ICCV |  | [![GitHub](https://img.shields.io/badge/GitHub-RobAVA-ff8800?logo=github)](https://github.com/Sunbaoli/RobAVA) |

</details>

#### Planning / Task Decomposition

<details open id="table-general-planning-task-decomposition">
<summary>Table: Planning and task decomposition data</summary>

| Year | Acronym | Paper | Venue | Project | Repo@GitHub |
|------|---------|-------|-------|---------|-------------|
| 2023 | EgoPlan-IT | [EgoPlan-Bench: Benchmarking Multimodal Large Language Models for Human-Level Planning](https://arxiv.org/abs/2312.06722) | IJCV | [![link](https://img.shields.io/badge/Website-9cf)](https://chenyi99.github.io/ego_plan/) | [![GitHub](https://img.shields.io/badge/GitHub-EgoPlan-ff8800?logo=github)](https://github.com/ChenYi99/EgoPlan) |
| 2023 | EmbodiedGPT | [EmbodiedGPT: Vision-Language Pre-Training via Embodied Chain of Thought](https://arxiv.org/abs/2305.15021) | NeurIPS | [![link](https://img.shields.io/badge/Website-9cf)](https://embodiedgpt.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-EmbodiedGPT-ff8800?logo=github)](https://github.com/OpenGVLab/EmbodiedGPT) |
| 2023 | LLaRP | [Large Language Models as Generalizable Policies for Embodied Tasks](https://arxiv.org/abs/2310.17722) | ICLR | [![link](https://img.shields.io/badge/Website-9cf)](https://llm-rl.github.io/) | [![GitHub](https://img.shields.io/badge/GitHub-ml--llarp-ff8800?logo=github)](https://github.com/apple/ml-llarp) |
| 2022 | EgoTaskQA | [EgoTaskQA: Understanding Human Tasks in Egocentric Videos](https://arxiv.org/abs/2210.03929) | NeurIPS | [![link](https://img.shields.io/badge/Website-9cf)](https://sites.google.com/view/egotaskqa) | [![GitHub](https://img.shields.io/badge/GitHub-EgoTaskQA-ff8800?logo=github)](https://github.com/Buzz-Beater/EgoTaskQA) |
| 2025 | WAP | [World-aware Planning Narratives Enhance Large Vision-Language Model Planner](https://arxiv.org/abs/2506.21230) | NeurIPS | [![link](https://img.shields.io/badge/Website-9cf)](https://huggingface.co/datasets/sii-research/World-Aware-Planning) | [![GitHub](https://img.shields.io/badge/GitHub-World--Aware--Planning-ff8800?logo=github)](https://github.com/sjh0354/World-Aware-Planning) |

</details>

#### Grasp Data

<details open id="table-general-grasp-data">
<summary>Table: Grasp data</summary>

| Year | Acronym | Paper | Venue | Project | Repo@GitHub |
|------|---------|-------|-------|---------|-------------|
| 2026 | MapleGrasp | [MapleGrasp: Mask-guided Feature Pooling for Language-driven Efficient Robotic Grasping](https://arxiv.org/abs/2506.06535) | WACV |  | [![GitHub](https://img.shields.io/badge/GitHub-MapleGrasp-ff8800?logo=github)](https://github.com/vineet2104/MapleGrasp) |
| 2024 |  | [Language-Driven 6-DoF Grasp Detection Using Negative Prompt Guidance](https://arxiv.org/abs/2407.13842) | ECCV | [![link](https://img.shields.io/badge/Website-9cf)](https://airvlab.github.io/grasp-anything/docs/grasp-anything-6d/) | [![GitHub](https://img.shields.io/badge/GitHub-Language--Driven--6--DoF--Grasp--Detection--Using--Negative--Prompt--Guidance-ff8800?logo=github)](https://github.com/Fsoft-AIC/Language-Driven-6-DoF-Grasp-Detection-Using-Negative-Prompt-Guidance) |
| 2024 | DexGraspNet 2.0 | [DexGraspNet 2.0: Learning Generative Dexterous Grasping in Large-scale Synthetic Cluttered Scenes](https://arxiv.org/abs/2410.23004) | CoRL | [![link](https://img.shields.io/badge/Website-9cf)](https://pku-epic.github.io/DexGraspNet2.0/) | [![GitHub](https://img.shields.io/badge/GitHub-DexGraspNet2-ff8800?logo=github)](https://github.com/PKU-EPIC/DexGraspNet2) |
| 2024 | Grasp-Anything | [Grasp-Anything: Large-scale Grasp Dataset from Foundation Models](https://arxiv.org/abs/2309.09818) | ICRA | [![link](https://img.shields.io/badge/Website-9cf)](https://airvlab.github.io/grasp-anything/) | [![GitHub](https://img.shields.io/badge/GitHub-Grasp--Anything-ff8800?logo=github)](https://github.com/Fsoft-AIC/Grasp-Anything) |
| 2021 | SuctionNet-1Billion | [SuctionNet-1Billion: A Large-Scale Benchmark for Suction Grasping](https://arxiv.org/abs/2103.12311) | RAL | [![link](https://img.shields.io/badge/Website-9cf)](https://graspnet.net/suction) | [![GitHub](https://img.shields.io/badge/GitHub-suctionnetAPI-ff8800?logo=github)](https://github.com/graspnet/suctionnetAPI) |
| 2018 | Jacquard | [Jacquard: A Large Scale Dataset for Robotic Grasp Detection](https://arxiv.org/abs/1803.11469) | IROS | [![link](https://img.shields.io/badge/Website-9cf)](https://jacquard.liris.cnrs.fr) |  |
| 2020 | GraspNet-1Billion | [GraspNet-1Billion: A Large-Scale Benchmark for General Object Grasping](https://openaccess.thecvf.com/content_CVPR_2020/html/Fang_GraspNet-1Billion_A_Large-Scale_Benchmark_for_General_Object_Grasping_CVPR_2020_paper.html) | CVPR | [![link](https://img.shields.io/badge/Website-9cf)](https://graspnet.net) | [![GitHub](https://img.shields.io/badge/GitHub-graspnet--baseline-ff8800?logo=github)](https://github.com/graspnet/graspnet-baseline) |

</details>

## Embodied Foundation Models

### Representative VLA and WAM Methods

Representative VLA and WAM methods by release time, model type, institution, and data source.

Data sources: `Real` = real-robot data; `UMI` = UMI data; `Ego` = egocentric data; `Sim` = simulation data; `General` = general data.

<details open id="table-embodied-foundation-models-vla-wam">
<summary>Table: Representative VLA and WAM methods (66 entries)</summary>

| Time | Method | Institution | Project | Model | Data |
|------|--------|-------------|---------|-------|------|
| 2023.3 | PaLM-E | Google | [Project](https://palm-e.github.io/) | VLA | Real / Sim / General |
| 2023.7 | RT-2 | DeepMind | [Project](https://robotics-transformer2.github.io/) | VLA | Real / General |
| 2024.5 | Octo | UC Berkeley | [Project](https://octo-models.github.io/) | VLA | Real |
| 2024.6 | OpenVLA | Stanford University | [Project](https://openvla.github.io/) | VLA | Real |
| 2024.10 | GR-2 | ByteDance | [Project](https://gr2-manipulation.github.io/) | VLA | Real / Ego |
| 2024.10 | π0 | Physical Intelligence | [Blog](https://www.pi.website/blog/pi0) | VLA | Real |
| 2024.10 | RDT-1B | THU | [Project](https://rdt-robotics.github.io/rdt-robotics/) | VLA | Real |
| 2024.11 | CogACT | THU | [Project](https://cogact.github.io/) | VLA | Real |
| 2025.1 | SpatialVLA | Shanghai AI Lab | [GitHub](https://github.com/SpatialVLA/SpatialVLA) | VLA | Real |
| 2025.1 | UP-VLA | THU | [GitHub](https://github.com/CladernyJorn/UP-VLA) | VLA | Real / General |
| 2025.3 | HybridVLA | PKU | [Project](https://hybrid-vla.github.io/) | VLA | Real |
| 2025.3 | GR00T N1 | NVIDIA | [GitHub](https://github.com/NVIDIA/Isaac-GR00T) | VLA | Real / Ego / Sim |
| 2025.3 | CoT-VLA | NVIDIA | [Project](https://cot-vla.github.io/) | VLA | Real / Ego / General |
| 2025.4 | UWM | University of Washington | [Project](https://weirdlabuw.github.io/uwm/) | WAM | Real |
| 2025.4 | π0.5 | Physical Intelligence | [Blog](https://www.pi.website/blog/pi05) | VLA | Real / General |
| 2025.5 | UniVLA | HKU | [GitHub](https://github.com/OpenDriveLab/UniVLA) | VLA | Real / Ego |
| 2025.6 | SmolVLA | Hugging Face | [Model](https://huggingface.co/lerobot/smolvla_base) | VLA | Real |
| 2025.6 | GR00T N1.5 | NVIDIA | [Project](https://research.nvidia.com/labs/gear/gr00t-n1_5/) | VLA | Real / Sim |
| 2025.7 | DreamVLA | SJTU | [Project](https://zhangwenyao1.github.io/DreamVLA/) | VLA | Real / Sim |
| 2025.7 | EgoVLA | UC San Diego | [Project](https://rchalyang.github.io/EgoVLA/) | VLA | Ego |
| 2025.7 | Being-H0 | PKU | [Project](https://beingbeyond.github.io/Being-H0/) | VLA | Ego |
| 2025.7 | GR-3 | ByteDance Seed | [Project](https://seed.bytedance.com/GR3) | VLA | Real / Ego / General |
| 2025.7 | H-RDT | THU | [Project](https://embodiedfoundation.github.io/hrdt) | VLA | Ego |
| 2025.8 | GalaxeaVLA(G0) | Galaxea | [Project](https://opengalaxea.github.io/G0/) | VLA | Real |
| 2025.8 | ReconVLA | HKUST | [Project](https://zionchow.github.io/ReconVLA/) | VLA | Real / Sim |
| 2025.9 | RynnVLA-001 | DAMO | [GitHub](https://github.com/alibaba-damo-academy/RynnVLA-001) | VLA | Real / Ego |
| 2025.10 | X-VLA | THU | [Project](https://thu-air-dream.github.io/X-VLA/) | VLA | Real |
| 2025.10 | InternVLA-M1 | Shanghai AI Lab | [Project](https://internrobotics.github.io/internvla-m1.github.io/) | VLA | Real / Sim / General |
| 2025.10 | VITRA | THU | [Project](https://microsoft.github.io/VITRA/) | VLA | Ego |
| 2025.11 | METIS | PKU | [Paper](https://arxiv.org/abs/2511.17366) | VLA | Real / Ego |
| 2025.12 | VideoVLA | XJTU | [Project](https://videovla-nips2025.github.io/) | VLA | Real |
| 2025.12 | Motus | THU | [Project](https://motus-robotics.github.io/motus) | WAM | Real / Ego / Sim / General |
| 2025.12 | GR00T N1.6 | NVIDIA | [GitHub](https://github.com/NVIDIA/Isaac-GR00T) | VLA | Real / Sim |
| 2026.1 | InternVLA-A1 | Shanghai AI Lab | [GitHub](https://github.com/InternRobotics/InternVLA-A1) | VLA | Real / Ego / Sim |
| 2026.1 | LaST_0 | PKU | [Project](https://vla-last0.github.io/) | VLA | Real |
| 2026.1 | Being-H0.5 | BeingBeyond | [Project](https://research.beingbeyond.com/being-h05) | VLA | Real / Ego / Sim / General |
| 2026.1 | LingbotVLA | Ant Group | [Project](https://technology.robbyant.com/lingbot-vla) | VLA | Real |
| 2026.1 | LingbotVA | Ant Group | [Project](https://technology.robbyant.com/lingbot-va) | WAM | Real / UMI / Sim |
| 2026.2 | RDT2 | THU | [Project](https://rdt-robotics.github.io/rdt2/) | VLA | UMI / General |
| 2026.2 | Xiaomi-Robotics-0 | Xiaomi | [Project](https://robotics.xiaomi.com/xiaomi-robotics-0.html) | VLA | Real / General |
| 2026.2 | ABot-M0 | AMAP CV Lab | [Project](https://amap-cvlab.github.io/ABot-Manipulation/m0/index.html) | VLA | Real |
| 2026.2 | DM0 | Dexmal | [GitHub](https://github.com/Dexmal/dexbotic) | VLA | Real / Sim / General |
| 2026.2 | LDA-1B | PKU | [GitHub](https://github.com/jiangranlv/LDA-1B) | WAM | Real / Ego / Sim |
| 2026.2 | DreamZero | NVIDIA | [Project](https://dreamzero0.github.io/) | WAM | Real |
| 2026.2 | EgoScale | NVIDIA | [Project](https://research.nvidia.com/labs/gear/egoscale/) | VLA | Real / Ego |
| 2026.3 | GigaWorld-Policy | GigaAI | [GitHub](https://github.com/open-gigaai/giga-world-policy) | WAM | Real / Ego / General |
| 2026.3 | UniDex | THU | [Project](https://unidex-ai.github.io/) | VLA | Ego |
| 2026.4 | JoyAI-RA 0.1 | JD | [Project](https://joyai-ra.github.io/) | VLA | Real / Ego / Sim / General |
| 2026.4 | π0.7 | Physical Intelligence | [Blog](https://www.pi.website/blog/pi07) | VLA | Real / Ego / General |
| 2026.4 | GR00T N1.7 | NVIDIA | [Project](https://developer.nvidia.com/isaac/gr00t) | VLA | Real / Ego / Sim |
| 2026.4 | Being-H0.7 | BeingBeyond | [Project](https://research.beingbeyond.com/being-h07) | WAM | Real / Ego / Sim / General |
| 2026.4 | MotuBrain | Shengshu | [Project](https://www.motubrain.com/en/) | WAM | Real / Ego / General |
| 2026.5 | Qwen-VLA | Qwen | [Blog](https://qwen.ai/blog?id=qwenvla) | VLA | Real / Ego / Sim / General |
| 2026.5 | Wall-OSS-0.5 | X Square Robot | [Project](https://x2robot.com/oss#resources) | VLA | Real / General |
| 2026.6 | Wall-WM | X Square Robot | [GitHub](https://github.com/X-Square-Robot/wall-x) | WAM | Real / UMI / Ego / General |
| 2026.6 | LaST-HD | PKU | [Project](https://siriyep.github.io/last-hd-project-page/) | VLA | Real / Ego |
| 2026.6 | Hy-Embodied-0.5-VLA | Tencent Robotics X | [GitHub](https://github.com/Tencent-Hunyuan/Hy-Embodied-0.5-VLA) | VLA | UMI |
| 2026.6 | Qwen-RobotManip | Qwen | [Blog](https://qwen.ai/blog?id=qwen-robotmanip) | VLA | Real / Ego / Sim / General |
| 2026.7 | ABot-M0.5 | AMAP CV Lab | [GitHub](https://github.com/amap-cvlab/ABot-Manipulation) | WAM | Real / Sim |
| 2026.7 | ACE-Brain-0.5 | ACE-Robotics | [GitHub](https://github.com/ACE-BRAIN-Team/ACE-Brain-0.5) | VLA | Real / General |
| 2026.7 | InternVLA-A1.5 | Shanghai AI Lab | [Project](https://internrobotics.github.io/internvla-a15.github.io/) | VLA | Real / UMI / Sim / General |
| 2026.7 | LingbotVLA 2.0 | Ant Group | [Project](https://technology.robbyant.com/lingbot-vla-v2) | VLA | Real / Ego |
| 2026.7 | LingbotVA 2.0 | Ant Group | [Project](https://technology.robbyant.com/lingbot-va-v2) | WAM | Real / UMI / Ego / Sim / General |
| 2026.7 | HumanScale | PKU | [Code](https://github.com/DAGroup-PKU/HumanNet/) | WAM | Ego |
| 2026.7 | GigaWorld-Policy-0.5 | GigaAI | [Project](https://open-gigaai.github.io/giga-world-policy/) | WAM | Real |
| 2026.7 | Xiaomi-Robotics-1 | Xiaomi | [Project](https://robotics.xiaomi.com/xiaomi-robotics-1.html) | VLA | Real / UMI / General |

</details>

---

## Contributing

This is an active repository and your contributions are always welcome!

If you would like to add a resource, please open a pull request with the paper, project page, and code links where available. I may keep some pull requests open when I am not sure whether they fit this awesome list; you can vote for them by adding :+1: to the PR.

---

If you have any question about this opinionated list, do not hesitate to open an issue or start a discussion in this repository.
