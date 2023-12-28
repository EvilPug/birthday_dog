# BIRTHDAY DOG
## Собака Поздравляка - Бот для создания чатов дней рождения

## Как появился бот
### Проблема
В нашем центре много сотрудников и каждый месяц мы собираем деньги на их дни рождения.
Обычно мы поступали так - вручную создавали чат и приглашали туда всех, кроме именинника, 
затем создавали счет в Тинькофф и кидали ссылку на него в чат. После сбора деньги отправляли имениннику,
а счет закрывали. Такой подход вынуждал менеджеров постоянно отслеживать дни рождения 
и заниматься рутинной работой по созданию чатов почти каждую неделю

### Решение
Мы решили автоматизировать подход. Посчитали, сколько чатов в теории может существовать одновременно и заранее создали для них счета.
Информацию о счетах, пользователях и созданных чатах мы отслеживаем в БД. Теперь алгоритм выглядит следующим образом:

1) Бот по расписанию проверяет, не будет ли у кого-нибудь в скором времени дня рождения
2) Если будет - создает для именинника чат, медленно добавляет пользователей (чтобы телеграм не ругался), выделяет счет, пишет введение в чат.
За одни сутки создаем только один чат - иначе телеграм банит бота, думая, что он спаммер
3) После дня рождения чат удаляется, счет снова становится свободен

## Функционал бота
- Отслеживает дни рождения пользователей чата (необходимо завести инфо в БД)
- Отслеживает ссылки на сборы денег (например в Тинькофф)
- Создает чат за N дней до дня рождения и приглашает туда всех кроме именинников
- Назначает администраторов чата
- Отправляет в чат введение со ссылкой на сбор денег
- Пользователям, которых не удалось пригласить отправляет ссылку на чат
- Через некоторое время после дня рождения удаляет чат и освобождает счет
- Имитирует пользователя при помощи случайных задержек между вызовами

## Используемый стек
- Python 3.9+
- Любая СУБД (в данный момент используем MariaDB)
- Airflow, cron или любой другой шедулер

## Инструкция по запуску:

1) Создайте отдельный телеграм-аккаунт для бота
2) Перейдите на сайт https://my.telegram.org/auth, авторизуйтесь и получите API_ID и API_HASH
3) Создайте **.env** файл в папке **src** со следующим содержанием:
    ```
    # Переменные, связанные с БД
    DB_HOST=''
    DB_PORT=''
    DB_USER=''
    DB_PASS=''
    DB_NAME=''
    
    # Переменные, связанные с ботом (получаем на https://my.telegram.org/auth)
    # В BOT_PHONE вводим номер телефона, который был использован для получения API ключа
    BOT_API_ID=''
    BOT_API_HASH=''
    BOT_PHONE=''
    
    # tg id администраторов бота. слитно через запятую
    ADMIN_IDS=''
    
    # id основного чата с пользователями
    MAIN_CHAT_ID=''

    # За сколько дней до ДР должен создаваться чат
    DAYS_BEFORE=7

    # Сколько дней после ДР чат должен существовать
    DAYS_AFTER=2

    ```

    

4) Создайте виртуальное окружение и установите зависимости
    ```
    python -m venv venv
    . ./venv/bin/activate
    pip3 install -r requirements.txt
    ```
5) Добавьте таски в шедулер
- Если используете cron - добавьте запуск main.py по расписанию
