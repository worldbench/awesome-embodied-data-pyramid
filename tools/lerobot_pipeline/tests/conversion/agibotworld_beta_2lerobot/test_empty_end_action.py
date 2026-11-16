"""The historical repair must never mask real actions or NaNs."""
import tempfile
import unittest
from pathlib import Path
import h5py
import numpy as np
from agibotworld_beta_2lerobot.beta_utils import _is_malformed_empty_end_action,load_unified_episode

class EmptyEndActionTests(unittest.TestCase):
    def test_only_confirmed_placeholder_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'episode.h5'
            with h5py.File(p,'w') as h:
                h['timestamp']=np.arange(2)
                for group in ['state','action']:
                    h[f'{group}/joint/position']=np.zeros((2,14))
                    h[f'{group}/effector/position']=np.zeros((2,2))
                    h[f'{group}/waist/position']=np.arange(4).reshape(2,2)
                h['state/end/position']=np.zeros((2,2,3))
                h['state/end/orientation']=np.tile([0,0,0,1],(2,2,1))
                h['action/end/position']=np.zeros((5,3))
                h['action/end/orientation']=np.zeros((5,4))
                h['action/end/index']=np.array([],dtype=np.int64)
                self.assertTrue(_is_malformed_empty_end_action(h,2))
            arrays=load_unified_episode(p,'gripper')
            np.testing.assert_array_equal(arrays['action.ee_valid'],0)
            np.testing.assert_array_equal(arrays['action.waist'],np.arange(4).reshape(2,2))
            for value in [1.0,float('nan')]:
                with h5py.File(p,'r+') as h:
                    h['action/end/position'][0,0]=value
                    self.assertFalse(_is_malformed_empty_end_action(h,2))
                with self.assertRaises(ValueError):load_unified_episode(p,'gripper')

if __name__=='__main__':unittest.main()
