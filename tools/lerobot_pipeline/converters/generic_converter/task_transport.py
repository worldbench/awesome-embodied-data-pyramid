from pathlib import Path
import pickle, tempfile, os
_TASK_CACHE = {}
def write_tasks(tasks):
    root=Path(os.environ.get('LEROBOT_TASK_CACHE', str(Path(tempfile.gettempdir()) / 'lerobot-task-cache')));root.mkdir(parents=True,exist_ok=True)
    fd,path=tempfile.mkstemp(prefix='tasks-',suffix='.pkl',dir=root)
    with os.fdopen(fd,'wb') as f:pickle.dump(tasks,f,protocol=pickle.HIGHEST_PROTOCOL)
    return path
def load_tasks(path):
    if path not in _TASK_CACHE:
        with open(path,'rb') as f:_TASK_CACHE[path]=pickle.load(f)
    return _TASK_CACHE[path]
