import sqlite3
import json
c = sqlite3.connect('secrunner.db')
args = json.dumps(["-u", "-c", "print('hello from mock'); import time; time.sleep(0.5); print('done')"])
c.execute('update command_configs set allowed_args=? where id=1', (args,))
c.commit()
print("Updated!")
