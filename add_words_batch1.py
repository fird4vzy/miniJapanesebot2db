"""
Adds a batch of 50 new words (25 N5 + 25 N4) to japanese_bot.db.
These were checked against the existing word list to avoid duplicates.

Run on the VPS, in the bot's folder, with the venv active:

    source venv/bin/activate
    python3 add_words_batch1.py

Safe to run once. Running it twice will insert the words again as
duplicates (there's no UNIQUE constraint on `word`), so don't re-run
unless you first check what's already there.
"""
import sqlite3

DB_NAME = 'japanese_bot.db'

NEW_WORDS = [
    # --- N5 ---
    {"word": "学校", "level": "N5", "romaji": "gakkou", "en_meaning": "school", "ru_meaning": "школа",
     "example_jp": "毎日学校に行きます。", "example_romaji": "Mainichi gakkou ni ikimasu.",
     "example_en": "I go to school every day.", "example_ru": "Я хожу в школу каждый день."},
    {"word": "先生", "level": "N5", "romaji": "sensei", "en_meaning": "teacher", "ru_meaning": "учитель",
     "example_jp": "先生はとても親切です。", "example_romaji": "Sensei wa totemo shinsetsu desu.",
     "example_en": "The teacher is very kind.", "example_ru": "Учитель очень добрый."},
    {"word": "学生", "level": "N5", "romaji": "gakusei", "en_meaning": "student", "ru_meaning": "студент",
     "example_jp": "彼は大学の学生です。", "example_romaji": "Kare wa daigaku no gakusei desu.",
     "example_en": "He is a university student.", "example_ru": "Он студент университета."},
    {"word": "友達", "level": "N5", "romaji": "tomodachi", "en_meaning": "friend", "ru_meaning": "друг",
     "example_jp": "友達と映画を見ました。", "example_romaji": "Tomodachi to eiga o mimashita.",
     "example_en": "I watched a movie with a friend.", "example_ru": "Я смотрел фильм с другом."},
    {"word": "本", "level": "N5", "romaji": "hon", "en_meaning": "book", "ru_meaning": "книга",
     "example_jp": "この本はおもしろいです。", "example_romaji": "Kono hon wa omoshiroi desu.",
     "example_en": "This book is interesting.", "example_ru": "Эта книга интересная."},
    {"word": "新聞", "level": "N5", "romaji": "shinbun", "en_meaning": "newspaper", "ru_meaning": "газета",
     "example_jp": "朝、新聞を読みます。", "example_romaji": "Asa, shinbun o yomimasu.",
     "example_en": "I read the newspaper in the morning.", "example_ru": "Утром я читаю газету."},
    {"word": "映画", "level": "N5", "romaji": "eiga", "en_meaning": "movie", "ru_meaning": "фильм",
     "example_jp": "週末に映画を見ます。", "example_romaji": "Shuumatsu ni eiga o mimasu.",
     "example_en": "I watch a movie on weekends.", "example_ru": "По выходным я смотрю фильм."},
    {"word": "色", "level": "N5", "romaji": "iro", "en_meaning": "color", "ru_meaning": "цвет",
     "example_jp": "好きな色は青です。", "example_romaji": "Sukina iro wa ao desu.",
     "example_en": "My favorite color is blue.", "example_ru": "Мой любимый цвет — синий."},
    {"word": "天気", "level": "N5", "romaji": "tenki", "en_meaning": "weather", "ru_meaning": "погода",
     "example_jp": "今日は天気がいいです。", "example_romaji": "Kyou wa tenki ga ii desu.",
     "example_en": "The weather is nice today.", "example_ru": "Сегодня хорошая погода."},
    {"word": "雨", "level": "N5", "romaji": "ame", "en_meaning": "rain", "ru_meaning": "дождь",
     "example_jp": "明日は雨が降るでしょう。", "example_romaji": "Ashita wa ame ga furu deshou.",
     "example_en": "It will probably rain tomorrow.", "example_ru": "Завтра, вероятно, пойдёт дождь."},
    {"word": "雪", "level": "N5", "romaji": "yuki", "en_meaning": "snow", "ru_meaning": "снег",
     "example_jp": "冬は雪がたくさん降ります。", "example_romaji": "Fuyu wa yuki ga takusan furimasu.",
     "example_en": "It snows a lot in winter.", "example_ru": "Зимой выпадает много снега."},
    {"word": "星", "level": "N5", "romaji": "hoshi", "en_meaning": "star", "ru_meaning": "звезда",
     "example_jp": "夜空に星がたくさん見えます。", "example_romaji": "Yozora ni hoshi ga takusan miemasu.",
     "example_en": "You can see many stars in the night sky.", "example_ru": "На ночном небе видно много звёзд."},
    {"word": "橋", "level": "N5", "romaji": "hashi", "en_meaning": "bridge", "ru_meaning": "мост",
     "example_jp": "この橋はとても長いです。", "example_romaji": "Kono hashi wa totemo nagai desu.",
     "example_en": "This bridge is very long.", "example_ru": "Этот мост очень длинный."},
    {"word": "店", "level": "N5", "romaji": "mise", "en_meaning": "shop", "ru_meaning": "магазин",
     "example_jp": "この店は九時に開きます。", "example_romaji": "Kono mise wa kuji ni akimasu.",
     "example_en": "This shop opens at nine o'clock.", "example_ru": "Этот магазин открывается в девять."},
    {"word": "銀行", "level": "N5", "romaji": "ginkou", "en_meaning": "bank", "ru_meaning": "банк",
     "example_jp": "銀行でお金を下ろしました。", "example_romaji": "Ginkou de okane o oroshimashita.",
     "example_en": "I withdrew money at the bank.", "example_ru": "Я снял деньги в банке."},
    {"word": "郵便局", "level": "N5", "romaji": "yuubinkyoku", "en_meaning": "post office", "ru_meaning": "почта",
     "example_jp": "郵便局で切手を買いました。", "example_romaji": "Yuubinkyoku de kitte o kaimashita.",
     "example_en": "I bought stamps at the post office.", "example_ru": "Я купил марки на почте."},
    {"word": "病気", "level": "N5", "romaji": "byouki", "en_meaning": "illness", "ru_meaning": "болезнь",
     "example_jp": "彼は病気で学校を休みました。", "example_romaji": "Kare wa byouki de gakkou o yasumimashita.",
     "example_en": "He missed school because of illness.", "example_ru": "Он пропустил школу из-за болезни."},
    {"word": "声", "level": "N5", "romaji": "koe", "en_meaning": "voice", "ru_meaning": "голос",
     "example_jp": "彼女の声はきれいです。", "example_romaji": "Kanojo no koe wa kirei desu.",
     "example_en": "Her voice is beautiful.", "example_ru": "У неё красивый голос."},
    {"word": "光", "level": "N5", "romaji": "hikari", "en_meaning": "light", "ru_meaning": "свет",
     "example_jp": "太陽の光がまぶしいです。", "example_romaji": "Taiyou no hikari ga mabushii desu.",
     "example_en": "The sunlight is dazzling.", "example_ru": "Солнечный свет слепит."},
    {"word": "火", "level": "N5", "romaji": "hi", "en_meaning": "fire", "ru_meaning": "огонь",
     "example_jp": "火に気をつけてください。", "example_romaji": "Hi ni ki o tsukete kudasai.",
     "example_en": "Please be careful with fire.", "example_ru": "Пожалуйста, будьте осторожны с огнём."},
    {"word": "木", "level": "N5", "romaji": "ki", "en_meaning": "tree", "ru_meaning": "дерево",
     "example_jp": "公園に大きい木があります。", "example_romaji": "Kouen ni ookii ki ga arimasu.",
     "example_en": "There is a big tree in the park.", "example_ru": "В парке есть большое дерево."},
    {"word": "石", "level": "N5", "romaji": "ishi", "en_meaning": "stone", "ru_meaning": "камень",
     "example_jp": "道に石がたくさんあります。", "example_romaji": "Michi ni ishi ga takusan arimasu.",
     "example_en": "There are many stones on the road.", "example_ru": "На дороге много камней."},
    {"word": "紙", "level": "N5", "romaji": "kami", "en_meaning": "paper", "ru_meaning": "бумага",
     "example_jp": "紙に名前を書いてください。", "example_romaji": "Kami ni namae o kaite kudasai.",
     "example_en": "Please write your name on the paper.", "example_ru": "Пожалуйста, напишите имя на бумаге."},
    {"word": "池", "level": "N5", "romaji": "ike", "en_meaning": "pond", "ru_meaning": "пруд",
     "example_jp": "公園の池に魚がいます。", "example_romaji": "Kouen no ike ni sakana ga imasu.",
     "example_en": "There are fish in the park pond.", "example_ru": "В пруду в парке есть рыба."},
    {"word": "音", "level": "N5", "romaji": "oto", "en_meaning": "sound", "ru_meaning": "звук",
     "example_jp": "変な音が聞こえました。", "example_romaji": "Hen na oto ga kikoemashita.",
     "example_en": "I heard a strange sound.", "example_ru": "Я услышал странный звук."},

    # --- N4 ---
    {"word": "卒業", "level": "N4", "romaji": "sotsugyou", "en_meaning": "graduation", "ru_meaning": "выпуск (окончание учёбы)",
     "example_jp": "来年、大学を卒業します。", "example_romaji": "Rainen, daigaku o sotsugyou shimasu.",
     "example_en": "I will graduate from university next year.", "example_ru": "В следующем году я закончу университет."},
    {"word": "入学", "level": "N4", "romaji": "nyuugaku", "en_meaning": "school enrollment", "ru_meaning": "поступление в школу",
     "example_jp": "四月に大学に入学します。", "example_romaji": "Shigatsu ni daigaku ni nyuugaku shimasu.",
     "example_en": "I will enroll in university in April.", "example_ru": "В апреле я поступаю в университет."},
    {"word": "締め切り", "level": "N4", "romaji": "shimekiri", "en_meaning": "deadline", "ru_meaning": "крайний срок",
     "example_jp": "レポートの締め切りは明日です。", "example_romaji": "Repouto no shimekiri wa ashita desu.",
     "example_en": "The report deadline is tomorrow.", "example_ru": "Крайний срок сдачи отчёта — завтра."},
    {"word": "遅刻", "level": "N4", "romaji": "chikoku", "en_meaning": "being late", "ru_meaning": "опоздание",
     "example_jp": "電車が遅れて、遅刻しました。", "example_romaji": "Densha ga okurete, chikoku shimashita.",
     "example_en": "The train was delayed, so I was late.", "example_ru": "Поезд задержался, и я опоздал."},
    {"word": "出張", "level": "N4", "romaji": "shucchou", "en_meaning": "business trip", "ru_meaning": "командировка",
     "example_jp": "来週、大阪に出張します。", "example_romaji": "Raishuu, Oosaka ni shucchou shimasu.",
     "example_en": "I have a business trip to Osaka next week.", "example_ru": "На следующей неделе я еду в командировку в Осаку."},
    {"word": "給料", "level": "N4", "romaji": "kyuuryou", "en_meaning": "salary", "ru_meaning": "зарплата",
     "example_jp": "今月の給料はまだです。", "example_romaji": "Kongetsu no kyuuryou wa mada desu.",
     "example_en": "This month's salary hasn't arrived yet.", "example_ru": "Зарплата за этот месяц ещё не пришла."},
    {"word": "税金", "level": "N4", "romaji": "zeikin", "en_meaning": "tax", "ru_meaning": "налог",
     "example_jp": "毎年税金を払います。", "example_romaji": "Maitoshi zeikin o haraimasu.",
     "example_en": "I pay taxes every year.", "example_ru": "Каждый год я плачу налоги."},
    {"word": "貯金", "level": "N4", "romaji": "chokin", "en_meaning": "savings", "ru_meaning": "сбережения",
     "example_jp": "旅行のために貯金しています。", "example_romaji": "Ryokou no tame ni chokin shite imasu.",
     "example_en": "I'm saving money for a trip.", "example_ru": "Я коплю деньги на путешествие."},
    {"word": "借りる", "level": "N4", "romaji": "kariru", "en_meaning": "to borrow", "ru_meaning": "занимать (брать взаймы)",
     "example_jp": "図書館で本を借りました。", "example_romaji": "Toshokan de hon o karimashita.",
     "example_en": "I borrowed a book from the library.", "example_ru": "Я взял книгу в библиотеке."},
    {"word": "貸す", "level": "N4", "romaji": "kasu", "en_meaning": "to lend", "ru_meaning": "одалживать",
     "example_jp": "友達にお金を貸しました。", "example_romaji": "Tomodachi ni okane o kashimashita.",
     "example_en": "I lent money to my friend.", "example_ru": "Я одолжил другу денег."},
    {"word": "返す", "level": "N4", "romaji": "kaesu", "en_meaning": "to return (something)", "ru_meaning": "возвращать",
     "example_jp": "明日、本を返します。", "example_romaji": "Ashita, hon o kaeshimasu.",
     "example_en": "I will return the book tomorrow.", "example_ru": "Завтра я верну книгу."},
    {"word": "選ぶ", "level": "N4", "romaji": "erabu", "en_meaning": "to choose", "ru_meaning": "выбирать",
     "example_jp": "好きな色を選んでください。", "example_romaji": "Sukina iro o erande kudasai.",
     "example_en": "Please choose your favorite color.", "example_ru": "Пожалуйста, выберите любимый цвет."},
    {"word": "比べる", "level": "N4", "romaji": "kuraberu", "en_meaning": "to compare", "ru_meaning": "сравнивать",
     "example_jp": "二つの製品を比べました。", "example_romaji": "Futatsu no seihin o kurabemashita.",
     "example_en": "I compared the two products.", "example_ru": "Я сравнил два товара."},
    {"word": "従う", "level": "N4", "romaji": "shitagau", "en_meaning": "to follow (rules)", "ru_meaning": "следовать",
     "example_jp": "規則に従ってください。", "example_romaji": "Kisoku ni shitagatte kudasai.",
     "example_en": "Please follow the rules.", "example_ru": "Пожалуйста, следуйте правилам."},
    {"word": "認める", "level": "N4", "romaji": "mitomeru", "en_meaning": "to admit / recognize", "ru_meaning": "признавать",
     "example_jp": "彼は自分の間違いを認めました。", "example_romaji": "Kare wa jibun no machigai o mitomemashita.",
     "example_en": "He admitted his mistake.", "example_ru": "Он признал свою ошибку."},
    {"word": "頼む", "level": "N4", "romaji": "tanomu", "en_meaning": "to request", "ru_meaning": "просить",
     "example_jp": "友達に手伝いを頼みました。", "example_romaji": "Tomodachi ni tetsudai o tanomimashita.",
     "example_en": "I asked a friend for help.", "example_ru": "Я попросил друга о помощи."},
    {"word": "断る", "level": "N4", "romaji": "kotowaru", "en_meaning": "to refuse", "ru_meaning": "отказывать",
     "example_jp": "彼の誘いを断りました。", "example_romaji": "Kare no sasoi o kotowarimashita.",
     "example_en": "I refused his invitation.", "example_ru": "Я отказался от его приглашения."},
    {"word": "謝る", "level": "N4", "romaji": "ayamaru", "en_meaning": "to apologize", "ru_meaning": "извиняться",
     "example_jp": "遅れたことを謝りました。", "example_romaji": "Okureta koto o ayamarimashita.",
     "example_en": "I apologized for being late.", "example_ru": "Я извинился за опоздание."},
    {"word": "疑う", "level": "N4", "romaji": "utagau", "en_meaning": "to doubt", "ru_meaning": "сомневаться",
     "example_jp": "彼の話を疑っています。", "example_romaji": "Kare no hanashi o utagatte imasu.",
     "example_en": "I doubt his story.", "example_ru": "Я сомневаюсь в его словах."},
    {"word": "支える", "level": "N4", "romaji": "sasaeru", "en_meaning": "to support", "ru_meaning": "поддерживать",
     "example_jp": "家族が私を支えてくれます。", "example_romaji": "Kazoku ga watashi o sasaete kuremasu.",
     "example_en": "My family supports me.", "example_ru": "Моя семья меня поддерживает."},
    {"word": "加える", "level": "N4", "romaji": "kuwaeru", "en_meaning": "to add", "ru_meaning": "добавлять",
     "example_jp": "砂糖を少し加えてください。", "example_romaji": "Satou o sukoshi kuwaete kudasai.",
     "example_en": "Please add a little sugar.", "example_ru": "Пожалуйста, добавьте немного сахара."},
    {"word": "増やす", "level": "N4", "romaji": "fuyasu", "en_meaning": "to increase (something)", "ru_meaning": "увеличивать",
     "example_jp": "貯金を増やしたいです。", "example_romaji": "Chokin o fuyashitai desu.",
     "example_en": "I want to increase my savings.", "example_ru": "Я хочу увеличить свои сбережения."},
    {"word": "減らす", "level": "N4", "romaji": "herasu", "en_meaning": "to decrease (something)", "ru_meaning": "уменьшать",
     "example_jp": "食べる量を減らしています。", "example_romaji": "Taberu ryou o herashite imasu.",
     "example_en": "I'm reducing the amount I eat.", "example_ru": "Я уменьшаю количество еды."},
    {"word": "防ぐ", "level": "N4", "romaji": "fusegu", "en_meaning": "to prevent", "ru_meaning": "предотвращать",
     "example_jp": "事故を防ぐために注意します。", "example_romaji": "Jiko o fusegu tame ni chuui shimasu.",
     "example_en": "I'll be careful to prevent an accident.", "example_ru": "Я буду осторожен, чтобы предотвратить аварию."},
    {"word": "争う", "level": "N4", "romaji": "arasou", "en_meaning": "to fight / dispute", "ru_meaning": "спорить, бороться",
     "example_jp": "二人はお金のことで争いました。", "example_romaji": "Futari wa okane no koto de arasoimashita.",
     "example_en": "The two of them argued about money.", "example_ru": "Они двое поспорили из-за денег."},
]


def main():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    # Skip anything that (somehow) already exists, so this is safe to
    # run more than once without creating duplicate rows.
    cur.execute("SELECT word FROM words")
    existing = {row[0] for row in cur.fetchall()}

    inserted = 0
    skipped = 0
    for w in NEW_WORDS:
        if w["word"] in existing:
            skipped += 1
            continue
        cur.execute(
            """INSERT INTO words
               (word, level, romaji, en_meaning, ru_meaning,
                example_jp, example_romaji, example_en, example_ru)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (w["word"], w["level"], w["romaji"], w["en_meaning"], w["ru_meaning"],
             w["example_jp"], w["example_romaji"], w["example_en"], w["example_ru"])
        )
        inserted += 1

    conn.commit()
    conn.close()
    print(f"✅ Inserted {inserted} new words, skipped {skipped} already present.")


if __name__ == "__main__":
    main()
