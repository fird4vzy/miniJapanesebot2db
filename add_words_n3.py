"""
Adds 60 JLPT N3 (intermediate) words to japanese_bot.db.

Kanji and readings were taken from japanesetest4you.com's JLPT N3
vocabulary list rather than written from memory; example sentences and
Russian translations were written to match. Checked against the existing
words so nothing is duplicated.

Run on the VPS, in the bot's folder, with the venv active:

    source venv/bin/activate
    python3 add_words_n3.py

Idempotent — words already in the DB are skipped, so re-running is safe.
"""
import sqlite3

DB_NAME = 'japanese_bot.db'

NEW_WORDS = [
    {"word": "相手", "level": "N3", "romaji": "aite", "en_meaning": "partner / opponent", "ru_meaning": "собеседник, партнёр, соперник",
     "example_jp": "相手の話をよく聞きましょう。", "example_romaji": "Aite no hanashi o yoku kikimashou.",
     "example_en": "Let's listen carefully to the other person.", "example_ru": "Давайте внимательно выслушаем собеседника."},
    {"word": "愛する", "level": "N3", "romaji": "aisuru", "en_meaning": "to love", "ru_meaning": "любить",
     "example_jp": "家族を愛しています。", "example_romaji": "Kazoku o aishite imasu.",
     "example_en": "I love my family.", "example_ru": "Я люблю свою семью."},
    {"word": "明らか", "level": "N3", "romaji": "akiraka", "en_meaning": "obvious / clear", "ru_meaning": "очевидный, ясный",
     "example_jp": "答えは明らかです。", "example_romaji": "Kotae wa akiraka desu.",
     "example_en": "The answer is obvious.", "example_ru": "Ответ очевиден."},
    {"word": "諦める", "level": "N3", "romaji": "akirameru", "en_meaning": "to give up", "ru_meaning": "сдаваться, отказываться",
     "example_jp": "簡単に諦めないでください。", "example_romaji": "Kantan ni akiramenaide kudasai.",
     "example_en": "Please don't give up easily.", "example_ru": "Пожалуйста, не сдавайтесь так легко."},
    {"word": "安定", "level": "N3", "romaji": "antei", "en_meaning": "stability", "ru_meaning": "стабильность",
     "example_jp": "収入が安定しています。", "example_romaji": "Shuunyuu ga antei shite imasu.",
     "example_en": "My income is stable.", "example_ru": "Мой доход стабилен."},
    {"word": "汗", "level": "N3", "romaji": "ase", "en_meaning": "sweat", "ru_meaning": "пот",
     "example_jp": "暑くて汗が出ます。", "example_romaji": "Atsukute ase ga demasu.",
     "example_en": "It's hot and I'm sweating.", "example_ru": "Жарко, и я потею."},
    {"word": "与える", "level": "N3", "romaji": "ataeru", "en_meaning": "to give / to grant", "ru_meaning": "давать, предоставлять",
     "example_jp": "彼にチャンスを与えました。", "example_romaji": "Kare ni chansu o ataemashita.",
     "example_en": "I gave him a chance.", "example_ru": "Я дал ему шанс."},
    {"word": "扱う", "level": "N3", "romaji": "atsukau", "en_meaning": "to handle / to deal with", "ru_meaning": "обращаться, иметь дело",
     "example_jp": "この機械は丁寧に扱ってください。", "example_romaji": "Kono kikai wa teinei ni atsukatte kudasai.",
     "example_en": "Please handle this machine carefully.", "example_ru": "Пожалуйста, обращайтесь с этой машиной аккуратно."},
    {"word": "部分", "level": "N3", "romaji": "bubun", "en_meaning": "part / portion", "ru_meaning": "часть",
     "example_jp": "この部分がよく分かりません。", "example_romaji": "Kono bubun ga yoku wakarimasen.",
     "example_en": "I don't really understand this part.", "example_ru": "Эту часть я не очень понимаю."},
    {"word": "文句", "level": "N3", "romaji": "monku", "en_meaning": "complaint", "ru_meaning": "жалоба, претензия",
     "example_jp": "彼はいつも文句を言います。", "example_romaji": "Kare wa itsumo monku o iimasu.",
     "example_en": "He always complains.", "example_ru": "Он всегда жалуется."},
    {"word": "違い", "level": "N3", "romaji": "chigai", "en_meaning": "difference", "ru_meaning": "разница, различие",
     "example_jp": "二つの違いを説明してください。", "example_romaji": "Futatsu no chigai o setsumei shite kudasai.",
     "example_en": "Please explain the difference between the two.", "example_ru": "Пожалуйста, объясните разницу между ними."},
    {"word": "地域", "level": "N3", "romaji": "chiiki", "en_meaning": "area / region", "ru_meaning": "регион, район",
     "example_jp": "この地域は静かです。", "example_romaji": "Kono chiiki wa shizuka desu.",
     "example_en": "This area is quiet.", "example_ru": "Этот район тихий."},
    {"word": "知識", "level": "N3", "romaji": "chishiki", "en_meaning": "knowledge", "ru_meaning": "знания",
     "example_jp": "彼は知識が豊富です。", "example_romaji": "Kare wa chishiki ga houfu desu.",
     "example_en": "He has extensive knowledge.", "example_ru": "У него обширные знания."},
    {"word": "直接", "level": "N3", "romaji": "chokusetsu", "en_meaning": "direct / directly", "ru_meaning": "напрямую, непосредственно",
     "example_jp": "直接話した方がいいです。", "example_romaji": "Chokusetsu hanashita hou ga ii desu.",
     "example_en": "It's better to talk directly.", "example_ru": "Лучше поговорить напрямую."},
    {"word": "調査", "level": "N3", "romaji": "chousa", "en_meaning": "investigation / survey", "ru_meaning": "исследование, опрос",
     "example_jp": "会社が調査を行いました。", "example_romaji": "Kaisha ga chousa o okonaimashita.",
     "example_en": "The company conducted a survey.", "example_ru": "Компания провела исследование."},
    {"word": "調子", "level": "N3", "romaji": "choushi", "en_meaning": "condition / tone", "ru_meaning": "состояние, самочувствие",
     "example_jp": "今日は調子がいいです。", "example_romaji": "Kyou wa choushi ga ii desu.",
     "example_en": "I'm in good shape today.", "example_ru": "Сегодня я в хорошей форме."},
    {"word": "注目", "level": "N3", "romaji": "chuumoku", "en_meaning": "attention / notice", "ru_meaning": "внимание",
     "example_jp": "この技術が注目されています。", "example_romaji": "Kono gijutsu ga chuumoku sarete imasu.",
     "example_en": "This technology is getting attention.", "example_ru": "Эта технология привлекает внимание."},
    {"word": "注文", "level": "N3", "romaji": "chuumon", "en_meaning": "order / request", "ru_meaning": "заказ",
     "example_jp": "コーヒーを注文しました。", "example_romaji": "Koohii o chuumon shimashita.",
     "example_en": "I ordered a coffee.", "example_ru": "Я заказал кофе."},
    {"word": "中心", "level": "N3", "romaji": "chuushin", "en_meaning": "center / core", "ru_meaning": "центр",
     "example_jp": "町の中心に駅があります。", "example_romaji": "Machi no chuushin ni eki ga arimasu.",
     "example_en": "There's a station in the center of town.", "example_ru": "В центре города есть станция."},
    {"word": "代表", "level": "N3", "romaji": "daihyou", "en_meaning": "representative", "ru_meaning": "представитель",
     "example_jp": "彼が会社の代表です。", "example_romaji": "Kare ga kaisha no daihyou desu.",
     "example_en": "He is the company's representative.", "example_ru": "Он представитель компании."},
    {"word": "黙る", "level": "N3", "romaji": "damaru", "en_meaning": "to be silent", "ru_meaning": "молчать",
     "example_jp": "彼は黙って聞いていました。", "example_romaji": "Kare wa damatte kiite imashita.",
     "example_en": "He listened in silence.", "example_ru": "Он молча слушал."},
    {"word": "出会う", "level": "N3", "romaji": "deau", "en_meaning": "to meet by chance", "ru_meaning": "случайно встретить",
     "example_jp": "駅で友達に出会いました。", "example_romaji": "Eki de tomodachi ni deaimashita.",
     "example_en": "I ran into a friend at the station.", "example_ru": "Я случайно встретил друга на станции."},
    {"word": "伝統", "level": "N3", "romaji": "dentou", "en_meaning": "tradition", "ru_meaning": "традиция",
     "example_jp": "日本の伝統を守ります。", "example_romaji": "Nihon no dentou o mamorimasu.",
     "example_en": "We preserve Japanese traditions.", "example_ru": "Мы храним японские традиции."},
    {"word": "努力", "level": "N3", "romaji": "doryoku", "en_meaning": "effort", "ru_meaning": "усилие, старание",
     "example_jp": "毎日の努力が大切です。", "example_romaji": "Mainichi no doryoku ga taisetsu desu.",
     "example_en": "Daily effort is important.", "example_ru": "Ежедневные усилия важны."},
    {"word": "同僚", "level": "N3", "romaji": "douryou", "en_meaning": "coworker / colleague", "ru_meaning": "коллега",
     "example_jp": "同僚と昼ご飯を食べました。", "example_romaji": "Douryou to hirugohan o tabemashita.",
     "example_en": "I had lunch with a colleague.", "example_ru": "Я пообедал с коллегой."},
    {"word": "影響", "level": "N3", "romaji": "eikyou", "en_meaning": "influence / effect", "ru_meaning": "влияние",
     "example_jp": "天気は気分に影響します。", "example_romaji": "Tenki wa kibun ni eikyou shimasu.",
     "example_en": "Weather affects your mood.", "example_ru": "Погода влияет на настроение."},
    {"word": "得る", "level": "N3", "romaji": "eru", "en_meaning": "to gain / to obtain", "ru_meaning": "получать, приобретать",
     "example_jp": "経験を得ることが大切です。", "example_romaji": "Keiken o eru koto ga taisetsu desu.",
     "example_en": "Gaining experience is important.", "example_ru": "Важно получать опыт."},
    {"word": "不安", "level": "N3", "romaji": "fuan", "en_meaning": "anxiety / uneasiness", "ru_meaning": "тревога, беспокойство",
     "example_jp": "試験の前は少し不安です。", "example_romaji": "Shiken no mae wa sukoshi fuan desu.",
     "example_en": "I'm a little anxious before the exam.", "example_ru": "Перед экзаменом я немного волнуюсь."},
    {"word": "含む", "level": "N3", "romaji": "fukumu", "en_meaning": "to contain / to include", "ru_meaning": "содержать, включать",
     "example_jp": "料金は税金を含みます。", "example_romaji": "Ryoukin wa zeikin o fukumimasu.",
     "example_en": "The price includes tax.", "example_ru": "Цена включает налог."},
    {"word": "不満", "level": "N3", "romaji": "fuman", "en_meaning": "dissatisfaction", "ru_meaning": "недовольство",
     "example_jp": "彼は結果に不満です。", "example_romaji": "Kare wa kekka ni fuman desu.",
     "example_en": "He is dissatisfied with the result.", "example_ru": "Он недоволен результатом."},
    {"word": "普段", "level": "N3", "romaji": "fudan", "en_meaning": "usually / ordinarily", "ru_meaning": "обычно, обыкновенно",
     "example_jp": "普段は七時に起きます。", "example_romaji": "Fudan wa shichiji ni okimasu.",
     "example_en": "I usually get up at seven.", "example_ru": "Обычно я встаю в семь."},
    {"word": "外出", "level": "N3", "romaji": "gaishutsu", "en_meaning": "going out", "ru_meaning": "выход из дома",
     "example_jp": "今日は外出の予定があります。", "example_romaji": "Kyou wa gaishutsu no yotei ga arimasu.",
     "example_en": "I have plans to go out today.", "example_ru": "Сегодня у меня планы выйти из дома."},
    {"word": "現金", "level": "N3", "romaji": "genkin", "en_meaning": "cash", "ru_meaning": "наличные",
     "example_jp": "現金で払ってもいいですか。", "example_romaji": "Genkin de haratte mo ii desu ka.",
     "example_en": "May I pay in cash?", "example_ru": "Можно заплатить наличными?"},
    {"word": "限界", "level": "N3", "romaji": "genkai", "en_meaning": "limit", "ru_meaning": "предел, лимит",
     "example_jp": "体力の限界を感じます。", "example_romaji": "Tairyoku no genkai o kanjimasu.",
     "example_en": "I feel the limit of my stamina.", "example_ru": "Я чувствую предел своих сил."},
    {"word": "現実", "level": "N3", "romaji": "genjitsu", "en_meaning": "reality", "ru_meaning": "реальность",
     "example_jp": "夢と現実は違います。", "example_romaji": "Yume to genjitsu wa chigaimasu.",
     "example_en": "Dreams and reality are different.", "example_ru": "Мечты и реальность — разные вещи."},
    {"word": "義務", "level": "N3", "romaji": "gimu", "en_meaning": "duty / obligation", "ru_meaning": "обязанность, долг",
     "example_jp": "税金を払うのは義務です。", "example_romaji": "Zeikin o harau no wa gimu desu.",
     "example_en": "Paying taxes is an obligation.", "example_ru": "Платить налоги — обязанность."},
    {"word": "合格", "level": "N3", "romaji": "goukaku", "en_meaning": "passing (an exam)", "ru_meaning": "сдача экзамена, зачёт",
     "example_jp": "試験に合格しました。", "example_romaji": "Shiken ni goukaku shimashita.",
     "example_en": "I passed the exam.", "example_ru": "Я сдал экзамен."},
    {"word": "偶然", "level": "N3", "romaji": "guuzen", "en_meaning": "by chance / coincidence", "ru_meaning": "случайно, совпадение",
     "example_jp": "偶然彼に会いました。", "example_romaji": "Guuzen kare ni aimashita.",
     "example_en": "I met him by chance.", "example_ru": "Я случайно его встретил."},
    {"word": "判断", "level": "N3", "romaji": "handan", "en_meaning": "judgment / decision", "ru_meaning": "суждение, решение",
     "example_jp": "自分で判断してください。", "example_romaji": "Jibun de handan shite kudasai.",
     "example_en": "Please decide for yourself.", "example_ru": "Пожалуйста, решите сами."},
    {"word": "発表", "level": "N3", "romaji": "happyou", "en_meaning": "announcement / presentation", "ru_meaning": "объявление, презентация",
     "example_jp": "明日、結果を発表します。", "example_romaji": "Ashita, kekka o happyou shimasu.",
     "example_en": "We'll announce the results tomorrow.", "example_ru": "Завтра мы объявим результаты."},
    {"word": "発展", "level": "N3", "romaji": "hatten", "en_meaning": "development / growth", "ru_meaning": "развитие",
     "example_jp": "町が発展しています。", "example_romaji": "Machi ga hatten shite imasu.",
     "example_en": "The town is developing.", "example_ru": "Город развивается."},
    {"word": "非常", "level": "N3", "romaji": "hijou", "en_meaning": "emergency / extremely", "ru_meaning": "чрезвычайный, крайне",
     "example_jp": "非常に難しい問題です。", "example_romaji": "Hijou ni muzukashii mondai desu.",
     "example_en": "It's an extremely difficult problem.", "example_ru": "Это крайне сложная задача."},
    {"word": "秘密", "level": "N3", "romaji": "himitsu", "en_meaning": "secret", "ru_meaning": "секрет, тайна",
     "example_jp": "これは秘密にしてください。", "example_romaji": "Kore wa himitsu ni shite kudasai.",
     "example_en": "Please keep this a secret.", "example_ru": "Пожалуйста, держите это в секрете."},
    {"word": "表現", "level": "N3", "romaji": "hyougen", "en_meaning": "expression", "ru_meaning": "выражение",
     "example_jp": "この表現は自然です。", "example_romaji": "Kono hyougen wa shizen desu.",
     "example_en": "This expression sounds natural.", "example_ru": "Это выражение звучит естественно."},
    {"word": "位置", "level": "N3", "romaji": "ichi", "en_meaning": "position / location", "ru_meaning": "положение, местоположение",
     "example_jp": "机の位置を変えました。", "example_romaji": "Tsukue no ichi o kaemashita.",
     "example_en": "I changed the desk's position.", "example_ru": "Я поменял положение стола."},
    {"word": "以来", "level": "N3", "romaji": "irai", "en_meaning": "since", "ru_meaning": "с тех пор как",
     "example_jp": "去年以来、会っていません。", "example_romaji": "Kyonen irai, atte imasen.",
     "example_en": "I haven't seen him since last year.", "example_ru": "Я не виделся с ним с прошлого года."},
    {"word": "意識", "level": "N3", "romaji": "ishiki", "en_meaning": "consciousness / awareness", "ru_meaning": "сознание, осознание",
     "example_jp": "健康を意識しています。", "example_romaji": "Kenkou o ishiki shite imasu.",
     "example_en": "I'm conscious of my health.", "example_ru": "Я осознанно слежу за здоровьем."},
    {"word": "事実", "level": "N3", "romaji": "jijitsu", "en_meaning": "fact", "ru_meaning": "факт",
     "example_jp": "それは事実です。", "example_romaji": "Sore wa jijitsu desu.",
     "example_en": "That is a fact.", "example_ru": "Это факт."},
    {"word": "実際", "level": "N3", "romaji": "jissai", "en_meaning": "actually / in reality", "ru_meaning": "на самом деле, фактически",
     "example_jp": "実際にやってみましょう。", "example_romaji": "Jissai ni yatte mimashou.",
     "example_en": "Let's actually try it.", "example_ru": "Давайте попробуем на практике."},
    {"word": "情報", "level": "N3", "romaji": "jouhou", "en_meaning": "information", "ru_meaning": "информация",
     "example_jp": "新しい情報が必要です。", "example_romaji": "Atarashii jouhou ga hitsuyou desu.",
     "example_en": "We need new information.", "example_ru": "Нам нужна новая информация."},
    {"word": "条件", "level": "N3", "romaji": "jouken", "en_meaning": "condition / terms", "ru_meaning": "условие",
     "example_jp": "条件を確認してください。", "example_romaji": "Jouken o kakunin shite kudasai.",
     "example_en": "Please check the conditions.", "example_ru": "Пожалуйста, проверьте условия."},
    {"word": "状態", "level": "N3", "romaji": "joutai", "en_meaning": "condition / state", "ru_meaning": "состояние",
     "example_jp": "機械の状態を調べます。", "example_romaji": "Kikai no joutai o shirabemasu.",
     "example_en": "I'll check the machine's condition.", "example_ru": "Я проверю состояние машины."},
    {"word": "重要", "level": "N3", "romaji": "juuyou", "en_meaning": "important / essential", "ru_meaning": "важный",
     "example_jp": "これは重要な問題です。", "example_romaji": "Kore wa juuyou na mondai desu.",
     "example_en": "This is an important issue.", "example_ru": "Это важный вопрос."},
    {"word": "価値", "level": "N3", "romaji": "kachi", "en_meaning": "value / worth", "ru_meaning": "ценность, стоимость",
     "example_jp": "この本は読む価値があります。", "example_romaji": "Kono hon wa yomu kachi ga arimasu.",
     "example_en": "This book is worth reading.", "example_ru": "Эту книгу стоит прочитать."},
    {"word": "解決", "level": "N3", "romaji": "kaiketsu", "en_meaning": "solution / settlement", "ru_meaning": "решение (проблемы)",
     "example_jp": "問題を解決しました。", "example_romaji": "Mondai o kaiketsu shimashita.",
     "example_en": "I solved the problem.", "example_ru": "Я решил проблему."},
    {"word": "改善", "level": "N3", "romaji": "kaizen", "en_meaning": "improvement", "ru_meaning": "улучшение",
     "example_jp": "サービスを改善します。", "example_romaji": "Saabisu o kaizen shimasu.",
     "example_en": "We will improve the service.", "example_ru": "Мы улучшим сервис."},
    {"word": "確認", "level": "N3", "romaji": "kakunin", "en_meaning": "confirmation", "ru_meaning": "подтверждение, проверка",
     "example_jp": "予約を確認してください。", "example_romaji": "Yoyaku o kakunin shite kudasai.",
     "example_en": "Please confirm the reservation.", "example_ru": "Пожалуйста, подтвердите бронь."},
    {"word": "環境", "level": "N3", "romaji": "kankyou", "en_meaning": "environment", "ru_meaning": "окружающая среда, обстановка",
     "example_jp": "働く環境が大切です。", "example_romaji": "Hataraku kankyou ga taisetsu desu.",
     "example_en": "The work environment is important.", "example_ru": "Рабочая обстановка важна."},
    {"word": "結果", "level": "N3", "romaji": "kekka", "en_meaning": "result", "ru_meaning": "результат",
     "example_jp": "試験の結果が出ました。", "example_romaji": "Shiken no kekka ga demashita.",
     "example_en": "The exam results are out.", "example_ru": "Результаты экзамена вышли."},
    {"word": "経営", "level": "N3", "romaji": "keiei", "en_meaning": "management", "ru_meaning": "управление, менеджмент",
     "example_jp": "彼は会社を経営しています。", "example_romaji": "Kare wa kaisha o keiei shite imasu.",
     "example_en": "He manages a company.", "example_ru": "Он управляет компанией."},
]


def main():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("SELECT word FROM words")
    existing = {row[0] for row in cur.fetchall()}

    inserted = skipped = 0
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

    cur.execute("SELECT level, COUNT(*) FROM words GROUP BY level ORDER BY level DESC")
    print(f"✅ Inserted {inserted} N3 words, skipped {skipped} already present.")
    print("Current word counts:")
    for level, n in cur.fetchall():
        print(f"   {level}: {n}")
    conn.close()


if __name__ == "__main__":
    main()
