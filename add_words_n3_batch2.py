"""
Adds a second batch of 60 JLPT N3 words to japanese_bot.db.

Kanji and readings come from japanesetest4you.com's JLPT N3 vocabulary
list; example sentences and Russian translations were written to match.
Checked against add_words_n3.py so nothing overlaps.

Run on the VPS, in the bot's folder, with the venv active:

    source venv/bin/activate
    python3 add_words_n3_batch2.py

Idempotent — already-present words are skipped, so re-running is safe.

After running it, refresh the audio cache and the git-tracked seed file:

    python3 prewarm_audio.py <your_telegram_id>
    python3 export_words.py && git add words_seed.json && git commit -m "More N3 words"
"""
import sqlite3

DB_NAME = 'japanese_bot.db'

NEW_WORDS = [
    {"word": "安心", "level": "N3", "romaji": "anshin", "en_meaning": "relief / peace of mind", "ru_meaning": "спокойствие, облегчение",
     "example_jp": "無事だと聞いて安心しました。", "example_romaji": "Buji da to kiite anshin shimashita.",
     "example_en": "I was relieved to hear you're safe.", "example_ru": "Я успокоился, узнав, что всё в порядке."},
    {"word": "案内", "level": "N3", "romaji": "annai", "en_meaning": "guidance / showing around", "ru_meaning": "сопровождение, экскурсия",
     "example_jp": "町を案内しましょうか。", "example_romaji": "Machi o annai shimashou ka.",
     "example_en": "Shall I show you around the town?", "example_ru": "Показать вам город?"},
    {"word": "以上", "level": "N3", "romaji": "ijou", "en_meaning": "more than / above", "ru_meaning": "более, свыше",
     "example_jp": "十人以上集まりました。", "example_romaji": "Juunin ijou atsumarimashita.",
     "example_en": "More than ten people gathered.", "example_ru": "Собралось более десяти человек."},
    {"word": "以内", "level": "N3", "romaji": "inai", "en_meaning": "within", "ru_meaning": "в пределах",
     "example_jp": "一週間以内に返事をください。", "example_romaji": "Isshuukan inai ni henji o kudasai.",
     "example_en": "Please reply within a week.", "example_ru": "Ответьте, пожалуйста, в течение недели."},
    {"word": "異常", "level": "N3", "romaji": "ijou", "en_meaning": "abnormality", "ru_meaning": "аномалия, отклонение",
     "example_jp": "機械に異常はありません。", "example_romaji": "Kikai ni ijou wa arimasen.",
     "example_en": "There's nothing wrong with the machine.", "example_ru": "С машиной всё в порядке."},
    {"word": "一般", "level": "N3", "romaji": "ippan", "en_meaning": "general / ordinary", "ru_meaning": "общий, обычный",
     "example_jp": "一般的な意見です。", "example_romaji": "Ippanteki na iken desu.",
     "example_en": "It's a general opinion.", "example_ru": "Это распространённое мнение."},
    {"word": "一方", "level": "N3", "romaji": "ippou", "en_meaning": "one side / on the other hand", "ru_meaning": "с одной стороны, тем временем",
     "example_jp": "一方、彼は反対しました。", "example_romaji": "Ippou, kare wa hantai shimashita.",
     "example_en": "On the other hand, he objected.", "example_ru": "С другой стороны, он возражал."},
    {"word": "移動", "level": "N3", "romaji": "idou", "en_meaning": "movement / transfer", "ru_meaning": "перемещение, переезд",
     "example_jp": "バスで移動します。", "example_romaji": "Basu de idou shimasu.",
     "example_en": "We'll travel by bus.", "example_ru": "Мы поедем на автобусе."},
    {"word": "印象", "level": "N3", "romaji": "inshou", "en_meaning": "impression", "ru_meaning": "впечатление",
     "example_jp": "彼の印象はよかったです。", "example_romaji": "Kare no inshou wa yokatta desu.",
     "example_en": "He made a good impression.", "example_ru": "Он произвёл хорошее впечатление."},
    {"word": "宇宙", "level": "N3", "romaji": "uchuu", "en_meaning": "universe / space", "ru_meaning": "космос, вселенная",
     "example_jp": "宇宙に興味があります。", "example_romaji": "Uchuu ni kyoumi ga arimasu.",
     "example_en": "I'm interested in space.", "example_ru": "Я интересуюсь космосом."},
    {"word": "応援", "level": "N3", "romaji": "ouen", "en_meaning": "support / cheering", "ru_meaning": "поддержка, болеть за",
     "example_jp": "チームを応援しています。", "example_romaji": "Chiimu o ouen shite imasu.",
     "example_en": "I'm rooting for the team.", "example_ru": "Я болею за команду."},
    {"word": "行う", "level": "N3", "romaji": "okonau", "en_meaning": "to carry out / to conduct", "ru_meaning": "проводить, осуществлять",
     "example_jp": "会議を行います。", "example_romaji": "Kaigi o okonaimasu.",
     "example_en": "We will hold a meeting.", "example_ru": "Мы проведём совещание."},
    {"word": "驚く", "level": "N3", "romaji": "odoroku", "en_meaning": "to be surprised", "ru_meaning": "удивляться",
     "example_jp": "その知らせに驚きました。", "example_romaji": "Sono shirase ni odorokimashita.",
     "example_en": "I was surprised by the news.", "example_ru": "Я удивился этой новости."},
    {"word": "過去", "level": "N3", "romaji": "kako", "en_meaning": "the past", "ru_meaning": "прошлое",
     "example_jp": "過去のことは忘れましょう。", "example_romaji": "Kako no koto wa wasuremashou.",
     "example_en": "Let's forget the past.", "example_ru": "Давайте забудем прошлое."},
    {"word": "活動", "level": "N3", "romaji": "katsudou", "en_meaning": "activity", "ru_meaning": "деятельность, активность",
     "example_jp": "クラブの活動に参加します。", "example_romaji": "Kurabu no katsudou ni sanka shimasu.",
     "example_en": "I take part in club activities.", "example_ru": "Я участвую в клубной деятельности."},
    {"word": "必ず", "level": "N3", "romaji": "kanarazu", "en_meaning": "certainly / without fail", "ru_meaning": "обязательно, непременно",
     "example_jp": "必ず連絡します。", "example_romaji": "Kanarazu renraku shimasu.",
     "example_en": "I'll definitely get in touch.", "example_ru": "Я обязательно свяжусь."},
    {"word": "我慢", "level": "N3", "romaji": "gaman", "en_meaning": "patience / endurance", "ru_meaning": "терпение, выдержка",
     "example_jp": "もう少し我慢してください。", "example_romaji": "Mou sukoshi gaman shite kudasai.",
     "example_en": "Please be patient a little longer.", "example_ru": "Потерпите ещё немного."},
    {"word": "完全", "level": "N3", "romaji": "kanzen", "en_meaning": "complete / perfect", "ru_meaning": "полный, совершенный",
     "example_jp": "完全に忘れていました。", "example_romaji": "Kanzen ni wasurete imashita.",
     "example_en": "I completely forgot.", "example_ru": "Я совершенно забыл."},
    {"word": "関係", "level": "N3", "romaji": "kankei", "en_meaning": "relation / connection", "ru_meaning": "отношение, связь",
     "example_jp": "二人の関係はいいです。", "example_romaji": "Futari no kankei wa ii desu.",
     "example_en": "The two of them get along well.", "example_ru": "У них хорошие отношения."},
    {"word": "記憶", "level": "N3", "romaji": "kioku", "en_meaning": "memory / recollection", "ru_meaning": "память, воспоминание",
     "example_jp": "子供の頃の記憶があります。", "example_romaji": "Kodomo no koro no kioku ga arimasu.",
     "example_en": "I have memories of my childhood.", "example_ru": "У меня есть воспоминания о детстве."},
    {"word": "季節", "level": "N3", "romaji": "kisetsu", "en_meaning": "season", "ru_meaning": "время года, сезон",
     "example_jp": "好きな季節は秋です。", "example_romaji": "Sukina kisetsu wa aki desu.",
     "example_en": "My favorite season is autumn.", "example_ru": "Моё любимое время года — осень."},
    {"word": "気温", "level": "N3", "romaji": "kion", "en_meaning": "air temperature", "ru_meaning": "температура воздуха",
     "example_jp": "今日は気温が低いです。", "example_romaji": "Kyou wa kion ga hikui desu.",
     "example_en": "The temperature is low today.", "example_ru": "Сегодня низкая температура."},
    {"word": "機会", "level": "N3", "romaji": "kikai", "en_meaning": "opportunity / chance", "ru_meaning": "возможность, случай",
     "example_jp": "いい機会だと思います。", "example_romaji": "Ii kikai da to omoimasu.",
     "example_en": "I think it's a good opportunity.", "example_ru": "Думаю, это хорошая возможность."},
    {"word": "希望", "level": "N3", "romaji": "kibou", "en_meaning": "hope / wish", "ru_meaning": "надежда, желание",
     "example_jp": "希望を持ちましょう。", "example_romaji": "Kibou o mochimashou.",
     "example_en": "Let's keep hope.", "example_ru": "Давайте сохранять надежду."},
    {"word": "規則", "level": "N3", "romaji": "kisoku", "en_meaning": "rule / regulation", "ru_meaning": "правило, устав",
     "example_jp": "会社の規則を守ります。", "example_romaji": "Kaisha no kisoku o mamorimasu.",
     "example_en": "I follow the company rules.", "example_ru": "Я соблюдаю правила компании."},
    {"word": "基本", "level": "N3", "romaji": "kihon", "en_meaning": "basis / fundamentals", "ru_meaning": "основа, база",
     "example_jp": "基本から勉強します。", "example_romaji": "Kihon kara benkyou shimasu.",
     "example_en": "I'll study from the basics.", "example_ru": "Я буду учиться с основ."},
    {"word": "決して", "level": "N3", "romaji": "kesshite", "en_meaning": "never (with negative)", "ru_meaning": "никогда, ни за что",
     "example_jp": "決して忘れません。", "example_romaji": "Kesshite wasuremasen.",
     "example_en": "I will never forget.", "example_ru": "Я никогда не забуду."},
    {"word": "権利", "level": "N3", "romaji": "kenri", "en_meaning": "right / privilege", "ru_meaning": "право",
     "example_jp": "それは私の権利です。", "example_romaji": "Sore wa watashi no kenri desu.",
     "example_en": "That is my right.", "example_ru": "Это моё право."},
    {"word": "原因", "level": "N3", "romaji": "genin", "en_meaning": "cause", "ru_meaning": "причина",
     "example_jp": "事故の原因を調べます。", "example_romaji": "Jiko no genin o shirabemasu.",
     "example_en": "We'll investigate the cause of the accident.", "example_ru": "Мы выясним причину аварии."},
    {"word": "現在", "level": "N3", "romaji": "genzai", "en_meaning": "now / at present", "ru_meaning": "сейчас, в настоящее время",
     "example_jp": "現在、東京に住んでいます。", "example_romaji": "Genzai, Toukyou ni sunde imasu.",
     "example_en": "I currently live in Tokyo.", "example_ru": "Сейчас я живу в Токио."},
    {"word": "効果", "level": "N3", "romaji": "kouka", "en_meaning": "effect / effectiveness", "ru_meaning": "эффект, действие",
     "example_jp": "この薬は効果があります。", "example_romaji": "Kono kusuri wa kouka ga arimasu.",
     "example_en": "This medicine is effective.", "example_ru": "Это лекарство действует."},
    {"word": "交換", "level": "N3", "romaji": "koukan", "en_meaning": "exchange", "ru_meaning": "обмен, замена",
     "example_jp": "部品を交換しました。", "example_romaji": "Buhin o koukan shimashita.",
     "example_en": "I replaced the part.", "example_ru": "Я заменил деталь."},
    {"word": "行動", "level": "N3", "romaji": "koudou", "en_meaning": "action / behaviour", "ru_meaning": "поведение, действие",
     "example_jp": "早く行動しましょう。", "example_romaji": "Hayaku koudou shimashou.",
     "example_en": "Let's act quickly.", "example_ru": "Давайте действовать быстро."},
    {"word": "幸福", "level": "N3", "romaji": "koufuku", "en_meaning": "happiness", "ru_meaning": "счастье",
     "example_jp": "幸福な家庭を作りたいです。", "example_romaji": "Koufuku na katei o tsukuritai desu.",
     "example_en": "I want to build a happy family.", "example_ru": "Я хочу построить счастливую семью."},
    {"word": "国際", "level": "N3", "romaji": "kokusai", "en_meaning": "international", "ru_meaning": "международный",
     "example_jp": "国際会議に出ます。", "example_romaji": "Kokusai kaigi ni demasu.",
     "example_en": "I'll attend an international conference.", "example_ru": "Я поеду на международную конференцию."},
    {"word": "混雑", "level": "N3", "romaji": "konzatsu", "en_meaning": "congestion / crowding", "ru_meaning": "толчея, давка",
     "example_jp": "朝の電車は混雑します。", "example_romaji": "Asa no densha wa konzatsu shimasu.",
     "example_en": "Morning trains get crowded.", "example_ru": "Утренние поезда переполнены."},
    {"word": "最近", "level": "N3", "romaji": "saikin", "en_meaning": "recently", "ru_meaning": "недавно, в последнее время",
     "example_jp": "最近、忙しいです。", "example_romaji": "Saikin, isogashii desu.",
     "example_en": "I've been busy recently.", "example_ru": "В последнее время я занят."},
    {"word": "再び", "level": "N3", "romaji": "futatabi", "en_meaning": "again / once more", "ru_meaning": "вновь, снова",
     "example_jp": "再び挑戦します。", "example_romaji": "Futatabi chousen shimasu.",
     "example_en": "I'll try again.", "example_ru": "Я попробую снова."},
    {"word": "作成", "level": "N3", "romaji": "sakusei", "en_meaning": "creation / drawing up", "ru_meaning": "составление, создание",
     "example_jp": "書類を作成しました。", "example_romaji": "Shorui o sakusei shimashita.",
     "example_en": "I drew up the documents.", "example_ru": "Я составил документы."},
    {"word": "参加", "level": "N3", "romaji": "sanka", "en_meaning": "participation", "ru_meaning": "участие",
     "example_jp": "大会に参加します。", "example_romaji": "Taikai ni sanka shimasu.",
     "example_en": "I'll take part in the tournament.", "example_ru": "Я приму участие в турнире."},
    {"word": "賛成", "level": "N3", "romaji": "sansei", "en_meaning": "approval / agreement", "ru_meaning": "согласие, одобрение",
     "example_jp": "その案に賛成です。", "example_romaji": "Sono an ni sansei desu.",
     "example_en": "I agree with that proposal.", "example_ru": "Я согласен с этим предложением."},
    {"word": "支持", "level": "N3", "romaji": "shiji", "en_meaning": "support / backing", "ru_meaning": "поддержка",
     "example_jp": "その意見を支持します。", "example_romaji": "Sono iken o shiji shimasu.",
     "example_en": "I support that opinion.", "example_ru": "Я поддерживаю это мнение."},
    {"word": "姿勢", "level": "N3", "romaji": "shisei", "en_meaning": "posture / attitude", "ru_meaning": "поза, позиция",
     "example_jp": "姿勢をよくしましょう。", "example_romaji": "Shisei o yoku shimashou.",
     "example_en": "Let's improve our posture.", "example_ru": "Давайте выпрямим спину."},
    {"word": "実力", "level": "N3", "romaji": "jitsuryoku", "en_meaning": "real ability", "ru_meaning": "реальные способности",
     "example_jp": "実力を見せてください。", "example_romaji": "Jitsuryoku o misete kudasai.",
     "example_en": "Please show your true ability.", "example_ru": "Покажите, на что вы способны."},
    {"word": "習慣", "level": "N3", "romaji": "shuukan", "en_meaning": "habit / custom", "ru_meaning": "привычка, обычай",
     "example_jp": "早起きの習慣をつけます。", "example_romaji": "Hayaoki no shuukan o tsukemasu.",
     "example_en": "I'm building a habit of waking up early.", "example_ru": "Я вырабатываю привычку рано вставать."},
    {"word": "順番", "level": "N3", "romaji": "junban", "en_meaning": "order / turn", "ru_meaning": "очередь, порядок",
     "example_jp": "順番を守ってください。", "example_romaji": "Junban o mamotte kudasai.",
     "example_en": "Please wait your turn.", "example_ru": "Соблюдайте очередь, пожалуйста."},
    {"word": "準備", "level": "N3", "romaji": "junbi", "en_meaning": "preparation", "ru_meaning": "подготовка",
     "example_jp": "旅行の準備をします。", "example_romaji": "Ryokou no junbi o shimasu.",
     "example_en": "I'll prepare for the trip.", "example_ru": "Я подготовлюсь к поездке."},
    {"word": "状況", "level": "N3", "romaji": "joukyou", "en_meaning": "situation / circumstances", "ru_meaning": "ситуация, обстановка",
     "example_jp": "状況を説明してください。", "example_romaji": "Joukyou o setsumei shite kudasai.",
     "example_en": "Please explain the situation.", "example_ru": "Объясните, пожалуйста, ситуацию."},
    {"word": "生活", "level": "N3", "romaji": "seikatsu", "en_meaning": "life / living", "ru_meaning": "жизнь, быт",
     "example_jp": "新しい生活が始まります。", "example_romaji": "Atarashii seikatsu ga hajimarimasu.",
     "example_en": "A new life begins.", "example_ru": "Начинается новая жизнь."},
    {"word": "成功", "level": "N3", "romaji": "seikou", "en_meaning": "success", "ru_meaning": "успех",
     "example_jp": "実験は成功しました。", "example_romaji": "Jikken wa seikou shimashita.",
     "example_en": "The experiment succeeded.", "example_ru": "Эксперимент удался."},
    {"word": "性格", "level": "N3", "romaji": "seikaku", "en_meaning": "character / personality", "ru_meaning": "характер",
     "example_jp": "彼は明るい性格です。", "example_romaji": "Kare wa akarui seikaku desu.",
     "example_en": "He has a cheerful personality.", "example_ru": "У него весёлый характер."},
    {"word": "責任", "level": "N3", "romaji": "sekinin", "en_meaning": "responsibility", "ru_meaning": "ответственность",
     "example_jp": "責任を持って仕事をします。", "example_romaji": "Sekinin o motte shigoto o shimasu.",
     "example_en": "I work responsibly.", "example_ru": "Я работаю ответственно."},
    {"word": "説明", "level": "N3", "romaji": "setsumei", "en_meaning": "explanation", "ru_meaning": "объяснение",
     "example_jp": "もう一度説明してください。", "example_romaji": "Mou ichido setsumei shite kudasai.",
     "example_en": "Please explain once more.", "example_ru": "Объясните ещё раз, пожалуйста."},
    {"word": "相談", "level": "N3", "romaji": "soudan", "en_meaning": "consultation / discussion", "ru_meaning": "консультация, совет",
     "example_jp": "先生に相談しました。", "example_romaji": "Sensei ni soudan shimashita.",
     "example_en": "I consulted my teacher.", "example_ru": "Я посоветовался с учителем."},
    {"word": "存在", "level": "N3", "romaji": "sonzai", "en_meaning": "existence", "ru_meaning": "существование",
     "example_jp": "その問題の存在を知りませんでした。", "example_romaji": "Sono mondai no sonzai o shirimasen deshita.",
     "example_en": "I didn't know that problem existed.", "example_ru": "Я не знал о существовании этой проблемы."},
    {"word": "態度", "level": "N3", "romaji": "taido", "en_meaning": "attitude / manner", "ru_meaning": "отношение, манера",
     "example_jp": "彼の態度は失礼です。", "example_romaji": "Kare no taido wa shitsurei desu.",
     "example_en": "His attitude is rude.", "example_ru": "Его поведение невежливо."},
    {"word": "確かめる", "level": "N3", "romaji": "tashikameru", "en_meaning": "to make sure / to verify", "ru_meaning": "убедиться, проверить",
     "example_jp": "住所を確かめてください。", "example_romaji": "Juusho o tashikamete kudasai.",
     "example_en": "Please verify the address.", "example_ru": "Проверьте, пожалуйста, адрес."},
    {"word": "提案", "level": "N3", "romaji": "teian", "en_meaning": "proposal / suggestion", "ru_meaning": "предложение",
     "example_jp": "新しい提案があります。", "example_romaji": "Atarashii teian ga arimasu.",
     "example_en": "I have a new proposal.", "example_ru": "У меня есть новое предложение."},
    {"word": "内容", "level": "N3", "romaji": "naiyou", "en_meaning": "contents", "ru_meaning": "содержание",
     "example_jp": "手紙の内容を教えてください。", "example_romaji": "Tegami no naiyou o oshiete kudasai.",
     "example_en": "Please tell me the contents of the letter.", "example_ru": "Расскажите содержание письма."},
    {"word": "納得", "level": "N3", "romaji": "nattoku", "en_meaning": "understanding / being convinced", "ru_meaning": "согласие, понимание",
     "example_jp": "説明に納得しました。", "example_romaji": "Setsumei ni nattoku shimashita.",
     "example_en": "I was convinced by the explanation.", "example_ru": "Объяснение меня убедило."},
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
