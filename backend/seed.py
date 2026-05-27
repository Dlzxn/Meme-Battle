"""Seed database with memes and situations."""
import asyncio
import logging

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.config import settings
from app.database import Base
from app.models import Meme, Situation, SituationCategory, SpecialType
import app.models  # noqa

logger = logging.getLogger(__name__)

engine = create_async_engine(settings.database_url)
Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# ─── Popular meme templates (deduplicated by URL) ──────────────────────────
STARTER_MEMES = [
    # Tier 1 — universally recognized
    ("https://i.imgflip.com/4t0m5.jpg",    "Drake Hotline Bling"),
    ("https://i.imgflip.com/26jxvz.png",   "Distracted Boyfriend"),
    ("https://i.imgflip.com/1bij.jpg",     "This Is Fine"),
    ("https://i.imgflip.com/2wifvo.jpg",   "Surprised Pikachu"),
    ("https://i.imgflip.com/1e7ql7.jpg",   "One Does Not Simply"),
    ("https://i.imgflip.com/3oevdk.jpg",   "Expanding Brain"),
    ("https://i.imgflip.com/4acd7j.png",   "Woman Yelling At Cat"),
    ("https://i.imgflip.com/1ur9b0.jpg",   "Two Buttons"),
    ("https://i.imgflip.com/23ls.jpg",     "Batman Slapping Robin"),
    ("https://i.imgflip.com/3lmzyx.png",   "UNO Draw 25"),
    ("https://i.imgflip.com/30b1gx.jpg",   "Epic Handshake"),
    ("https://i.imgflip.com/5c7lwq.png",   "Always Has Been"),
    ("https://i.imgflip.com/2gnhut.jpg",   "Change My Mind"),
    ("https://i.imgflip.com/2hgfw.jpg",    "Hide The Pain Harold"),
    ("https://i.imgflip.com/1otk96.jpg",   "Mocking SpongeBob"),
    ("https://i.imgflip.com/1yxkcp.jpg",   "Roll Safe"),
    ("https://i.imgflip.com/3s08z3.jpg",   "Buff Doge vs Cheems"),
    ("https://i.imgflip.com/1jwhww.jpg",   "Is This A Pigeon"),
    ("https://i.imgflip.com/3lhx3p.jpg",   "Gru's Plan"),
    ("https://i.imgflip.com/2fm6x.jpg",    "Success Kid"),
    ("https://i.imgflip.com/37cjr.jpg",    "Futurama Fry"),
    ("https://i.imgflip.com/2yut.jpg",     "Philosoraptor"),
    ("https://i.imgflip.com/gk5el.jpg",    "Picard Facepalm"),
    ("https://i.imgflip.com/9vct.jpg",     "Ancient Aliens"),
    ("https://i.imgflip.com/2zo1ki.jpg",   "Monkey Puppet"),
    ("https://i.imgflip.com/3p3bij.jpg",   "Swole Doge vs Cheems"),
    ("https://i.imgflip.com/1kijv0.jpg",   "Tuxedo Winnie The Pooh"),
    ("https://i.imgflip.com/6v8xuo.jpg",   "GigaChad"),
    ("https://i.imgflip.com/5hfybi.jpg",   "Trade Offer"),
    ("https://i.imgflip.com/50lyb8.jpg",   "Panik Kalm Panik"),
    ("https://i.imgflip.com/33fb4o.jpg",   "Stonks"),
    ("https://i.imgflip.com/1bh8wl.jpg",   "Bad Luck Brian"),
    ("https://i.imgflip.com/5exjdv.jpg",   "Crying Cat"),
    ("https://i.imgflip.com/6nu7g.jpg",    "Michael Jordan Crying"),
    ("https://i.imgflip.com/qkpy2.jpg",    "Spiderman Pointing"),
    ("https://i.imgflip.com/n58iz.jpg",    "Confession Bear"),
    ("https://i.imgflip.com/92p3z.jpg",    "First World Problems"),
    ("https://i.imgflip.com/7d68p.jpg",    "Willy Wonka"),
    ("https://i.imgflip.com/2kbn1e.jpg",   "X X Everywhere"),
    ("https://i.imgflip.com/265k.jpg",     "Third World Skeptical Kid"),
    ("https://i.imgflip.com/1bhf.jpg",     "Y U No"),
    ("https://i.imgflip.com/3vfmyp.jpg",   "Socially Awkward Penguin"),
    ("https://i.imgflip.com/3lhx6x.jpg",   "Scumbag Steve"),
    ("https://i.imgflip.com/yz6t4.jpg",    "Good Guy Greg"),
    ("https://i.imgflip.com/g8k1s.jpg",    "Conspiracy Keanu"),
    ("https://i.imgflip.com/3idn.jpg",     "X All The Y"),
    ("https://i.imgflip.com/5cy0.jpg",     "10 Guy"),
    ("https://i.imgflip.com/3si4.jpg",     "Overly Attached Girlfriend"),
    ("https://i.imgflip.com/1o00in.jpg",   "American Chopper Argument"),
    ("https://i.imgflip.com/53ny2v.jpg",   "Marked Safe From"),
    # Tier 2 — highly popular
    ("https://i.imgflip.com/4vjgmh.jpg",   "Megamind Peeking"),
    ("https://i.imgflip.com/4hbspy.jpg",   "Gus Fring We Are Not The Same"),
    ("https://i.imgflip.com/30cub.jpg",    "Boardroom Meeting Suggestion"),
    ("https://i.imgflip.com/1c1uej.jpg",   "Oprah You Get A"),
    ("https://i.imgflip.com/43a45p.png",   "Chad vs Virgin"),
    ("https://i.imgflip.com/52e5ry.jpg",   "Running Away Balloon"),
    ("https://i.imgflip.com/6e73jb.jpg",   "Squid Game Doll"),
    ("https://i.imgflip.com/5y0m1d.jpg",   "Patrick To Do List"),
    ("https://i.imgflip.com/1g8my4.jpg",   "Big Brain Time"),
    ("https://i.imgflip.com/18iy.jpg",     "Not Sure If"),
    ("https://i.imgflip.com/8k0sa.jpg",    "Overthinking It"),
    ("https://i.imgflip.com/24y43o.jpg",   "Wait That's Illegal"),
    ("https://i.imgflip.com/3j193j.jpg",   "Clown Applying Makeup"),
    ("https://i.imgflip.com/57hz93.png",   "Running Guys"),
    ("https://i.imgflip.com/5oeoe8.jpg",   "Sigma Grindset"),
    ("https://i.imgflip.com/3udrba.jpg",   "Pushing And Pulling"),
    ("https://i.imgflip.com/1s3k5.jpg",    "I Should Buy A Boat Cat"),
    ("https://i.imgflip.com/9ehk.jpg",     "Waiting Skeleton"),
    ("https://i.imgflip.com/26xrd.jpg",    "The Most Interesting Man"),
    ("https://i.imgflip.com/3046y.jpg",    "Surprised Monkey"),
    ("https://i.imgflip.com/m78d.jpg",     "Ancient Aliens Guy"),
    ("https://i.imgflip.com/5p7csy.jpg",   "Two Paths"),
    ("https://i.imgflip.com/51wz3k.jpg",   "Finding Neverland"),
    ("https://i.imgflip.com/5lek8u.jpg",   "Technically True"),
    ("https://i.imgflip.com/vsg6f.jpg",    "90s Kid"),
    ("https://i.imgflip.com/4hf4s3.jpg",   "Karen"),
    ("https://i.imgflip.com/23bs8.jpg",    "Back In My Day"),
    ("https://i.imgflip.com/6t4ck9.jpg",   "Train vs School Bus"),
    ("https://i.imgflip.com/2ku1a0.jpg",   "I Bet He's Thinking About Others"),
    ("https://i.imgflip.com/5tf5gz.jpg",   "He Doesn't Know"),
    ("https://i.imgflip.com/3ot8g.jpg",    "Crazy Ex Girlfriend"),
    ("https://i.imgflip.com/2ag9iu.jpg",   "Success Kid Original"),
    ("https://i.imgflip.com/3c5uf8.png",   "Nobody Absolutely Nobody"),
    ("https://i.imgflip.com/1h7in3.jpg",   "Think About It"),
    ("https://i.imgflip.com/2hgfw.jpg",    "Hide The Pain Harold"),
    # Tier 3 — format classics
    ("https://i.imgflip.com/5nqgd5.jpg",   "Anakin Padme They're The Same"),
    ("https://i.imgflip.com/7y3xxu.jpg",   "Breaking Bad Say The Line"),
    ("https://i.imgflip.com/4pn1an.jpg",   "Awkward Monkey Puppet"),
    ("https://i.imgflip.com/5zvt5x.jpg",   "Average Fan vs Average Enjoyer"),
    ("https://i.imgflip.com/2f4e8m.jpg",   "Two Guys One Meme"),
    ("https://i.imgflip.com/44o2yb.jpg",   "Uno Reverse Card"),
    ("https://i.imgflip.com/2p4siq.jpg",   "Imagine If You Will"),
    ("https://i.imgflip.com/39t1o.jpg",    "It's Not Going To Happen"),
    ("https://i.imgflip.com/1jaa5.jpg",    "Super Cool Ski Instructor"),
    ("https://i.imgflip.com/dxb1z.jpg",    "Leonardo DiCaprio Cheers"),
    ("https://i.imgflip.com/u0qsb.jpg",    "Dwight Schrute"),
    ("https://i.imgflip.com/12mk4.jpg",    "That Would Be Great"),
    ("https://i.imgflip.com/3lhzgk.jpg",   "The Scroll Of Truth"),
    ("https://i.imgflip.com/5lkr2g.jpg",   "Distracted BF Upgrade"),
    ("https://i.imgflip.com/1o1hjq.jpg",   "Left Exit 12 Off Ramp"),
    ("https://i.imgflip.com/4x8nqu.jpg",   "Squid Game Cookie Shape"),
    ("https://i.imgflip.com/7e0f92.jpg",   "Let Me In"),
    ("https://i.imgflip.com/4tcb3m.jpg",   "History Of The World Part"),
    ("https://i.imgflip.com/3kvv0n.jpg",   "Grandma Finds The Internet"),
    ("https://i.imgflip.com/2xjb7k.jpg",   "Spongebob Ight Imma Head Out"),
    ("https://i.imgflip.com/68p9tr.jpg",   "Homer Simpson Backing Into Bushes"),
    ("https://i.imgflip.com/261o3j.jpg",   "How Tough Are You"),
    ("https://i.imgflip.com/4cq9qv.jpg",   "POV You're About To"),
    ("https://i.imgflip.com/6uhkuw.jpg",   "I Am Speed"),
    ("https://i.imgflip.com/cjuh3.jpg",    "Doge"),
    ("https://i.imgflip.com/28j0te.jpg",   "Flexing Skeleton"),
    ("https://i.imgflip.com/5b14vp.jpg",   "Nobody Me"),
    ("https://i.imgflip.com/30k24s.jpg",   "Clapping Kid"),
    ("https://i.imgflip.com/7br3zw.jpg",   "Russian Sleep Experiment"),
]

SPECIAL_MEMES = [
    ("https://i.imgflip.com/2zo1ki.jpg",   "Кража карты",    SpecialType.steal),
    ("https://i.imgflip.com/5c7lwq.png",   "Щит от штрафа",  SpecialType.skip_penalty),
    ("https://i.imgflip.com/3lmzyx.png",   "Двойной удар",   SpecialType.double_play),
]

# ─── Situations ──────────────────────────────────────────────────────────────

SITUATIONS: list[tuple[str, SituationCategory]] = [
    # ── Work ─────────────────────────────────────────────────────────────────
    ("Дедлайн через час, ты ещё не начинал", SituationCategory.work),
    ("Менеджер просит сделать «просто маленькую правку»", SituationCategory.work),
    ("Коллега снова не пришёл на митинг без предупреждения", SituationCategory.work),
    ("Тебя добавили в 10-й групповой чат за сегодня", SituationCategory.work),
    ("Баг в проде в пятницу в 18:00", SituationCategory.work),
    ("Клиент говорит «хочу как у конкурентов, только лучше»", SituationCategory.work),
    ("Шеф опять перепутал Slack и личные SMS", SituationCategory.work),
    ("Тебя повысили, но зарплату не подняли", SituationCategory.work),
    ("«Это срочно» — задача висит уже третий месяц", SituationCategory.work),
    ("Митинг, который мог быть письмом на 2 строки", SituationCategory.work),
    ("Принтер сломался именно в момент дедлайна", SituationCategory.work),
    ("Коллега объясняет Excel человеку с 20-летним стажем в Excel", SituationCategory.work),
    ("Руководитель добавляет новые требования за час до сдачи", SituationCategory.work),
    ("Кто-то в офисе разогрел рыбу в микроволновке", SituationCategory.work),
    ("Ты случайно написал в рабочий чат вместо личного", SituationCategory.work),
    ("Зарплата пришла, а уже ничего не осталось", SituationCategory.work),
    ("Корпоратив в будний день в 19:00 — обязательно", SituationCategory.work),
    ("Тебя попросили «быть позитивнее» на работе", SituationCategory.work),
    ("Опенспейс — сосед жуёт с открытым ртом весь день", SituationCategory.work),
    ("Коллега снова украл твою кружку из кухни", SituationCategory.work),
    ("Тимлид просит оценить задачу, которую ты видишь впервые", SituationCategory.work),
    ("Конференц-звонок, где все говорят одновременно", SituationCategory.work),
    ("«Я просто хочу уточнить» — следует 40 минут вопросов", SituationCategory.work),
    ("На собеседовании просят 10 лет опыта для джуниор-позиции", SituationCategory.work),
    ("Задача помечена «высокий приоритет» — её никто не трогает неделю", SituationCategory.work),
    ("Тебя добавили в проект за день до релиза", SituationCategory.work),
    ("Клиент одобрил дизайн, а потом попросил «чуть-чуть переделать»", SituationCategory.work),
    ("Zoom-звонок, а у тебя фон — бардак в комнате", SituationCategory.work),
    ("Тебе написали в 23:55 с пометкой «срочно»", SituationCategory.work),
    ("На ревью код-ревьюер нашёл запятую не там", SituationCategory.work),
    ("Интернет упал во время важной видеоконференции", SituationCategory.work),
    ("Шеф спрашивает почему нет прогресса — он же сам всё заблокировал", SituationCategory.work),
    ("Ты написал «с уважением» в конце злобного письма", SituationCategory.work),
    ("Задача в Jira открыта с 2019 года — никто не знает зачем", SituationCategory.work),
    ("Тебя попросили «просто задокументировать» 100 000 строк кода", SituationCategory.work),
    ("Пришёл в офис — а там ремонт и все работают в наушниках", SituationCategory.work),
    ("Твою идею отвергли, а потом предложили её же через месяц", SituationCategory.work),
    ("Коллега делает один и тот же баг третий раз подряд", SituationCategory.work),
    ("«Ты же не уйдёшь пока не доделаешь?» — в пятницу в 17:59", SituationCategory.work),
    ("Тебя отправили на тимбилдинг вместо отпуска", SituationCategory.work),
    ("Репозиторий упал, а бэкапа нет", SituationCategory.work),
    ("Тебя попросили подготовить презентацию — к завтрашнему утру", SituationCategory.work),
    ("«Давай без формальностей» — потом штрафуют за нарушение регламента", SituationCategory.work),
    ("Коллега берёт кредит на кофе-машину в офис и просит скинуться", SituationCategory.work),
    ("Тебе дали «удалённую» работу — требуют быть онлайн с 8 до 20", SituationCategory.work),

    # ── School ────────────────────────────────────────────────────────────────
    ("Учитель вызывает к доске — ты вообще не слушал", SituationCategory.school),
    ("Завтра экзамен, ты только открыл учебник в 23:00", SituationCategory.school),
    ("Сосед по парте просит списать в последнюю секунду", SituationCategory.school),
    ("Родители спрашивают про оценки за четверть", SituationCategory.school),
    ("Забыл дома домашнюю работу", SituationCategory.school),
    ("Учитель поймал с телефоном на уроке", SituationCategory.school),
    ("Контрольная перенесена на сегодня — тебя не предупредили", SituationCategory.school),
    ("Ты знал ответ, но не поднял руку вовремя", SituationCategory.school),
    ("Выучил не тот билет накануне экзамена", SituationCategory.school),
    ("Перемена кончилась, а ты в другом конце школы", SituationCategory.school),
    ("Учитель вернул тетрадь — она вся красная", SituationCategory.school),
    ("Группа молчит в чате до 23:58 — потом шквал вопросов", SituationCategory.school),
    ("Тест по предмету, который ты пропускал весь семестр", SituationCategory.school),
    ("Дипломный проект: 80 страниц написано, требуется 120", SituationCategory.school),
    ("Одногруппник сдал раньше всех — теперь он твоя совесть", SituationCategory.school),
    ("Профессор говорит «это было на прошлой лекции» — а ты прогулял", SituationCategory.school),
    ("Ты вышел к доске и забыл всё что знал", SituationCategory.school),
    ("Пересдача — а ты знаешь меньше чем на первом экзамене", SituationCategory.school),
    ("Учитель спрашивает «кто не сделал домашку» — молчание в классе", SituationCategory.school),
    ("Ты опоздал на 5 минут, а дверь заперта изнутри", SituationCategory.school),
    ("Тест по 20 страницам — ты прочитал аннотацию", SituationCategory.school),
    ("«Зачем мне это нужно в жизни?» — спросил ты на уроке математики", SituationCategory.school),
    ("Библиотека закрыта именно сегодня", SituationCategory.school),
    ("Списал у соседа, а у него тоже неправильно", SituationCategory.school),
    ("Последний день сдачи рефератов — а ты только выбрал тему", SituationCategory.school),
    ("Учитель вызвал родителей после одной пятёрки в конце четверти", SituationCategory.school),
    ("Ты получил тройку — а стараться начал только вчера", SituationCategory.school),
    ("В зачётке одна оценка, и она «удовлетворительно»", SituationCategory.school),
    ("Сессия через неделю — а ты ещё не открывал ни один конспект", SituationCategory.school),
    ("Автоматом не получил — а весь семестр думал что получишь", SituationCategory.school),

    # ── Relations ─────────────────────────────────────────────────────────────
    ("Партнёр говорит «всё нормально» — очень нехорошим тоном", SituationCategory.relations),
    ("Ты случайно поставил лайк на фото 2013 года", SituationCategory.relations),
    ("Друг снова просит денег до зарплаты — третий раз подряд", SituationCategory.relations),
    ("Тебя пригласили — и ты не понял, это свидание или нет", SituationCategory.relations),
    ("Написал сообщение — прочитано, ответа нет три часа", SituationCategory.relations),
    ("Бывший лайкнул твои сторис в 3 ночи", SituationCategory.relations),
    ("«Приедь через 5 минут» — ты ещё даже не одет", SituationCategory.relations),
    ("Подруга в 12-й раз рассказывает о том же парне", SituationCategory.relations),
    ("Друг в отношениях исчез — совсем", SituationCategory.relations),
    ("«Я не злюсь» — очень злым голосом", SituationCategory.relations),
    ("Забыл годовщину и вспомнил в полночь", SituationCategory.relations),
    ("Переписка начинается с «нам надо поговорить»", SituationCategory.relations),
    ("Встретил бывшего/бывшую в самом жалком своём виде", SituationCategory.relations),
    ("Друг отменяет планы за 10 минут до встречи", SituationCategory.relations),
    ("Мама звонит в самый неподходящий момент", SituationCategory.relations),
    ("Ты написал злое сообщение — и случайно отправил", SituationCategory.relations),
    ("Тебя познакомили с «идеальным» человеком — прямо сейчас", SituationCategory.relations),
    ("Сосед включает музыку в час ночи", SituationCategory.relations),
    ("Тебя добавили в семейный чат — без предупреждения", SituationCategory.relations),
    ("Родственники на застолье снова спрашивают про отношения", SituationCategory.relations),
    ("Ты попросил «честное мнение» — и оно оказалось честным", SituationCategory.relations),
    ("Друг опоздал на час и говорит «ну ты же знаешь меня»", SituationCategory.relations),
    ("Кто-то рассказал твой секрет — «случайно»", SituationCategory.relations),
    ("Тебе написали «спасибо, ты хороший друг» — после разрыва", SituationCategory.relations),
    ("Ты сказал «приходи в любое время» — и они пришли сейчас", SituationCategory.relations),
    ("Тебя пригласили на свадьбу людей, которых ты едва знаешь", SituationCategory.relations),
    ("Вся семья спрашивает «когда свадьба?» за столом", SituationCategory.relations),
    ("Ты решил поговорить серьёзно — а они начали смеяться", SituationCategory.relations),
    ("Друг ответил на твой длинный монолог: «угу»", SituationCategory.relations),
    ("Тебе написали «нам надо поговорить» — и ушли спать", SituationCategory.relations),

    # ── Internet ──────────────────────────────────────────────────────────────
    ("Сайт снова лежит — именно сейчас", SituationCategory.internet),
    ("YouTube: 30 секунд рекламы перед 15-секундным видео", SituationCategory.internet),
    ("Обновление Windows начинается прямо перед презентацией", SituationCategory.internet),
    ("Кто-то в комментах категорически не согласен с тобой", SituationCategory.internet),
    ("Интернет пропал в самый ответственный момент", SituationCategory.internet),
    ("Тебя забанили в любимом сабреддите без объяснений", SituationCategory.internet),
    ("Капча снова не признаёт тебя человеком", SituationCategory.internet),
    ("Телефон умер на 1% в неудобный момент", SituationCategory.internet),
    ("Google предлагает 10 страниц Stack Overflow — ни один не помог", SituationCategory.internet),
    ("Написал длинное сообщение — оно не отправилось", SituationCategory.internet),
    ("Каждый сайт требует «принять все куки»", SituationCategory.internet),
    ("Пароль не подходит, хотя ты уверен что он правильный", SituationCategory.internet),
    ("Wi-Fi ловит везде, кроме твоей комнаты", SituationCategory.internet),
    ("Приложение обновилось — и всё стало хуже", SituationCategory.internet),
    ("«Ваша сессия истекла» — посреди заполнения длинной формы", SituationCategory.internet),
    ("Реклама точно повторяет твой разговор часовой давности", SituationCategory.internet),
    ("«Отключи AdBlock» — там 15 рекламных баннеров сразу", SituationCategory.internet),
    ("Тебя добавили в спам-рассылку с 50 письмами в день", SituationCategory.internet),
    ("Скачал фильм 4К — он оказался в 480p", SituationCategory.internet),
    ("Твит случайно завирусился — и ты его уже удалил", SituationCategory.internet),
    ("Фотография не загружается 8-й раз подряд", SituationCategory.internet),
    ("Прошла отписка — теперь рекомендации стали ещё хуже", SituationCategory.internet),
    ("Комментарий с 1000 лайков противоречит здравому смыслу", SituationCategory.internet),
    ("«Ваш браузер устарел» — на Firefox 2 месяца назад", SituationCategory.internet),
    ("Ты ответил на спам ради интереса — теперь их втрое больше", SituationCategory.internet),
    ("Авторизация через соцсеть — а та требует авторизацию через другую", SituationCategory.internet),
    ("Онлайн-оплата не прошла — деньги списались", SituationCategory.internet),
    ("VPN включён — геоблокировка всё равно работает", SituationCategory.internet),
    ("QR-код не сканируется пятый раз", SituationCategory.internet),
    ("Ты открыл 47 вкладок «почитать потом» — не перечитал ни одну", SituationCategory.internet),
    ("Сторис просмотрена — человек видит что ты видел", SituationCategory.internet),
    ("Голосовое сообщение на 5 минут — вместо двух слов текстом", SituationCategory.internet),
    ("Телефон автоматически исправил важное слово в сообщении", SituationCategory.internet),
    ("Ты случайно заблокировал нужный контакт", SituationCategory.internet),
    ("«Скоро будет» — функция обещана три года назад", SituationCategory.internet),
    ("Интернет-банк завис в момент перевода", SituationCategory.internet),
    ("Тебя упомянули в мем-паблике без разрешения", SituationCategory.internet),
    ("«Ваш аккаунт заблокирован» — ты не нарушал правила", SituationCategory.internet),
    ("Уведомления от всех приложений одновременно в 7 утра", SituationCategory.internet),
    ("Онлайн-курс: 10 часов видео, 1 час реальной пользы", SituationCategory.internet),
    ("Ты поставил лайк не тому посту в прямом эфире", SituationCategory.internet),
    ("«Бесплатно» — потом оказалось подпиской", SituationCategory.internet),
    ("Поисковик запомнил твои странные запросы", SituationCategory.internet),
    ("Форум с ответом на твой вопрос закрыт в 2009 году", SituationCategory.internet),

    # ── All / General ─────────────────────────────────────────────────────────
    ("Будильник прозвонил — ты его выключил «на минуту»", SituationCategory.all),
    ("Вышел из дома и сразу понял что забыл что-то важное", SituationCategory.all),
    ("Магазин закрылся за 3 минуты до твоего прихода", SituationCategory.all),
    ("Очередь в супермаркете движется — твоя стоит", SituationCategory.all),
    ("Зарядка кончается в дороге, розетки нет", SituationCategory.all),
    ("Ты опоздал на автобус — следующий через 40 минут", SituationCategory.all),
    ("Заказал еду — курьер стоит у другого подъезда", SituationCategory.all),
    ("«Доставка 30 минут» — прошло 2 часа", SituationCategory.all),
    ("Лифт не работает — ты живёшь на 9-м этаже", SituationCategory.all),
    ("Пакет из супермаркета порвался на полдороге домой", SituationCategory.all),
    ("Чек нужен — а ты его выбросил", SituationCategory.all),
    ("Ты вспомнил что забыл что-то купить — уже дома", SituationCategory.all),
    ("Поставил кипятиться воду — и забыл на 40 минут", SituationCategory.all),
    ("Банкомат выдаёт только крупные купюры — тебе нужна мелочь", SituationCategory.all),
    ("Дождь начался ровно когда ты вышел без зонта", SituationCategory.all),
    ("Такси приехало не туда где ты стоишь", SituationCategory.all),
    ("Ты вбил пароль от Wi-Fi — он не подходит у гостей", SituationCategory.all),
    ("Пицца приехала холодная, но ты уже очень голоден", SituationCategory.all),
    ("На вечеринке ты единственный, кто не знает никого", SituationCategory.all),
    ("Ты взял последний кусок пиццы — и все посмотрели", SituationCategory.all),
    ("Купил билет заранее — концерт отменили", SituationCategory.all),
    ("Очередной «финальный» сезон оказался не финальным", SituationCategory.all),
    ("Ты надел наушники — провод зацепился за ручку двери", SituationCategory.all),
    ("Спойлер прилетел за 5 минут до финала", SituationCategory.all),
    ("Ты лёг спать в 10 — проснулся в 23 — теперь не заснёшь", SituationCategory.all),
    ("Поставил «посмотреть потом» — теперь 300 видео в очереди", SituationCategory.all),
    ("Оставил телефон в другой комнате — не можешь встать", SituationCategory.all),
    ("Ты искал очки 20 минут — они были на твоей голове", SituationCategory.all),
    ("Пришёл первым на вечеринку — никого нет", SituationCategory.all),
    ("Купил новую вещь — старая немедленно сломалась", SituationCategory.all),
]


async def fetch_imgflip_memes() -> list[tuple[str, str]]:
    if not HAS_HTTPX:
        return []
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get("https://api.imgflip.com/get_memes")
            data = resp.json()
            if not data.get("success"):
                return []
            return [
                (m["url"], m["name"])
                for m in data["data"]["memes"]
                if m.get("url") and m.get("name")
            ]
    except Exception as exc:
        logger.warning("imgflip API unavailable: %s", exc)
        return []


async def _upsert_meme(db: AsyncSession, url: str, name: str, category: str) -> None:
    existing = await db.execute(select(Meme).where(Meme.url == url))
    if not existing.scalars().first():
        db.add(Meme(url=url, name=name, category=category))


async def _run_migrations() -> None:
    from sqlalchemy import text
    for stmt in [
        "ALTER TYPE gamemode ADD VALUE IF NOT EXISTS 'arena'",
        "ALTER TABLE rooms ADD COLUMN IF NOT EXISTS rounds_count INTEGER NOT NULL DEFAULT 10",
    ]:
        try:
            async with engine.begin() as conn:
                await conn.execute(text(stmt))
        except Exception as exc:
            logger.warning("Migration skipped (%s): %s", stmt[:40], exc)


async def seed():
    await _run_migrations()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("Fetching memes from imgflip.com API…")
    api_memes = await fetch_imgflip_memes()
    print(f"  Got {len(api_memes)} templates from imgflip API")

    async with Session() as db:
        for url, name in api_memes:
            await _upsert_meme(db, url, name, "starter")

        for url, name in STARTER_MEMES:
            await _upsert_meme(db, url, name, "starter")

        for url, name, special_type in SPECIAL_MEMES:
            existing = await db.execute(select(Meme).where(Meme.url == url, Meme.is_special == True))
            if not existing.scalars().first():
                db.add(Meme(
                    url=url, name=name, category="special",
                    is_special=True, special_type=special_type,
                ))

        for text, category in SITUATIONS:
            existing = await db.execute(select(Situation).where(Situation.text == text))
            if not existing.scalars().first():
                db.add(Situation(text=text, category=category))

        await db.commit()

    total = len(api_memes) + len(STARTER_MEMES)
    print(f"Seed complete! Memes: ~{total} unique | Situations: {len(SITUATIONS)}")


if __name__ == "__main__":
    asyncio.run(seed())
