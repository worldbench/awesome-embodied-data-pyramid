import tempfile, unittest
from pathlib import Path
from unittest.mock import Mock, patch
import pandas as pd
import pyarrow.parquet as pq
from generic_converter.parquet_shards import StreamingDataShards

class StreamingDataShardsTest(unittest.TestCase):
    def test_append_and_episode_fragments(self):
        with tempfile.TemporaryDirectory() as d:
            writer=StreamingDataShards(Mock());idx={'chunk':0,'file':0}
            with patch('lerobot.datasets.aggregate.get_parquet_file_size_in_mb',return_value=1):
                for ids in [[0,0],[0,1],[2,2]]:
                    writer(pd.DataFrame({'episode_index':ids,'value':[1.,2.]}),Path('src'),idx,10,2,
                           'data/chunk-{chunk_index:03d}/file-{file_index:03d}.parquet',
                           aggr_root=Path(d),one_row_group_per_episode=True)
            writer.close();p=next(Path(d).rglob('*.parquet'));f=pq.ParquetFile(p)
            self.assertEqual(f.metadata.num_row_groups,3)
            self.assertEqual([f.metadata.row_group(i).num_rows for i in range(3)],[3,1,2])
            self.assertEqual(f.read()['episode_index'].to_pylist(),[0,0,0,1,2,2])

    def test_rotation_and_footer(self):
        with tempfile.TemporaryDirectory() as d:
            writer=StreamingDataShards(Mock());idx={'chunk':0,'file':0};mapping=[]
            with patch('lerobot.datasets.aggregate.get_parquet_file_size_in_mb',return_value=1):
                for i in range(3):
                    _,pair=writer(pd.DataFrame({'episode_index':[i]}),Path('src'),idx,2,2,
                                 'data/chunk-{chunk_index:03d}/file-{file_index:03d}.parquet',
                                 aggr_root=Path(d),one_row_group_per_episode=True)
                    mapping.append(pair)
            writer.close()
            self.assertEqual(mapping,[(0,0),(0,1),(1,0)])
            self.assertEqual(sum(pq.read_table(p).num_rows for p in Path(d).rglob('*.parquet')),3)

    def test_embedded_images_use_native_writer(self):
        fallback=Mock(return_value='native');writer=StreamingDataShards(fallback)
        self.assertEqual(writer(None,None,{},1,1,'x',contains_images=True),'native')
        fallback.assert_called_once()
