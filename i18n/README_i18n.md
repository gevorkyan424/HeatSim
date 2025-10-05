# Локализация (i18n)

В проекте включена инфраструктура для переключения языка (RU/EN) через Qt Translator.

## Файлы переводов

Ожидаемые бинарные файлы переводов:
- i18n/HeatSim_ru.qm
- i18n/HeatSim_en.qm

Эти файлы генерируются из источников .ts и подключаются автоматически на старте
в зависимости от настроек пользователя (см. QSettings key `ui/language`).

## Как сгенерировать .qm

1) Установите Qt лингвистические инструменты:
   - Вариант A: Qt (Qt Linguist Tools) — доступны `lupdate` и `lrelease`.
   - Вариант B: PyQt5 tools — доступны `pylupdate5` и `lrelease`.

2) Соберите .ts из исходников:

   Пример (Windows PowerShell):
   
    - Сгенерировать русский и английский .ts (PyQt5):
       pylupdate5 interface.py analysis_interface.py -ts i18n/HeatSim_ru.ts i18n/HeatSim_en.ts

    - Либо через Qt (Qt6/Qt5):
       lupdate interface.py analysis_interface.py -ts i18n/HeatSim_ru.ts i18n/HeatSim_en.ts

   - Откройте .ts в Qt Linguist и переведите строки.

3) Соберите .qm из .ts:

   lrelease i18n/HeatSim_ru.ts -qm i18n/HeatSim_ru.qm
   lrelease i18n/HeatSim_en.ts -qm i18n/HeatSim_en.qm

4) Запустите приложение и используйте правые верхние кнопки RU/EN для мгновенного переключения языка. Перезапуск не требуется; при наличии .qm переводы применяются на лету.

## Примечания
- Уже обёрнуты ключевые строки меню и заголовок главного окна в self.tr().
- По мере необходимости можно добавлять self.tr() вокруг видимых пользователю строк в других частях UI.
