import pickle


class package():
    def __init__(self, info_type, info, seq_num):
        self.type = info_type
        self.info = info
        self.seq_num = seq_num

    def dump_pack(self):
        rez = pickle.dumps(self)
        return rez

    def load_pack(self, info):
        rez = pickle.loads(info)
        self.type = rez.type
        self.info = rez.info
        self.seq_num = rez.seq_num


class frame():
    def __init__(self, info, is_ack, seq_num):
        self.info = info
        self.is_ack = is_ack
        self.seq_num = seq_num
