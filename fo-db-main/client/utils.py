from PySide6.QtWidgets import QHeaderView, QStyledItemDelegate, QSpinBox, QLineEdit, QComboBox, QAbstractItemView, QApplication, QDoubleSpinBox, QAbstractSpinBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette
import time
import re


CABLE_NAME_RE = re.compile("^(FO[0-9]+).*$")


def tr(s):
    return QApplication.translate("", s)


def to_widget_ts(ts):
    return "" if ts == 0 else time.strftime("%Y-%m-%d %H-%M-%S", time.localtime(ts))


class Cell(object):
    __slots__ = [
        "type",
        "name",
        "label",
        "min",
        "max",
        "items",
        "calculated",
        "column",
        "readonly",
        "to_widget",
        "to_backend",
        "validate"
    ]

    def __init__(
        self,
        type,
        name,
        label=None,
        min=None,
        max=None,
        items=None,
        calculated=False,
        column=None,
        readonly=False,
        to_widget=None,
        to_backend=None,
        validate=None
    ):
        self.type = type
        self.name = name
        self.label = label
        self.min = min
        self.max = max
        self.items = items
        self.calculated = calculated
        self.column = column
        self.readonly = readonly
        self.to_widget = to_widget
        self.to_backend = to_backend
        self.validate = validate


def prepare_cells(cells):
    for column, cell in enumerate(cells):
        cell.column = column
        if cell.label is None:
            cell.label = cell.name
        if cell.type in ["i", "f"]:
            if cell.min is None:
                cell.min = 0
            if cell.max is None:
                cell.max = 10**6
        elif cell.type == "e":
            if cell.items is None:
                cell.items = []
    return cells


def create_name_to_cell(cells):
    return {cell.name: cell for cell in cells}


class RowCore(object):
    __slots__ = ["__table", "__row", "__name_to_cell"]

    def __init__(self, table, row, name_to_cell):
        self.table = table
        self.row = row
        self.name_to_cell = name_to_cell


def Row(table, row, name_to_cell):
    class RowInternal(object):
        def get_id(self):
            index = table.model().index(row, 0)
            return index.data(Qt.UserRole)

        def get_row(self):
            return row

        def __getattr__(self, name):
            cell = name_to_cell[name]
            index = table.model().index(row, cell.column)
            return index.data()

        def __setattr__(self, name, value):
            cell = name_to_cell[name]
            index = table.model().index(row, cell.column)
            table.model().setData(index, value)

    return RowInternal()


class QSpinBoxEx(QSpinBox):
    def wheelEvent(self, e):
        pass


class QDoubleSpinBoxEx(QDoubleSpinBox):
    def wheelEvent(self, e):
        pass


class QComboBoxEx(QComboBox):
    def wheelEvent(self, e):
        pass


class Delegate(QStyledItemDelegate):
    __slots__ = ["__table", "__cells"]

    def __init__(self, table, cells, on_create_editor):
        super().__init__()
        self.__table = table
        self.__cells = cells
        self.__on_create_editor = on_create_editor
        self.readonly = False

    def createEditor(self, parent, option, index):
        cell = self.__cells[index.column()]
        first_cell_index = index.model().index(index.row(), 0)
        self.__on_create_editor(first_cell_index.data(Qt.UserRole), cell.name, first_cell_index.data())
        if cell.type in ["i", "f"]:
            if cell.calculated or cell.readonly or self.readonly:
                editor = QLineEdit(parent)
                editor.setReadOnly(True)
            else:
                editor = (QSpinBoxEx if cell.type == "i" else QDoubleSpinBoxEx)(parent)
                editor.setMinimum(cell.min)
                editor.setMaximum(cell.max)
                editor.setButtonSymbols(QAbstractSpinBox.NoButtons)
        elif cell.type == "s":
            editor = QLineEdit(parent)
            if cell.calculated or cell.readonly or self.readonly:
                editor.setReadOnly(True)
        elif cell.type == "e":
            if cell.calculated or cell.readonly or self.readonly:
                editor = QLineEdit(parent)
                editor.setReadOnly(True)
            else:
                editor = QComboBoxEx(parent)
                for item in cell.items:
                    editor.addItem(item)
        return editor

    def setEditorData(self, editor, index):
        data = index.data()
        cell = self.__cells[index.column()]
        if cell.type in ["i", "f"]:
            if cell.calculated or cell.readonly or self.readonly:
                editor.setText("{:.2f}".format(data) if cell.type == "f" else str(data))
            else:
                editor.setValue(data)
        elif cell.type == "s":
            editor.setText(data)
        elif cell.type == "e":
            if cell.calculated or cell.readonly or self.readonly:
                editor.setText(data)
            else:
                editor.setCurrentText(data)

    def setModelData(self, editor, model, index):
        cell = self.__cells[index.column()]
        if cell.calculated or cell.readonly or self.readonly:
            return
        if cell.type in ["i", "f"]:
            value = editor.value()
        elif cell.type == "s":
            value = editor.text()
        elif cell.type == "e":
            value = editor.currentText()
        if cell.validate and not cell.validate(index.row(), cell, value):
            return
        model.setData(index, value)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)

    def paint(self, painter, option, index):
        cell = self.__cells[index.column()]
        if cell.type in ["i", "f"] and index.data() == 0:
            if self.__table.selectionBehavior() == QAbstractItemView.SelectRows:
                indexes = option.widget.selectedIndexes()
                selected = indexes and indexes[0].row() == index.row()
                if selected:
                    painter.fillRect(option.rect, option.palette.color(QPalette.Highlight))
                else:
                    painter.fillRect(option.rect, option.palette.color(QPalette.Base))
            else:
                painter.fillRect(option.rect, option.palette.color(QPalette.Base))
            return
        super().paint(painter, option, index)

    def displayText(self, value, locale):
        return "{:.2f}".format(value) if isinstance(value, float) else super().displayText(value, locale)


def prepare_table(table, cells, on_create_editor):
    table.setColumnCount(len(cells))
    table.setHorizontalHeaderLabels([cell.label for cell in cells])
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
    delegate = Delegate(table, cells, on_create_editor)
    table.setItemDelegate(delegate)
    table.setEditTriggers(QAbstractItemView.AllEditTriggers)
    return delegate


def create_cell_changed(table, cells, delegate, calculate=None, commit=None):
    def cell_changed(row, column):
        cell = cells[column]
        if cell.calculated or cell.readonly or delegate.readonly:
            return
        calculate and calculate(table, row, column)
        commit and commit(table, row, column)
    return cell_changed


def insert_item(item, table, cells, cell_changed, calculate=None):
    table.cellChanged.disconnect()
    row = table.rowCount()
    table.insertRow(row)
    for cell in cells:
        if cell.calculated:
            continue
        index = table.model().index(row, cell.column)
        value = item[cell.name]
        if cell.to_widget is not None:
            value = cell.to_widget(value)
        table.model().setData(index, value)
    index = table.model().index(row, 0)
    table.model().setData(index, item["id"], Qt.UserRole)
    calculate and calculate(table, row)
    table.cellChanged.connect(cell_changed)


def reload_table(items, table, cells, cell_changed, calculate=None, show_deleted=False):
    table.setRowCount(0)
    for item in items:
        if show_deleted or item.get("deleted_ts", 0) == 0:
            insert_item(item, table, cells, cell_changed, calculate)


def reload_combobox(items, combobox, combobox_changed, show_deleted=False):
    combobox.currentTextChanged.disconnect()
    combobox.clear()
    combobox.currentTextChanged.connect(combobox_changed)
    for item in items:
        deleted_ts = item.get("deleted_ts", 0)
        if show_deleted or deleted_ts == 0:
            name = item["name"]
            if item.get("comment"):
                name = "{}***".format(name)
            if deleted_ts > 0:
                name = "{} ({})".format(name, tr("Deleted"))
            combobox.addItem(name, item["id"])
            if deleted_ts > 0:
                tooltip = "{} {} {}".format(tr("Deleted"), to_widget_ts(deleted_ts), item["user_id"])
                combobox.setItemData(combobox.count() - 1, tooltip, Qt.ToolTipRole)


class Table(object):
    def __init__(self, table, cells, items, calculate=None, backend=None, table_name=None, on_create_editor=None):
        self.table = table
        self.cells = prepare_cells(cells)
        self.name_to_cell = create_name_to_cell(self.cells)
        self.calculate = calculate

        def commit(table, row, column):
            id = table.model().index(row, 0).data(Qt.UserRole)
            cell = self.cells[column]
            name = cell.name
            value = table.model().index(row, column).data()
            if cell.to_backend is not None:
                value = cell.to_backend(value)
            backend.update(table_name, {"id": id, name: value})

        self.delegate = prepare_table(self.table, self.cells, lambda row, column, row_name: on_create_editor and on_create_editor(table_name, row, column, row_name))
        self.cell_changed = create_cell_changed(self.table, self.cells, self.delegate, self.calculate, commit)
        table.cellChanged.connect(self.cell_changed)
        self.reload(items)

    def reload(self, items, show_deleted=False, readonly=False):
        reload_table(items, self.table, self.cells, self.cell_changed, self.calculate, show_deleted)
        self.delegate.readonly = show_deleted or readonly

    def insert(self, item):
        insert_item(item, self.table, self.cells, self.cell_changed, self.calculate)

    def row(self, row):
        return Row(self.table, row, self.name_to_cell)

    def selected_row(self):
        indexes = self.table.selectedIndexes()
        if not indexes:
            return None
        return Row(self.table, indexes[0].row(), self.name_to_cell)

    def find(self, row_name):
        for row in range(self.table.rowCount()):
            if self.table.model().index(row, 0).data() == row_name:
                return row
        return -1


def cable_type(cable_name):
    m = CABLE_NAME_RE.match(cable_name)
    return None if m is None else m.group(1)
