call venv\Scripts\activate
pyside6-uic enter_window.ui -o enter_window_ui.py
pyside6-uic main_window.ui -o main_window_ui.py
pyside6-uic item_types_window.ui -o item_types_window_ui.py
pyside6-uic users_window.ui -o users_window_ui.py
pyside6-uic history_window.ui -o history_window_ui.py
pyside6-uic user_history_window.ui -o user_history_window_ui.py
pyside6-uic select_users_window.ui -o select_users_window_ui.py
pyside6-lupdate main.py enter_window.ui main_window.ui item_types_window.ui users_window.ui history_window.ui user_history_window.ui select_users_window.ui -ts i18n/app_ru.ts i18n/app_az.ts -locations none
pyside6-lrelease i18n/app_ru.ts i18n/app_az.ts
pyside6-rcc app.qrc -o app_rc.py
pause
