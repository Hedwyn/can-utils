from candump import loop, recv
from can.message import Message
from threading import Thread
from multiprocessing import Process
import time
import yappi

receiver = Thread(target = loop)
# yappi.start()
receiver.start()
ctr = 0
while True:
    frame = recv()
    buffer = []
    if frame:
        can_id, lgth, data, ts = frame
        
        msg = Message()
        msg.arbitration_id = can_id
        msg.dlc = lgth
        msg.data = data
        msg.timestamp = ts
        ctr += 1
        print(f"len: {lgth}, id: {hex(can_id)}, data: {data}, ts: {ts}")
        # print(msg)
        buffer.append(msg)

    if ctr > 173693:
        with open('candump.dump', 'wb') as f:
            for msg in buffer:
                f.write(str(msg))
        # yappi.stop()
        # yappi.get_func_stats()._save_as_PSTAT('test.dump')
        break