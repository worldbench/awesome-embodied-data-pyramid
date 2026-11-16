import unittest,json
from pathlib import Path
import numpy as np,pandas as pd
from interndata_a1_2lerobot.convert import schema,transform

FIXTURES=json.loads((Path(__file__).resolve().parents[3]/'converters/interndata_a1_2lerobot/schema_fixtures.json').read_text())

class MappingTest(unittest.TestCase):
    def test_all_sim_robot_schemas_and_quaternions(self):
        for robot,dim,arms in [('franka',8,1),('lift2',14,2),('split_aloha',14,2),('genie1',16,2)]:
            info=FIXTURES[robot]
            spec,features,_,actual_arms=schema(info);self.assertEqual(actual_arms,arms)
            self.assertEqual(features['state.qpos']['shape'],[dim]);self.assertNotIn('state.waist',features)
            data={}
            for k,v in info['features'].items():
                if v['dtype']=='video':continue
                a=np.ones((2,v['shape'][0]),np.float32)
                if 'ee_to_robot_pose' in k:a[:]=[1,2,3,2,0,0,0]
                data[k]=list(a)
            result=transform(pd.DataFrame(data),spec,features,arms)
            np.testing.assert_array_equal(result['state.ee'].reshape(2,arms,7)[0,0],[1,2,3,0,0,0,1])
            self.assertEqual(result['action.qpos'].shape,(2,dim))
    def test_missing_pose_and_real_waist(self):
        info=FIXTURES['A2D']
        spec,features,_,arms=schema(info)
        data={k:list(np.ones((2,v['shape'][0]),np.float32)) for k,v in info['features'].items() if v['dtype']!='video'}
        r=transform(pd.DataFrame(data),spec,features,arms)
        self.assertEqual(r['state.qpos'].shape,(2,16));np.testing.assert_array_equal(r['state.ee_valid'],0)
        self.assertEqual(r['state.waist'].shape,(2,2))
    def test_physical_arx_split_columns_and_invalid_action_arm(self):
        info={'features':{k:{'shape':[14],'dtype':'float32','names':None} for k in ['observation.state','action']}}
        spec,features,_,arms=schema(info)
        data={}
        for prefix in ['states','actions']:
            for side,offset in [('left',0),('right',7)]:
                data[f'{prefix}.{side}_joint.position']=[np.arange(offset,offset+6,dtype=np.float32)]
                data[f'{prefix}.{side}_gripper.position']=[np.array([offset+6],dtype=np.float32)]
        data['actions.right_joint.position'][0][0]=np.nan
        r=transform(pd.DataFrame(data),spec,features,arms)
        np.testing.assert_array_equal(r['state.qpos'],[np.arange(14)])
        np.testing.assert_array_equal(r['action.qpos'],[[0,1,2,3,4,5,6,0,0,0,0,0,0,0]])
        np.testing.assert_array_equal(r['action.qpos_valid'],[[1,0]])
        np.testing.assert_array_equal(r['action.ee_valid'],[[0,0]])
if __name__=='__main__':unittest.main()
