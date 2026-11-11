# Dataset release timelines

Snapshot checked on **2026-11-11**. The totals cover selected releases with a documented duration and a public distribution route, including releases available under generally offered access terms. Access and reuse terms vary by dataset. The curves use release months or, when only a current snapshot could be substantiated, the month of that snapshot. A full release is added at its documented milestone when earlier tranches cannot be reconciled reliably. "Lower bound" refers to the listed release, and "partial" means the subtotal covers only the inspected portion.

Hours describe recording or interaction time. Synchronized streams, mirror repositories, alternate encodings, subsets already covered by a parent release, and known repackagings are counted once. The totals are sums of documented releases. Cross-provider overlap cannot be fully determined from public metadata. A release with only a trajectory count needs duration metadata before it can enter the hour series.

| Month | Category | Dataset | Added hours | Basis | Evidence |
| --- | --- | --- | ---: | --- | --- |
| 2022-02 | Ego | Ego4D | 3670 | Reported | [Release date and hours](https://ego4d-data.org/) · [Access terms](https://ego4d-data.org/docs/start-here/) |
| 2023-07 | Real robot | FurnitureBench | 219.6 | Reported | [Official data table](https://clvrai.github.io/furniture-bench/docs/tutorials/dataset.html) · 5,100 successful real-robot teleoperation demos |
| 2024-03 | Ego | Ego-Exo4D v2 | 221.26 | Reported | [Full release announcement](https://discuss.ego4d-data.org/t/ego-exo4d-v2-full-ego-exo4d-release/552) · Ego stream hours only |
| 2024-03 | Real robot | DROID | 350 | Reported | [Project and data](https://droid-dataset.github.io/) · original release, excluding DROID-3D and format conversions |
| 2025-03 | Real robot | AgiBot World Colosseo | 2976.4 | Reported | [Official report](https://agibot-world.com/blog/agibot_go1.pdf) · [Release](https://agibot-world.com/) |
| 2025-07 | Ego | EgoDex | 829 | Reported | [Apple release](https://machinelearning.apple.com/research/egodex-learning-dexterous-manipulation) · [Download manifest](https://github.com/apple/ml-egodex) |
| 2026-04 | Ego | EgoVerse | 1362 | Reported | [Paper and release scope](https://arxiv.org/abs/2604.07607) · [Project](https://egoverse.ai/) |
| 2026-07 | UMI | RealOmni-Open | 13000 | Lower bound | [Official data library](https://www.genrobot.ai/data/open-dataset/) · 13,000+ hours, July catalogue snapshot |
| 2026-07 | Real robot | EgoSteer-RealWorld | 192.1 | Reported | [Dataset card](https://huggingface.co/datasets/EgoSteer/EgoSteer-RealWorld) · real-robot subset only |
| 2026-07 | Real robot | RoboMIND 2.0 | 1000 | Lower bound | [Release card](https://www.modelscope.cn/datasets/X-Humanoid/RoboMIND2.0) · 310K real-robot trajectories, 1,000+ hours, with simulation listed separately |
| 2026-08 | Real robot | PrimeBot Household | 500 | Lower bound | [Aug 6 release note](https://huggingface.co/datasets/challenge-2026/challenge_data#change-log) · real-robot split |
| 2026-08 | Ego | EgoSuite-Open100K initial release | 10000 | Reported | [Aug 26 launch](https://huggingface.co/blog/LightwheelAI/egosuite-open100k) · verified release statement for the first batch, with collection target of 100,000 h |
| 2026-08 | UMI | PrimeBot UMI first tranche | 5 | Reported | [Aug 10 release note](https://huggingface.co/datasets/challenge-2026/challenge_data#change-log) |
| 2026-09 | UMI | PrimeBot UMI and PrimeUMI tranches | 200 | Reported | [Sep 8 and Sep 23 release notes](https://huggingface.co/datasets/challenge-2026/challenge_data#change-log) · 100 h each, separate releases |
| 2026-09 | Ego | RekaDaily-10k raw | 10865 | Reported | [Full raw release](https://huggingface.co/datasets/RekaAI/RekaDaily-10k-raw) · [Sep 9 card update](https://huggingface.co/datasets/RekaAI/RekaDaily-10k-raw/commits/main/README.md) · processed clips reuse the recordings |
| 2026-10 | Ego | Open-AoE | 2000 | Approximate | [Oct 17 full release](https://huggingface.co/datasets/inclusionAI/OpenAoE-2000h) · includes nano and tiny tiers |
| 2026-10 | Real robot | SharpaDex v1.0 | 300 | Approximate | [Official release](https://sharpadex.sharpa.com.cn/) · v2.1 and v3.0 encode the same episodes |
| 2026-10 | Real robot | FineART | 1718 | Reported | [Oct 29 announcement](https://labs.scale.com/blog/fineart) · [Dataset card](https://huggingface.co/datasets/lerobot/FineART) |
| 2026-11 | UMI | FastUMI-100K LeRobot snapshot | 461.7685 | Partial | [Nov 11 metadata snapshot](https://huggingface.co/datasets/IPEC-COMMUNITY/FastUMI_100k_lerobot/tree/main) · 31 readable task metadata files, 92,823 episodes. Sum of total_frames / fps / 3600. One other directory has videos but no meta/info.json. The paper reports 600 h collected. |
| 2026-11 | UMI | Soft YUBI | 99.25 | Reported | [Project](https://lute-corp.github.io/soft-yubi-site/) · [Dataset card](https://huggingface.co/datasets/LuteCorp/soft-yubi-100h) · 92.03 h mid-training and 7.22 h SFT |
| 2026-11 | Ego | EgoForce | 739 | Reported | [Dataset card and files](https://huggingface.co/datasets/zhicao/EgoForce) · whole recording set, including 62 recordings without a usable tactile stream |
| 2026-11 | Ego | NVIDIA PhysicalAI Human-1M-100K | 100000 | Reported | [Nov 9 release announcement](https://blogs.nvidia.com/blog/robotics-simulation-advancements-corl/) · [Dataset card](https://huggingface.co/datasets/nvidia/PhysicalAI-Human-1M-100K) · [Files](https://huggingface.co/buckets/nvidia/human-1m-100k-oss/tree/release-staging) |

### Releases outside the hour totals

| Resource | Release scope | Reason |
| --- | --- | --- |
| [Open-HumanWAM-50K](https://huggingface.co/datasets/DAGroup-PKU/Open-HumanWAM-50K) | 50,000 h curated from five existing sources. Upload completion reported on Nov 11. Hugging Face access request required. | The release reuses HumanNet, EgoSuite-Open100K, EgoDex, Gen-HumanEgo and EgoVerse. [EgoStandard](https://huggingface.co/datasets/DAGroup-PKU/Open-HumanWAM-50K/tree/main/egostandard) is one source directory, with its own duration unverified. |
| [OpenNeoData](https://huggingface.co/datasets/NeoteAIEmbodied/OpenNeoData) | 5,000+ h across robot platforms and handheld UMI devices. | A category split could not be verified from public metadata. |
| [Daimon-Infinity](https://huggingface.co/datasets/daimonrobotics/Daimon-Infinity) | The card describes the first 1,000 h across DataClaw handheld and DataDex wearable capture. | The handheld share of the release could not be verified. The TacClaw-Infinity paper reports 10,000+ h collected. |
| [EgoSuite-Open100K subsequent batches](https://huggingface.co/collections/LightwheelAI/egosuite-open100k) | 100,000 h collection target. | Total availability beyond the documented initial 10,000 h needs a manifest audit. |

### Website demonstration counts

These figures extend the two curves in the [project website](https://jasper-aaa.github.io/embodied-data-pyramid/), using its [catalogue script](https://jasper-aaa.github.io/embodied-data-pyramid/script.js) on Nov 11. The script sums numeric dataset-section demo counts by catalogue year. The graph headline uses the last cumulative point. The historical points retain the website's grouping and counting conventions, including its grouping of some mixed releases. These are catalogue counts and may include overlapping datasets.

The 2026 website endpoints were 5,436,589 real-robot demos and 1,232,340 UMI demos. This update adds 40,543 [FineART](https://huggingface.co/datasets/lerobot/FineART), 28,993 [SharpaDex](https://huggingface.co/datasets/Sharpa-Robotics/SharpaDex-v1.0), and 54,454 [EgoSteer-RealWorld](https://huggingface.co/datasets/EgoSteer/EgoSteer-RealWorld) episodes to the real-robot series. The UMI series adds 51,118 [Soft YUBI](https://huggingface.co/datasets/LuteCorp/soft-yubi-100h) episodes across its two splits. These four datasets are absent from the site's demo series. The three new Ego resources belong to the human-data catalogue and do not contribute to these two demo series.

| Year | Real robot demos | UMI demos |
| --- | ---: | ---: |
| 2018 | 11259 | |
| 2021 | 811259 | |
| 2023 | 3340452 | |
| 2024 | 4449914 | 38034 |
| 2025 | 4970300 | 161739 |
| 2026 | 5560579 | 1283458 |

To regenerate the README figures, run `python scripts/plot_data_trends.py` with Matplotlib installed.
