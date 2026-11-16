import io
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "converters" / "robomind2lerobot"))
from archive_input import PartsReader, inventory
from robomind_fast import feed_lossless, source_split, select_rgb_keys, scratch_budget


class ArchiveInputTests(unittest.TestCase):
    def test_documented_two_camera_episode_preserves_real_cameras(self):
        member='task/success_episodes/train/episode/data/trajectory.hdf5'
        manifest={f'h5_franka_3rgb/{member}'}
        expected=['camera_left','camera_right','camera_top']
        self.assertEqual(select_rgb_keys(expected,expected,'franka_3rgb',member,manifest),expected)
        self.assertEqual(select_rgb_keys(expected,expected[:2],'franka_3rgb',member,manifest),expected[:2])
        for available, emb, docs in [(expected[:2],'franka_3rgb',set()),
                                     (['camera_left'],'franka_3rgb',manifest),
                                     (expected[:2],'franka_1rgb',manifest)]:
            with self.assertRaisesRegex(ValueError,'Undocumented missing RGB'):
                select_rgb_keys(expected,available,emb,member,docs)

    def test_scratch_budget_scales_without_overcommit(self):
        self.assertEqual(scratch_budget(28*2**30,4,4),4)
        self.assertEqual(scratch_budget(28*2**30,8,4),3.25)
        self.assertEqual(scratch_budget(28*2**30,16,4),1.625)
        with self.assertRaisesRegex(ValueError,'Insufficient scratch'):
            scratch_budget(2*2**30,8,4)

    def test_split_layout_preserves_unspecified(self):
        for directory, expected in [('train/', 'train'), ('val/', 'validation'),
                                    ('validation/', 'validation'), ('', 'unspecified')]:
            self.assertEqual(source_split(f'task/success_episodes/{directory}1016_134948/data/trajectory.hdf5'), expected)
        with self.assertRaisesRegex(ValueError, 'Unrecognized source split'):
            source_split('task/success_episodes/test/episode/data/trajectory.hdf5')
        self.assertEqual(source_split('train/success_episodes/episode/data/trajectory.hdf5'), 'unspecified')

    def test_split_gzip_stream_crosses_part_boundaries(self):
        raw = io.BytesIO()
        with tarfile.open(fileobj=raw, mode='w:gz') as tf:
            entry = tarfile.TarInfo('task/success_episodes/train/e/data/trajectory.hdf5')
            payload = bytes(range(256)) * 9
            entry.size = len(payload)
            tf.addfile(entry, io.BytesIO(payload))
        compressed = raw.getvalue()
        with tempfile.TemporaryDirectory() as d:
            paths=[]
            for i,start in enumerate(range(0,len(compressed),17)):
                path=Path(d)/str(i);path.write_bytes(compressed[start:start+17]);paths.append(path)
            reader=PartsReader(paths)
            with io.BufferedReader(reader,buffer_size=23) as f:
                with tarfile.open(fileobj=f,mode='r|gz') as tf:
                    member=next(iter(tf))
                    self.assertEqual(tf.extractfile(member).read(),payload)

    def test_partial_downloads_are_not_counted_as_archive_parts(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'static').mkdir()
            (root/'static/RoboMIND_v1_2_instr.csv').write_text(',task,instruction\n0,task,pick item\n')
            folder=root/'benchmark1_0_compressed/h5_franka_3rgb';folder.mkdir(parents=True)
            (folder/'task.tar.gz.part-aa').write_bytes(b'abc')
            (folder/'task.tar.gz.part-aa.incomplete').write_bytes(b'bad')
            result=inventory(root)
            self.assertEqual(result['bytes'],3)
            (folder/'task.tar.gz.part-ac').write_bytes(b'gap')
            with self.assertRaisesRegex(ValueError,'Missing archive part'):inventory(root)

    def test_backpressure_retries_instead_of_dropping(self):
        import queue
        from types import SimpleNamespace
        class Frames:
            calls=0
            def put(self, frame, timeout):
                self.calls+=1
                if self.calls<3:raise queue.Full
        q=Frames()
        encoder=SimpleNamespace(_episode_active=True,_threads={'cam':SimpleNamespace(is_alive=lambda:True)},
                                _frame_queues={'cam':q})
        feed_lossless(encoder,'cam',SimpleNamespace(copy=lambda:'frame'))
        self.assertEqual(q.calls,3)
        encoder._threads['cam'].is_alive=lambda:False
        with self.assertRaisesRegex(RuntimeError,'Encoder failed'):
            feed_lossless(encoder,'cam',SimpleNamespace(copy=lambda:'frame'))



class ReleaseScopeTests(unittest.TestCase):
    def test_only_released_embodiments_are_supported(self):
        from archive_input import SUPPORTED
        self.assertEqual(SUPPORTED, {
            'franka_1rgb', 'franka_3rgb', 'franka_fr3_dual', 'ur_1rgb',
            'tienkung_gello_1rgb', 'tienkung_prod1_gello_1rgb', 'tienkung_xsens_1rgb',
        })

    def test_unknown_embodiment_is_not_scheduled(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'static').mkdir()
            (root/'static/RoboMIND_v1_2_instr.csv').write_text('task,instruction\ntask,pick item\n')
            folder=root/'benchmark1_0_compressed/h5_unknown_robot';folder.mkdir(parents=True)
            (folder/'task.tar.gz').write_bytes(b'fixture')
            report=inventory(root)
            self.assertEqual(report['archives'],[])
            self.assertEqual(len(report['unsupported']),1)


if __name__=='__main__':
    unittest.main()
