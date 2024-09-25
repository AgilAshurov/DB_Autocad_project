import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, Session
from sqlalchemy import Column, Integer, String, Index, Float
from sqlalchemy.schema import ForeignKey
import time


Base = declarative_base()


class OLT(Base):
    __tablename__ = "olt"

    id = Column(Integer, primary_key=True)
    name = Column(String(30), nullable=False)
    gpon = Column(Integer, server_default="0")
    odf = Column(Integer, server_default="0")
    olt = Column(Integer, server_default="0")
    connector = Column(Integer, server_default="0")
    pt = Column(Integer, server_default="0")
    ups = Column(Integer, server_default="0")
    deleted_ts = Column(Integer, server_default="0")
    user_id = Column(String, server_default="")

    __table_args__ = {"sqlite_autoincrement": True}


class Project(Base):
    __tablename__ = "project"

    id = Column(Integer, primary_key=True)
    name = Column(String(30), nullable=False)
    olt_id = Column(Integer, ForeignKey("olt.id"))
    deleted_ts = Column(Integer, server_default="0")
    user_id = Column(String, server_default="")
    comment = Column(String, server_default="")

    __table_args__ = {"sqlite_autoincrement": True}


class Object(Base):
    __tablename__ = "object"

    id = Column(Integer, primary_key=True)
    addr = Column(String(50), server_default="")
    name = Column(String(30), nullable=False)
    blocks = Column(Integer, server_default="0")
    levels = Column(Integer, server_default="0")
    apartments = Column(Integer, server_default="0")
    branch = Column(String, server_default="")
    comment = Column(String, server_default="")
    project_id = Column(Integer, ForeignKey("project.id"))
    deleted_ts = Column(Integer, server_default="0")
    user_id = Column(String, server_default="")
    extra_codes = Column(String, server_default="")

    __table_args__ = {"sqlite_autoincrement": True}


class Item(Base):
    __tablename__ = "item"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    block_1 = Column(Integer, server_default="0")
    block_2 = Column(Integer, server_default="0")
    block_3 = Column(Integer, server_default="0")
    block_4 = Column(Integer, server_default="0")
    block_5 = Column(Integer, server_default="0")
    block_6 = Column(Integer, server_default="0")
    block_7 = Column(Integer, server_default="0")
    block_8 = Column(Integer, server_default="0")
    block_9 = Column(Integer, server_default="0")
    block_10 = Column(Integer, server_default="0")
    block_11 = Column(Integer, server_default="0")
    block_12 = Column(Integer, server_default="0")
    block_13 = Column(Integer, server_default="0")
    block_14 = Column(Integer, server_default="0")
    block_15 = Column(Integer, server_default="0")
    block_16 = Column(Integer, server_default="0")
    block_17 = Column(Integer, server_default="0")
    block_18 = Column(Integer, server_default="0")
    block_19 = Column(Integer, server_default="0")
    block_20 = Column(Integer, server_default="0")
    block_21 = Column(Integer, server_default="0")
    block_22 = Column(Integer, server_default="0")
    block_23 = Column(Integer, server_default="0")
    block_24 = Column(Integer, server_default="0")
    block_25 = Column(Integer, server_default="0")
    basement = Column(Integer, server_default="0")
    project = Column(Integer, server_default="0")
    comment = Column(String, server_default="")
    object_id = Column(Integer, ForeignKey("object.id"))
    deleted_ts = Column(Integer, server_default="0")
    user_id = Column(String, server_default="")

    __table_args__ = {"sqlite_autoincrement": True}


class ItemType(Base):
    __tablename__ = "item_type"

    id = Column(String, primary_key=True)


class Cable(Base):
    __tablename__ = "cable"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    block_1 = Column(Float, server_default="0")
    block_2 = Column(Float, server_default="0")
    block_3 = Column(Float, server_default="0")
    block_4 = Column(Float, server_default="0")
    block_5 = Column(Float, server_default="0")
    block_6 = Column(Float, server_default="0")
    block_7 = Column(Float, server_default="0")
    block_8 = Column(Float, server_default="0")
    block_9 = Column(Float, server_default="0")
    block_10 = Column(Float, server_default="0")
    block_11 = Column(Float, server_default="0")
    block_12 = Column(Float, server_default="0")
    block_13 = Column(Float, server_default="0")
    block_14 = Column(Float, server_default="0")
    block_15 = Column(Float, server_default="0")
    block_16 = Column(Float, server_default="0")
    block_17 = Column(Float, server_default="0")
    block_18 = Column(Float, server_default="0")
    block_19 = Column(Float, server_default="0")
    block_20 = Column(Float, server_default="0")
    block_21 = Column(Float, server_default="0")
    block_22 = Column(Float, server_default="0")
    block_23 = Column(Float, server_default="0")
    block_24 = Column(Float, server_default="0")
    block_25 = Column(Float, server_default="0")
    basement = Column(Float, server_default="0")
    project = Column(Float, server_default="0")
    comment = Column(String, server_default="")
    object_id = Column(Integer, ForeignKey("object.id"))
    deleted_ts = Column(Integer, server_default="0")
    user_id = Column(String, server_default="")

    __table_args__ = {"sqlite_autoincrement": True}


class User(Base):
    __tablename__ = "user"

    id = Column(String, primary_key=True)
    password = Column(String, nullable=False)
    admin = Column(Integer, nullable=False)
    editor = Column(Integer, nullable=False)
    advanced_editor = Column(Integer, server_default="0")


class WebServerSession(Base):
    __tablename__ = "session"

    id = Column(String, primary_key=True)
    created_ts = Column(Integer, nullable=False)
    user_id = Column(String, ForeignKey("user.id"))


class History(Base):
    __tablename__ = "history"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False)
    ts = Column(Integer, nullable=False)
    table = Column(String, nullable=False)
    row = Column(String, nullable=False)
    column = Column(String, nullable=False)
    value = Column(String, nullable=False)


Index("history_table_row_column_idx", History.table, History.row, History.column)
Index("history_table_ts_idx", History.table, History.ts)


class SchemaVersion(Base):
    __tablename__ = "schema_version"

    id = Column(Integer, primary_key=True)
    schema_version = Column(Integer, nullable=False)


__engine = None


def init_db(app_wd):
    global __engine
    __engine = create_engine(
        "sqlite:///{}".format(os.path.join(app_wd, "database.db")),
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(__engine)


def get_engine():
    return __engine


def obj_to_dict(db_class, obj):
    res = {}
    for column in db_class.metadata.tables[db_class.__tablename__].columns:
        res[column.name] = getattr(obj, column.name)
    return res


def get_schema_version(session):
    row = session.query(SchemaVersion).all()
    if len(row) > 1:
        raise RuntimeError("unexpected number of rows in schema_version table")
    return None if not row else row[0].schema_version


def init_schema_version(session):
    session.add(SchemaVersion(id=1, schema_version=3))


def init_user(session):
    session.add(User(id="admin", password="", admin=1, editor=1, advanced_editor=1))


def init_item_type(session):
    session.add(ItemType(id="Şkaf  x16"))
    session.add(ItemType(id="Şkaf  x32"))
    session.add(ItemType(id="Şkaf  x64"))
    session.add(ItemType(id="Cartridge splitter  x2"))
    session.add(ItemType(id="Cartridge splitter  x4"))
    session.add(ItemType(id="Cartridge splitter  x8"))
    session.add(ItemType(id="Cartridge splitter  x16"))
    session.add(ItemType(id="Cartridge splitter  x32"))
    session.add(ItemType(id="Mufta  1x48"))
    session.add(ItemType(id="Mufta  1x96"))
    session.add(ItemType(id="Mufta  KKC"))
    session.add(ItemType(id="Payka  Pikteyl"))
    session.add(ItemType(id="Payka  Gilza"))
    session.add(ItemType(id="RAK  x4"))
    session.add(ItemType(id="ODF RAK  x12"))
    session.add(ItemType(id="ODF RAK  x24"))
    session.add(ItemType(id="ODF RAK  x48"))
    session.add(ItemType(id="ODF RAK  x48 dx"))
    session.add(ItemType(id="ODF RAK  1x24 dx"))
    session.add(ItemType(id="ODF RAK  1x24 dx divar"))
    session.add(ItemType(id="Adapter  SC/SC"))
    session.add(ItemType(id="Adapter  SC/SC DX"))
    session.add(ItemType(id="Patchcord  SC-SC -1m"))
    session.add(ItemType(id="Patchcord  SC-SC -3m"))
    session.add(ItemType(id="Drop  Qara (metr)"))
    session.add(ItemType(id="Drop  Ağ   (metr)"))
    session.add(ItemType(id="Mərtəbə arası Borular 2,5m (əd)"))
    session.add(ItemType(id="Mərtəbə arası Borular 2,5m (metr)"))
    session.add(ItemType(id="Mərtəbə arası Borular 3,3m (əd)"))
    session.add(ItemType(id="Mərtəbə arası Borular 3,3m (metr)"))
    session.add(ItemType(id="Şlanq  Plasmas  d20"))
    session.add(ItemType(id="Trank  16x16mm"))
    session.add(ItemType(id="Trank  25x25mm"))
    session.add(ItemType(id="Trank  40x25mm"))
    session.add(ItemType(id="Trank  40x40mm"))
    session.add(ItemType(id="Trank  60x60mm"))
    session.add(ItemType(id="Stolb  5m"))
    session.add(ItemType(id="Stolb  6m"))
    session.add(ItemType(id="Stolb  6,5m"))
    session.add(ItemType(id="Stolb  7m"))
    session.add(ItemType(id="Stolb  8m"))
    session.add(ItemType(id="Stolb  9m"))
    session.add(ItemType(id="Stolb  10m"))
    session.add(ItemType(id="Stolb  12m"))
    session.add(ItemType(id="Yeraltı  DN110"))
    session.add(ItemType(id="Yeraltı  KKC"))


def init_tables(session):
    schema_version = get_schema_version(session)
    if schema_version is None:
        init_schema_version(session)
        init_user(session)
        init_item_type(session)
        session.commit()
    else:
        def upgrade_schema_version(new_schema_version, queries):
            if schema_version < new_schema_version:
                with __engine.begin() as connection:
                    for query in queries:
                        if isinstance(query, (tuple, list)):
                            connection.execute(query[0], query[1])
                        else:
                            connection.execute(query)
                    connection.execute("UPDATE schema_version SET schema_version=?", (new_schema_version,))

        upgrade_schema_version(
            1,
            [
                "ALTER TABLE project ADD COLUMN comment TEXT DEFAULT ''"
            ]
        )
        upgrade_schema_version(
            2,
            [
                "ALTER TABLE user ADD COLUMN advanced_editor INTEGER DEFAULT '0'"
            ]
        )
        upgrade_schema_version(
            3,
            [
                "ALTER TABLE object ADD COLUMN extra_codes TEXT DEFAULT ''"
            ]
        )


if __name__ == "__main__":
    db_fn = "C:\\temp\\database.db"
    if os.path.exists(db_fn):
        os.remove(db_fn)
    init_db("C:\\temp")
    with Session(__engine) as session:
        init_tables(session)

        item_types = session.query(ItemType).all()

        olt_count = 50
        project_count = 1
        object_count = 100
        cable_count = 15

        olt_id = 0
        project_id = 0
        object_id = 0
        item_id = 0
        cable_id = 0

        object_processed = 0
        object_total = olt_count * project_count * object_count

        t = time.time()
        ts = [int(t) - 365 * 24 * 60 * 60]

        def update_history(props, table, row):
            for k, v in props.items():
                history = History(
                    user_id="admin",
                    ts=ts[0],
                    table=table,
                    row=row,
                    column=k,
                    value=v
                )
                session.add(history)
                ts[0] += 2

        for olt_i in range(olt_count):
            olt_id += 1
            props = dict(
                name="New OLT {:03d}".format(olt_i + 1),
                gpon=1,
                odf=1,
                olt=1,
                connector=1,
                pt=1,
                ups=1
            )
            olt = OLT(**dict(props, id=olt_id))
            session.add(olt)
            update_history(props, "olt", olt_id)

            for project_i in range(project_count):
                project_id += 1
                props = dict(
                    name="New project {:03d}-{:03d}".format(olt_i + 1, project_i + 1)
                )
                project = Project(**dict(props, id=project_id, olt_id=olt_id))
                session.add(project)
                update_history(props, "project", project_id)

                for object_i in range(object_count):
                    object_id += 1
                    props = dict(
                        name="New object {:03d}-{:03d}-{:03d}".format(olt_i + 1, project_i + 1, object_i + 1),
                        addr="Some addr {:03d}".format(object_i + 1),
                        blocks=4,
                        levels=16,
                        apartments=256,
                        branch="Some branch {:03d}".format(object_i + 1),
                        comment="Some comment {:03d}".format(object_i + 1)
                    )
                    obj = Object(**dict(props, id=object_id, project_id=project_id))
                    session.add(obj)
                    update_history(props, "object", object_id)

                    for item_i, item_type in enumerate(item_types):
                        item_id += 1
                        props = dict(
                            name=item_type.id,
                            block_1=1,
                            block_2=1,
                            block_3=1,
                            block_4=1,
                            basement=1,
                            project=7,
                            comment="Some comment {:03d}".format(item_i + 1)
                        )
                        item = Item(**dict(props, id=item_id, object_id=object_id))
                        session.add(item)
                        update_history(props, "item", item_id)

                    for cable_i in range(cable_count):
                        cable_id += 1
                        props = dict(
                            name="FO{}-{:03d}-{:03d}-{:03d}".format(cable_i + 1, olt_i + 1, project_i + 1, object_i + 1),
                            block_1=1,
                            block_2=1,
                            block_3=1,
                            block_4=1,
                            basement=1,
                            project=7,
                            comment="Some comment {:03d}".format(cable_i + 1)
                        )
                        cable = Cable(**dict(props, id=cable_id, object_id=object_id))
                        session.add(cable)
                        update_history(props, "cable", cable_id)

                    session.commit()

                    object_processed += 1
                    if object_processed % 10 == 0:
                        eta = (time.time() - t) / object_processed * (object_total - object_processed)
                        print("{} / {} processed, ETA {} s".format(object_processed, object_total, int(eta)))
