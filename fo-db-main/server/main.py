from startup import app_wd
import os
from threading import Thread, Lock
from flask import Flask, request
from waitress import serve
import socket
from https_utils import wrap_socket
import logging
from backend import Backend, exclude
import uuid
import time
import hashlib
import json


try:
    with open(os.path.join(app_wd, "settings.json"), "rb") as f:
        settings = json.loads(f.read().decode("UTF-8"))
except:
    settings = {}
settings.setdefault("ip", "0.0.0.0")
settings.setdefault("port", 8080)
settings.setdefault("crt", os.path.join(app_wd, "127.0.0.1.crt"))
settings.setdefault("key", os.path.join(app_wd, "127.0.0.1.key"))
settings.setdefault("hostname", "127.0.0.1")
settings.setdefault("sid_exp_s", 30 * 60)
settings.setdefault("sid_refresh_s", 25 * 60)

logger = logging.getLogger("waitress")
logger.setLevel(logging.ERROR)

app = Flask(
    __name__,
    static_folder=None,
    template_folder=None
)

backend = Backend(app_wd)

sessions_mutex = Lock()
sessions = {}
salt = b"fb4a072d499b4fcbae4bebb0ea1e367c70d25d720ca746cca69fcbaf205b9e38269f2d5e9e694d858e2d54a746ae9939c1a5feb6b8a74deea0b0e12f0c6f82e9"


class Session(object):
    __slots__ = ["created_ts", "user_id", "admin", "editor", "advanced_editor"]

    def __init__(self, created_ts, user_id, admin, editor, advanced_editor):
        self.created_ts = created_ts
        self.user_id = user_id
        self.admin = admin
        self.editor = editor
        self.advanced_editor = advanced_editor


def init_sessions():
    users = {user["id"]: user for user in backend.select("user")}
    for session in backend.select("session"):
        user_id = session["user_id"]
        user = users.get(user_id)
        if user is not None:
            sessions[session["id"]] = Session(
                session["created_ts"], user_id,
                user["admin"], user["editor"], user["advanced_editor"]
            )


def monitor_loop():
    while True:
        with sessions_mutex:
            now = time.time()
            sessions_to_delete = []
            for sid, session in sessions.items():
                if now - session.created_ts > settings["sid_exp_s"]:
                    sessions_to_delete.append((sid, session))
            for sid, session in sessions_to_delete:
                logging.info("delete expired session {} for user {}".format(sid, session.user_id))
                sessions.pop(sid)
                backend.delete("session", sid)
        time.sleep(60)


def check_rights(sid, table=None, op=None):
    with sessions_mutex:
        session = sessions.get(sid)
    if session is None:
        return None
    now = int(time.time())
    if now - session.created_ts > settings["sid_refresh_s"]:
        if backend.update("session", {"id": sid, "created_ts": now}):
            session.created_ts = now
    if table is None:
        return session
    tables = table if isinstance(table, list) else [table]
    for table in tables:
        if table not in ["olt", "project", "object", "item", "item_type", "cable", "user", "history"]:
            return None
        if table == "item_type" and op not in ["insert", "select"]:
            return None
        if table in ["olt", "project", "object", "item", "cable"] and op != "select" and not session.editor and not session.advanced_editor:
            return None
        if table in ["item_type"] and op != "select" and not session.admin:
            return None
        if table in ["user", "history"] and not session.admin:
            return None
        if table == "history" and op != "select":
            return None
    return session


def add_session(user_id, admin, editor, advanced_editor):
    with sessions_mutex:
        while True:
            sid = uuid.uuid4().hex
            if sid not in sessions:
                break
        created_ts = int(time.time())
        if backend.insert("session", {"id": sid, "created_ts": created_ts, "user_id": user_id}):
            sessions[sid] = Session(created_ts, user_id, admin, editor, advanced_editor)
        else:
            sid = None
    return sid


def delete_sessions(user_id, new_sid):
    with sessions_mutex:
        sessions_to_delete = []
        for sid, session in sessions.items():
            if session.user_id == user_id and sid != new_sid:
                sessions_to_delete.append((sid, session))
        for sid, session in sessions_to_delete:
            logging.info("delete session {} for user {}".format(sid, session.user_id))
            sessions.pop(sid)
            backend.delete("session", sid)


@app.route("/enter", methods=["POST"])
def enter():
    result = {"sid": None}
    name = request.json["name"]
    users = backend.select("user", {"id": name})
    if users is False:
        raise RuntimeError("backend error")
    if users:
        user = users[0]
        user_password = user["password"]
        admin = user["admin"]
        editor = user["editor"]
        advanced_editor = user["advanced_editor"]
        password = request.json["password"]
        if password:
            password = hashlib.md5(password.encode("UTF-8") + salt).hexdigest()
        if (not user_password and not password) or user_password == password:
            sid = add_session(name, admin, editor, advanced_editor)
            if sid is not None:
                result["sid"] = sid
                result["admin"] = admin
                result["editor"] = editor
                result["advanced_editor"] = advanced_editor
    return result


@app.route("/set_password", methods=["POST"])
def set_password():
    global sessions

    sid = request.json["sid"]
    with sessions_mutex:
        session = sessions.get(sid)
    if session is None:
        return {"result": False}

    name = request.json.get("name", session.user_id)
    new_sid = None
    if name == session.user_id:
        new_sid = add_session(name, session.admin, session.editor, session.advanced_editor)
        if new_sid is None:
            return {"result": False}

    password = request.json["password"]
    if password:
        password = hashlib.md5(password.encode("UTF-8") + salt).hexdigest()
    if not backend.update("user", {"id": name, "password": password}):
        delete_sessions(name, None)
        return {"result": False}

    delete_sessions(name, new_sid)

    return {"result": True, "new_sid": new_sid}


@app.route("/keepalive", methods=["POST"])
def keepalive():
    if not check_rights(request.json["sid"]):
        return {"result": False}
    return {"result": True}


@app.route("/get_user_history", methods=["POST"])
def get_user_history():
    if not check_rights(request.json["sid"], "history", "select"):
        return {"result": False}
    return {"result": backend.get_user_history(request.json["user_ids"], request.json["start_of_day"], request.json["chunk"])}


@app.route("/get_olt_report", methods=["POST"])
def get_olt_report():
    if not check_rights(request.json["sid"], "olt", "select"):
        return {"result": False}
    return {"result": backend.get_olt_report(request.json["olt_id"])}


@app.route("/<table>/insert", methods=["POST"])
def insert(table):
    session = check_rights(request.json["sid"], table, "insert")
    if not session:
        return {"result": False}
    if table in ["olt", "project", "object", "item", "cable"] and not session.advanced_editor:
        return {"result": False}
    result = backend.insert(table, request.json["args"], session.user_id)
    if not result:
        return {"result": False}
    if table == "user":
        result = exclude(result, ["password"])
    return {"result": result}


@app.route("/<table>/select", methods=["POST"])
def select(table):
    if not check_rights(request.json["sid"], table, "select"):
        return {"result": False}
    result = backend.select(table, request.json["args"]["filter_by"], request.json["args"]["order_by"], request.json["args"]["asc"])
    if result is False:
        return {"result": False}
    if table == "user":
        result = [exclude(user, ["password"]) for user in result]
    return {"result": result}


@app.route("/<table>/update", methods=["POST"])
def update(table):
    session = check_rights(request.json["sid"], table, "update")
    if not session:
        return {"result": False}
    if not session.advanced_editor:
        props = set([
            "block_" if prop.startswith("block_") else prop
            for prop in request.json["args"].keys()
        ])
        if table == "project" and len(props - set(["id", "comment"])) > 0:
            return {"result": False}
        if table in ["item", "cable"] and len(props - set(["id", "comment", "basement", "block_"])) > 0:
            return {"result": False}
    return {"result": backend.update(table, request.json["args"], session.user_id)}


@app.route("/<table>/delete", methods=["POST"])
def delete(table):
    session = check_rights(request.json["sid"], table, "delete")
    if not session:
        return {"result": False}
    if table in ["olt", "project", "object", "item", "cable"] and not session.advanced_editor:
        return {"result": False}
    id = request.json["args"]
    if table == "user":
        delete_sessions(id, None)
    return {"result": backend.delete(table, id, session.user_id)}


@app.route("/load_project", methods=["POST"])
def load_project():
    session = check_rights(request.json["sid"], ["project", "object", "item", "cable"], "insert")
    if not session:
        return {"result": False}
    if not session.advanced_editor:
        return {"result": False}
    result = backend.load_project(request.json["args"], session.user_id)
    if not result:
        return {"result": False}
    return {"result": result}


if __name__ == "__main__":
    init_sessions()
    sessions_thread = Thread(target=monitor_loop)
    sessions_thread.start()

    web_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    web_server_socket.bind((settings["ip"], settings["port"]))
    web_server_socket = wrap_socket(
        web_server_socket,
        settings["crt"],
        settings["key"],
        settings["hostname"]
    )

    flask_thread = Thread(target=serve, args=(app,), kwargs={"sockets": [web_server_socket], "url_scheme": "https"})
    flask_thread.start()

    flask_thread.join()
