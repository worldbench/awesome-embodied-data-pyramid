# FK model assets

The public source archive excludes `quality/robot_models/`. The local working copy may contain those ignored files for validation. Model copyrights are independent of the code license.

```bash
python scripts/import_robot_models.py --source /path/to/authorized/robot_models
```

The importer checks every expected relative file, byte size and SHA256 before copying. It refuses to overwrite different destination bytes. The original layout is required. Do not replace a URDF with an arbitrary model sharing the robot name: link frames, joint mappings and calibration matter.

Without these assets, use planning and non-FK tests only. Do not report an asset-free run as a reproduction of the four-rule/FK release. Run `python scripts/import_robot_models.py --check` before full tests or cleaning. Model files remain ignored by Git.
