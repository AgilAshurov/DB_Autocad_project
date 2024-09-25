import requests
import hashlib
from threading import Thread
import time
import logging


salt = b"17785218f7464a56a9540deda71f49838776bc39c56140f1af0d84cc407229d5d394ee511ee747b7a25fb2066ecede95005be86ce1d140729c89b7076cfd824e"


def error_boundary(f):
    def wrapper(*args, **kwargs):
        while True:
            try:
                res = f(*args, **kwargs)
                if res is False:
                    try:
                        args[0].error and args[0].error()
                    except Exception as e:
                        logging.warning("error_boundary: can not make error call: {}".format(e))
                return res
            except Exception as e:
                logging.warning("error_boundary: {}".format(e))
                if args[0].repeat and args[0].repeat():
                    continue
                return False
    return wrapper


class Backend(object):
    def __init__(self, url, timeout, repeat=None, error=None):
        self.url = url
        self.timeout = timeout
        self.repeat = repeat
        self.error = error
        self.session = requests.session()
        self.name = None
        self.user = None
        self.keepalive_thread = Thread(target=self.keepalive_loop)
        self.keepalive_thread.start()

    def send(self, path, data):
        return self.session.post("{}/{}".format(self.url, path), json=data, timeout=self.timeout, verify=False).json()

    def send_table(self, table, op, data):
        return self.send("{}/{}".format(table, op), data)

    def keepalive_loop(self):
        while True:
            if self.user is not None and self.user["sid"] is not None:
                data = {"sid": self.user["sid"]}
                try:
                    self.send("keepalive", data)
                except Exception as e:
                    logging.warning("Backend: keepalive_loop: {}".format(e))
            time.sleep(60)

    def enter(self, name, password):
        if password:
            password = hashlib.md5(password.encode("UTF-8") + salt).hexdigest()
        data = {"name": name, "password": password}
        try:
            self.name = name
            self.user = self.send("enter", data)
            return self.user["sid"] is not None
        except Exception as e:
            logging.warning("Backend: enter: {}".format(e))
        return None

    def set_password(self, name, password):
        if password:
            password = hashlib.md5(password.encode("UTF-8") + salt).hexdigest()
        data = {"sid": self.user["sid"], "name": name, "password": password}
        try:
            response = self.send("set_password", data)
            if not response["result"]:
                return False
            if name == self.name:
                self.user["sid"] = response["new_sid"]
            return True
        except Exception as e:
            logging.warning("Backend: set_password: {}".format(e))
        return False

    @error_boundary
    def get_user_history(self, user_ids, start_of_day, chunk):
        data = {"sid": self.user["sid"], "user_ids": user_ids, "start_of_day": start_of_day, "chunk": chunk}
        response = self.send("get_user_history", data)
        return response["result"]

    @error_boundary
    def get_olt_report(self, olt_id):
        data = {"sid": self.user["sid"], "olt_id": olt_id}
        response = self.send("get_olt_report", data)
        return response["result"]

    @error_boundary
    def insert(self, table, obj):
        data = {"sid": self.user["sid"], "args": obj}
        response = self.send_table(table, "insert", data)
        return response["result"]

    @error_boundary
    def select(self, table, filter_by=None, order_by=None, asc=True):
        data = {"sid": self.user["sid"], "args": {"filter_by": filter_by, "order_by": order_by, "asc": asc}}
        response = self.send_table(table, "select", data)
        return response["result"]

    @error_boundary
    def update(self, table, obj):
        data = {"sid": self.user["sid"], "args": obj}
        response = self.send_table(table, "update", data)
        return response["result"]

    @error_boundary
    def delete(self, table, id):
        data = {"sid": self.user["sid"], "args": id}
        response = self.send_table(table, "delete", data)
        return response["result"]

    @error_boundary
    def load_project(self, obj):
        data = {"sid": self.user["sid"], "args": obj}
        response = self.send("load_project", data)
        return response["result"]
