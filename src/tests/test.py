from freezegun import freeze_time

from src.models import User
from src.utils import FindBirthday


test_users = [
    User(tg_id=55555,
         username='test1',
         short_name='Ваня',
         last_name='Иванов',
         birth_day=13,
         birth_month=1,
         gender='male',
         is_active=1),
    User(tg_id=666666,
         username='test2',
         short_name='Леша',
         last_name='Алексеев',
         birth_day=20,
         birth_month=6,
         gender='male',
         is_active=1),
    User(tg_id=7777777,
         username='test3',
         short_name='Вадим',
         last_name='Вадимов',
         birth_day=20,
         birth_month=10,
         gender='male',
         is_active=1),
]


@freeze_time("2023-06-16 03:00:00")
def test_check_birthday():
    assert FindBirthday.check_birthday(birth_month=1, birth_day=7) is False
    assert FindBirthday.check_birthday(birth_month=6, birth_day=12) is True
    assert FindBirthday.check_birthday(birth_month=6, birth_day=17) is True


@freeze_time("2023-06-16 03:00:00")
def test_get_birthday_users():
    fb = FindBirthday(test_users)
    bdayer_1 = test_users[0]
    bdayer_2 = test_users[1]

    print(fb.birthday_users)

    assert bdayer_1 not in fb.birthday_users
    assert bdayer_2 in fb.birthday_users
