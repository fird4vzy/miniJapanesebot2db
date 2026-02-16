import sqlite3

# Batch 10: Formal Actions & States of Being
n4_batch_10 = [
    # --- Polite & Formal Actions (Keigo Basics) ---
    ("召し上がる", "N4", "Meshiagaru", "To eat/drink (honorific)", "Кушать/пить (вежливо)",
     "どうぞ、温かいうちに召し上がってください。", "Douzo, atatakai uchi ni meshiagatte kudasai.",
     "Please eat while it is still warm.", "Пожалуйста, кушайте, пока не остыло."),

    ("おっしゃる", "N4", "Ossharu", "To say (honorific)", "Говорить (вежливо)",
     "先生がおっしゃったことを覚えていますか。", "Sensei ga osshatta koto o oboete imasu ka.",
     "Do you remember what the teacher said?", "Вы помните, что сказал учитель?"),

    ("下さる", "N4", "Kudasaru", "To give (to me - honorific)", "Давать (мне/нам - вежливо)",
     "先生がこの本をくださいました。", "Sensei ga kono hon o kudasaimashita.",
     "The teacher gave me this book.", "Учитель дал мне эту книгу."),

    ("参る", "N4", "Mairu", "To go/come (humble)", "Идти/приходить (скромно)",
     "ただいま参りますので、少々お待ちください。", "Tadaima mairimasu node, shouhou omachi kudasai.",
     "I am coming now, so please wait a moment.", "Я сейчас приду, пожалуйста, подождите немного."),

    # --- Quantities & Sufficiency ---
    ("足りる", "N4", "Tariru", "To be sufficient/enough", "Хватать/быть достаточным",
     "時間が足りなくて、全部書けませんでした。", "Jikan ga tarinakute, zenbu kakemasendeshita.",
     "I didn't have enough time, so I couldn't write everything.",
     "Мне не хватило времени, поэтому я не смог написать всё."),

    ("適当", "N4", "Tekitou", "Suitable/Appropriate", "Подходящий",
     "適当な言葉が見つかりません。", "Tekitou na kotoba ga mitsukarimasen.",
     "I can't find the appropriate words.", "Я не могу найти подходящих слов."),

    ("半分", "N4", "Hanbun", "Half", "Половина",
     "リンゴを半分に切ってください。", "Ringo o hanbun ni kitte kudasai.",
     "Please cut the apple in half.", "Пожалуйста, разрежьте яблоко пополам."),

    # --- Social Situations ---
    ("混む", "N4", "Komu", "To be crowded", "Быть людным/переполненным",
     "日曜日のデパートはとても混んでいます。", "Nichiyoubi no depaato wa totemo konde imasu.",
     "The department store is very crowded on Sundays.", "В воскресенье в универмаге очень многолюдно."),

    ("間に合う", "N4", "Maniau", "To be in time for", "Успевать",
     "走れば、電車に間に合いますよ。", "Hashireba, densha ni maniaimasu yo.",
     "If you run, you will make it in time for the train.", "Если побежишь, успеешь на поезд."),

    ("寄る", "N4", "Yoru", "To stop by/drop in", "Заходить/заезжать (по пути)",
     "帰りにスーパーに寄って帰ります。", "Kaeri ni suupaa ni yotte kaerimasu.",
     "I will stop by the supermarket on my way home.", "На обратном пути я зайду в супермаркет."),

    # --- Abstract & Useful Phrases ---
    ("お見舞い", "N4", "Omimai", "Visiting someone who is ill", "Посещение больного",
     "友達のお見舞いに行きました。", "Tomodachi no omimai ni ikimashita.",
     "I went to visit my sick friend.", "Я пошел навестить больного друга."),

    ("おかげ", "N4", "Okage", "Thanks to...", "Благодаря...",
     "先生のおかげで試験に合格しました。", "Sensei no okage de shiken ni goukaku shimashita.",
     "Thanks to the teacher, I passed the exam.", "Благодаря учителю я сдал экзамен."),

    ("せい", "N4", "Sei", "Because of/Fault of...", "Из-за... (вина)",
     "雨のせいでピクニックが中止になりました。", "Ame no sei de pikunikku ga chuushi ni narimashita.",
     "Because of the rain, the picnic was cancelled.", "Из-за дождя пикник отменили."),

    # --- Work & Effort ---
    ("勤める", "N4", "Tsutomeru", "To work for/be employed at", "Служить/работать (в фирме)",
     "父は銀行に勤めています。", "Chichi wa ginkou ni tsutomete imasu.",
     "My father works for a bank.", "Мой отец работает в банке."),

    ("稼ぐ", "N4", "Kasegu", "To earn income", "Зарабатывать",
     "自分でお金を稼ぐのは大変です。", "Jibun de okane o kasegu no wa taihen desu.",
     "It is hard to earn money on your own.", "Зарабатывать деньги самому трудно."),

    # --- Objects & Materials ---
    ("道具", "N4", "Dougu", "Tool/Instrument", "Инструмент",
     "料理の道具を片付けました。", "Ryouri no dougu o katazukemashita.",
     "I tidied up the cooking tools.", "Я убрал кухонные принадлежности."),

    ("材料", "N4", "Zairyou", "Ingredients/Materials", "Ингредиенты/материалы",
     "カレーの材料を買いに行きます。", "Karee no zairyou o kai ni ikimasu.",
     "I am going to buy ingredients for curry.", "Я иду покупать ингредиенты для карри."),

    ("品物", "N4", "Shinamono", "Goods/Article", "Товар/вещь",
     "この店にはいい品物がたくさんあります。", "Kono mise ni wa ii shinamono ga takusan arimasu.",
     "This store has many good items.", "В этом магазине много хороших товаров."),

    # --- Final N4 Verbs ---
    ("代わる", "N4", "Kawaru", "To take the place of", "Сменять/замещать",
     "病気の先生の代わりに田中先生が来ました。", "Byouki no sensei no kawari ni Tanaka-sensei ga kimashita.",
     "Tanaka-sensei came instead of the sick teacher.", "Вместо заболевшего учителя пришел учитель Танака."),

    ("伺う", "N4", "Ukagau", "To visit/ask (humble)", "Посещать/спрашивать (скромно)",
     "明日、お宅に伺ってもよろしいですか。", "Ashita, otaku ni ukagau mo yoroshii desu ka.",
     "May I visit your home tomorrow?", "Можно мне завтра прийти к вам домой?")
]


def add_n4_batch_10():
    try:
        conn = sqlite3.connect('japanese_bot.db')
        cursor = conn.cursor()
        cursor.executemany('''
            INSERT OR REPLACE INTO words 
            (word, level, romaji, en_meaning, ru_meaning, example_jp, example_romaji, example_en, example_ru)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', n4_batch_10)
        conn.commit()
        print(f"🎉 Batch #10 Loaded! You have reached 200 words for N4.")
        conn.close()
    except sqlite3.Error as e:
        print(f"❌ DB Error: {e}")


if __name__ == "__main__":
    add_n4_batch_10()