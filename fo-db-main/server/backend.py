from db import init_db, init_tables, get_engine, obj_to_dict, OLT, Project, Object, Item, ItemType, Cable, User, WebServerSession, History
from sqlalchemy.orm import Session
from threading import Lock
import logging
import time
import re
import traceback


CHUNK_SIZE = 2000
ARGS_SIZE = 20000
MANAGED_TABLES = ["item", "cable", "object", "project", "olt"]  # do not change order
CABLE_NAME_RE = re.compile("^(FO[0-9]+).*$")


def cable_type(cable_name):
    m = CABLE_NAME_RE.match(cable_name)
    return None if m is None else m.group(1)


def make_chunks(src, chunk_size):
    return [src[start_index:start_index + chunk_size] for start_index in range(0, len(src), chunk_size)]


def exclude(obj, excluded_keys):
    return {k: v for k, v in obj.items() if k not in excluded_keys}


def error_boundary(f):
    def wrapper(*args, **kwargs):
        with args[0].mutex:
            try:
                return f(*args, **kwargs)
            except:
                logging.warning("error_boundary: {}".format(traceback.format_exc()))
                try:
                    args[0].session.rollback()
                    args[0].error and args[0].error()
                except:
                    logging.warning("error_boundary: can not make error call: {}".format(traceback.format_exc()))
                return False
    return wrapper


class Backend(object):
    def __init__(self, app_wd, repeat=None, error=None):
        init_db(app_wd)
        self.session = Session(get_engine())
        init_tables(self.session)
        self.db_classes = {
            "olt": OLT,
            "project": Project,
            "object": Object,
            "item": Item,
            "item_type": ItemType,
            "cable": Cable,
            "user": User,
            "session": WebServerSession,
            "history": History
        }
        self.repeat = repeat
        self.error = error
        self.mutex = Lock()

    @error_boundary
    def get_user_history(self, user_ids, start_of_day, chunk):
        result = []

        no_info = ("", None)

        info = {
            "olt": {None: no_info},
            "project": {None: no_info},
            "object": {None: no_info},
            "item": {None: no_info},
            "cable": {None: no_info}
        }

        records = self.session.query(History).filter(History.ts >= start_of_day, History.ts < start_of_day + 86400)
        if user_ids:
            records = records.filter(History.user_id.in_(user_ids))

        for record in records.all():
            data = {
                "id": record.id,
                "user_id": record.user_id,
                "ts": record.ts,
                "table": record.table,
                "row": int(record.row),
                "row_name": "",
                "column": record.column,
                "value": record.value,

                "olt": "",
                "project": "",
                "object": "",

                "action": 1
            }

            info[record.table][data["row"]] = no_info

            result.append(data)

        for table in MANAGED_TABLES:
            db_class = self.db_classes[table]
            records = self.session.query(db_class).filter(db_class.deleted_ts >= start_of_day, db_class.deleted_ts < start_of_day + 86400)
            if user_ids:
                records = records.filter(db_class.user_id.in_(user_ids))

            for record in records.all():
                data = {
                    "id": record.id,
                    "user_id": record.user_id,
                    "ts": record.deleted_ts,
                    "table": table,
                    "row": record.id,
                    "row_name": "",
                    "column": "",
                    "value": "",

                    "olt": "",
                    "project": "",
                    "object": "",

                    "action": 2
                }

                info[table][data["row"]] = no_info

                result.append(data)

        for table in MANAGED_TABLES:
            db_class = self.db_classes[table]
            id_to_info = info[table]
            for ids in make_chunks(list(id_to_info.keys()), ARGS_SIZE):
                for item in self.session.query(db_class).filter(db_class.id.in_(ids)).all():
                    parent_id = None
                    if table == "project":
                        parent_id = item.olt_id
                        info["olt"][parent_id] = no_info
                    elif table == "object":
                        parent_id = item.project_id
                        info["project"][parent_id] = no_info
                    elif table in ["item", "cable"]:
                        parent_id = item.object_id
                        info["object"][parent_id] = no_info
                    id_to_info[item.id] = (item.name, parent_id)

        for record in result:
            if record["table"] == "olt":
                name, _ = info["olt"][record["row"]]
                record["olt"] = name
            elif record["table"] == "project":
                name, parent_id = info["project"][record["row"]]
                record["project"] = name

                name, _ = info["olt"][parent_id]
                record["olt"] = name
            elif record["table"] == "object":
                name, parent_id = info["object"][record["row"]]
                record["object"] = name

                name, parent_id = info["project"][parent_id]
                record["project"] = name

                name, _ = info["olt"][parent_id]
                record["olt"] = name
            elif record["table"] in ["item", "cable"]:
                name, parent_id = info[record["table"]][record["row"]]
                record["row_name"] = name

                name, parent_id = info["object"][parent_id]
                record["object"] = name

                name, parent_id = info["project"][parent_id]
                record["project"] = name

                name, _ = info["olt"][parent_id]
                record["olt"] = name

        result = sorted(result, key=lambda item: (item["ts"], item["table"], item["id"]))
        chunk_count = int(len(result) / CHUNK_SIZE) + (1 if len(result) % CHUNK_SIZE > 0 else 0)
        if chunk_count == 0:
            chunk_count = 1
        start_index = chunk * CHUNK_SIZE
        return {
            "chunk": result[start_index:start_index + CHUNK_SIZE],
            "chunk_count": chunk_count
        }

    @error_boundary
    def get_olt_report(self, olt_id):
        columns = []

        projects = self.session.query(Project).filter(Project.olt_id == olt_id, Project.deleted_ts == 0).order_by(Project.name).all()
        for project in projects:
            column = {}
            blocks = {}
            object_ids = []
            objects = self.session.query(Object).filter(Object.project_id == project.id, Object.deleted_ts == 0).all()
            for obj in objects:
                blocks[obj.id] = obj.blocks
                object_ids.append(obj.id)
            items = self.session.query(Item).filter(Item.object_id.in_(object_ids), Item.deleted_ts == 0).all()
            for items in make_chunks(items, ARGS_SIZE):
                for item in items:
                    total = item.basement
                    for block_i in range(blocks[item.object_id]):
                        total += getattr(item, "block_{}".format(block_i + 1))
                    real_count, project_count = column.get(item.name, [0, 0])
                    column[item.name] = [real_count + total, project_count + item.project]
            cables = self.session.query(Cable).filter(Cable.object_id.in_(object_ids), Cable.deleted_ts == 0).all()
            for cables in make_chunks(cables, ARGS_SIZE):
                for cable in cables:
                    total = cable.basement
                    for block_i in range(blocks[cable.object_id]):
                        total += getattr(cable, "block_{}".format(block_i + 1))
                    t = cable_type(cable.name) or cable.name
                    real_count, project_count = column.get(t, [0, 0])
                    column[t] = [real_count + total, project_count + cable.project]
            columns.append(column)

        row_names = {}
        for column in columns:
            row_names.update(column)

        result = [[""]]
        result[0].extend([[project.name, ""] for project in projects])

        for row_name in sorted(row_names):
            row = [row_name]
            for column in columns:
                row.append(column.get(row_name, [0, 0]))
            result.append(row)

        return result

    @error_boundary
    def insert(self, table, obj, user_id=None):
        if table in MANAGED_TABLES and ("deleted_ts" in obj or "user_id" in obj):
            raise RuntimeError("unexpected fields")
        db_class = self.db_classes[table]
        item = db_class(**obj)
        self.session.add(item)
        self.session.commit()
        item = obj_to_dict(db_class, item)
        if table in MANAGED_TABLES:
            self.update_history(table, item, user_id, True)
        self.session.commit()
        return item

    @error_boundary
    def select(self, table, filter_by=None, order_by=None, asc=True):
        db_class = self.db_classes[table]
        items = self.session.query(db_class)
        if filter_by is not None:
            items = items.filter_by(**filter_by)
        if order_by is not None:
            column = getattr(db_class, order_by)
            items = items.order_by(column.asc() if asc else column.desc())
        return [obj_to_dict(db_class, item) for item in items.all()]

    def update_history(self, table, obj, user_id, skip_empty_cells=False):
        ts = int(time.time())
        row = obj["id"]
        excluded_keys = {"id", "olt_id", "project_id", "object_id", "deleted_ts", "user_id"}
        for k, v in obj.items():
            if (k in excluded_keys) or (skip_empty_cells and (v == "" or v == 0)):
                continue
            self.session.add(History(
                user_id=user_id,
                ts=ts,
                table=table,
                row=row,
                column=k,
                value=v
            ))

    @error_boundary
    def update(self, table, obj, user_id=None):
        db_class = self.db_classes[table]
        if table in MANAGED_TABLES:
            if ("deleted_ts" in obj or "user_id" in obj):
                raise RuntimeError("unexpected fields")
            self.session.query(db_class).filter_by(id=obj["id"], deleted_ts=0, user_id="").update(obj)
        else:
            self.session.query(db_class).filter_by(id=obj["id"]).update(obj)
        if table in MANAGED_TABLES:
            self.update_history(table, obj, user_id)
        self.session.commit()
        return True

    def delete_object(self, object_ids, deleted_ts, user_id):
        for object_ids in make_chunks(object_ids, ARGS_SIZE):
            self.session.query(Item).filter(Item.object_id.in_(object_ids), Item.deleted_ts == 0).update({"deleted_ts": deleted_ts, "user_id": user_id})
            self.session.query(Cable).filter(Cable.object_id.in_(object_ids), Cable.deleted_ts == 0).update({"deleted_ts": deleted_ts, "user_id": user_id})
            self.session.query(Object).filter(Object.id.in_(object_ids), Object.deleted_ts == 0).update({"deleted_ts": deleted_ts, "user_id": user_id})

    def delete_project(self, project_ids, deleted_ts, user_id):
        for project_ids in make_chunks(project_ids, ARGS_SIZE):
            object_ids = [obj.id for obj in self.session.query(Object).filter(Object.project_id.in_(project_ids), Object.deleted_ts == 0).all()]
            self.delete_object(object_ids, deleted_ts, user_id)
            self.session.query(Project).filter(Project.id.in_(project_ids), Project.deleted_ts == 0).update({"deleted_ts": deleted_ts, "user_id": user_id})

    def delete_olt(self, olt_id, deleted_ts, user_id):
        project_ids = [project.id for project in self.session.query(Project).filter(Project.olt_id == olt_id, Project.deleted_ts == 0).all()]
        self.delete_project(project_ids, deleted_ts, user_id)
        self.session.query(OLT).filter(OLT.id == olt_id, OLT.deleted_ts == 0).update({"deleted_ts": deleted_ts, "user_id": user_id})

    @error_boundary
    def delete(self, table, id, user_id=None):
        db_class = self.db_classes[table]
        deleted_ts = int(time.time())
        if table in MANAGED_TABLES:
            if table == "olt":
                self.delete_olt(id, deleted_ts, user_id)
            elif table == "project":
                self.delete_project([id], deleted_ts, user_id)
            elif table == "object":
                self.delete_object([id], deleted_ts, user_id)
            else:
                self.session.query(db_class).filter(db_class.id == id, db_class.deleted_ts == 0).update({"deleted_ts": deleted_ts, "user_id": user_id})
            self.session.commit()
        else:
            self.session.query(db_class).filter_by(id=id).delete()
            self.session.commit()
        return True

    def objects_to_db(self, user_id, project_id, objects):
        db_objects = []
        db_items = []
        db_cables = []

        for obj in objects:
            items = obj.pop("items")
            cables = obj.pop("cables")
            obj = Object(**dict(obj, project_id=project_id))
            db_objects.append((obj, items, cables))
            self.session.add(obj)

        self.session.commit()

        for obj, items, cables in db_objects:
            obj = obj_to_dict(Object, obj)
            self.update_history("object", obj, user_id, True)

            object_id = obj["id"]

            for name, project in items.items():
                item = Item(name=name, project=project, object_id=object_id)
                db_items.append(item)
                self.session.add(item)

            for name, project in cables.items():
                cable = Cable(name=name, project=project, object_id=object_id)
                db_cables.append(cable)
                self.session.add(cable)

        self.session.commit()

        for item in db_items:
            item = obj_to_dict(Item, item)
            self.update_history("item", item, user_id, True)

        for cable in db_cables:
            cable = obj_to_dict(Cable, cable)
            self.update_history("cable", cable, user_id, True)

        self.session.commit()

    @error_boundary
    def load_project(self, obj, user_id=None):
        objects = obj.pop("objects")
        if "deleted_ts" in obj or "user_id" in obj:
            raise RuntimeError("unexpected fields")
        project = Project(**obj)
        self.session.add(project)
        self.session.commit()
        project = obj_to_dict(Project, project)
        self.update_history("project", project, user_id, True)
        self.session.commit()
        self.objects_to_db(user_id, project["id"], objects)
        return project
