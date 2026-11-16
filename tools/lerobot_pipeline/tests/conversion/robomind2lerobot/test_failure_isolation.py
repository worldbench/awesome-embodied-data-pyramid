import json
from pathlib import Path
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "converters" / "robomind2lerobot"))
from robomind_fast import (identity, pending_archive_rows, record_archive_failure,
                           require_all_archives, write_json)
import robomind_fast


class FailureIsolationTests(unittest.TestCase):
    def test_scheduler_finishes_other_archive_but_never_aggregates_partial_run(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);source=base/'source';source.mkdir()
            part=source/'part';part.write_bytes(b'broken')
            rows=[{'task':task,'embodiment':'franka_3rgb','bytes':6,
                   'parts':[{'path':str(part),'size':6}]} for task in ['bad','good']]
            plan={'root':str(source),'archives':rows,'unsupported':[],'missing_instructions':[]}
            calls=[]
            def fake_worker(row, settings):
                calls.append(row['task'])
                if row['task']=='bad':raise EOFError('unexpected end of data')
                return {'archive':row,'saved':1,'frames':2,'seconds':0,'shards':[]}
            work=base/'work'
            argv=['robomind_fast.py','--mode','full','--source',str(source),
                  '--output-base',str(base/'output'),'--work',str(work),'--scratch',str(base/'scratch'),'--workers','1']
            with patch.object(sys,'argv',argv), patch.object(robomind_fast,'inventory',return_value=plan), \
                 patch.object(robomind_fast,'worker',side_effect=fake_worker), \
                 patch.object(robomind_fast,'ProcessPoolExecutor',side_effect=lambda **kw:ThreadPoolExecutor(max_workers=kw['max_workers'])), \
                 patch.object(robomind_fast,'aggregate') as aggregate:
                with self.assertRaisesRegex(RuntimeError,'Final aggregation is blocked'):robomind_fast.main()
                self.assertEqual(calls,['bad','good'])
                calls.clear()
                with self.assertRaisesRegex(RuntimeError,'Final aggregation is blocked'):robomind_fast.main()
                self.assertEqual(calls,['good'])
                aggregate.assert_not_called()
            progress=json.loads((work/'progress.json').read_text())
            self.assertEqual(progress['stage'],'blocked_source_repair')
            self.assertEqual(progress['completed_archives'],1)
            self.assertEqual(progress['total_archives'],2)
            self.assertFalse((work/'COMPLETED.json').exists())

    def test_failed_source_is_explicitly_deferred_and_other_rows_continue(self):
        with tempfile.TemporaryDirectory() as d:
            work=Path(d)
            part=work/'bad.gz';part.write_bytes(b'broken')
            bad={'task':'bad','parts':[{'path':str(part),'size':6}]}
            good={'task':'good','parts':[{'path':str(part),'size':6}]}
            record_archive_failure(work,bad,'unexpected end of data')
            pending,failed=pending_archive_rows(work,[bad,good])
            self.assertEqual(pending,[good])
            self.assertEqual(set(failed),{identity(bad)})
            self.assertTrue(part.exists())
            with self.assertRaisesRegex(RuntimeError,'Final aggregation is blocked'):
                require_all_archives([{'archive':good}],[bad,good],failed)
            part.write_bytes(b'restored source')
            pending,failed=pending_archive_rows(work,[bad,good])
            self.assertEqual(pending,[bad,good])
            self.assertFalse(failed)

    def test_completed_marker_takes_precedence_and_completion_requires_all(self):
        with tempfile.TemporaryDirectory() as d:
            work=Path(d);p=work/'data.gz';p.write_bytes(b'abc')
            row={'task':'task','parts':[{'path':str(p),'size':3}]}
            record_archive_failure(work,row,'previous failure')
            write_json(work/'archives'/identity(row)/'COMPLETED.json',{})
            pending,failed=pending_archive_rows(work,[row])
            self.assertEqual(pending,[row]);self.assertFalse(failed)
            require_all_archives([{'archive':row}],[row],{})
            with self.assertRaises(RuntimeError):require_all_archives([],[row],{})


if __name__=='__main__':unittest.main()
