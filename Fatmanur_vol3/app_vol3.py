from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
# Silinecekler: requests, os
# Eklenecek: Yeni öneri fonksiyonumuz
from recommendations_logic_vol2 import get_recommendations_with_weighted_scoring

app = Flask(__name__)

# app_vol3.py dosyanızda, app = Flask(__name__) satırından sonrasını bununla değiştirin.

# --- YENİ YAPILANDIRMA AYARLARI ---
app.config['SECRET_KEY'] = 'aa7ffa4de0568769a725c004f7f84bf1'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///book_app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- UYGULAMA EKLENTİLERİNİ BAŞLATMA ---
# Önce 'db' değişkenini oluşturuyoruz.
db = SQLAlchemy(app)

# Sonra Login Yöneticisini başlatıyoruz.
login_manager = LoginManager(app)
login_manager.login_view = 'login'


# --- VERİTABANI MODELLERİNİ OLUŞTURMA ---
# 'db' değişkeni artık tanımlı olduğu için, bu sınıflar sorunsuz oluşturulabilir.
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    saved_books = db.relationship('SavedBook', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class SavedBook(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    book_api_id = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(200))
    status = db.Column(db.String(50), default='want_to_read')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


# --- KULLANICI YÜKLEYİCİ FONKSİYONU ---
# Bu fonksiyon, Flask-Login'in kullanıcıları nasıl yöneteceğini bilmesi için gereklidir.
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

#
# Buradan sonra quiz_questions, READER_TYPE_INFO ve diğer Flask rotalarınız (@app.route...) gelir.


# quiz_questions listesi burada olduğu gibi kalacak...
quiz_questions = [
    {
        "id": 1,
        "question": "When you walk into a bookstore, which section do you head to first?",
        "options": [
            {"label": "a) Bestseller shelf / What's Hot",
             "types": ["the chill guy", "the plot pilot", "the growth guru", "the jack of all trades", "the yearner"]},
            {"label": "b) My favorite genres (Sci-Fi, Romance, History, etc.)",
             "types": ["melancholic ruminator", "the tale whisperer", "the geeky chap", "the history nerd",
                       "the hopeless romantic", "the leering diva", "the reverie", "the deducer dudette",
                       "the thriller seeker"]},
            {"label": "c) I seek to learn and gain knowledge",
             "types": ["the contemplator", "the literature sage", "the joyful activist", "the growth guru",
                       "the jack of all trades", "the workaholic", "the geeky chap", "the history nerd"]},
            {"label": "d) I browse a bit of everything!", "types": ["the jack of all trades", "the growth guru"]},
            {"label": "e) Hidden gems, not-so-pop titles",
             "types": ["melancholic ruminator", "the literature sage", "the tale whisperer", "the teagan"]},
        ]
    },
    {
        "id": 2,
        "question": "The ideal ending to a book for you is:",
        "options": [
            {"label": "a) One that neatly ties up all loose ends.",
             "types": ["the hopeless romantic", "the deducer dudette", "the plot pilot"]},
            {"label": "b) One that makes me think for days.",
             "types": ["the contemplator", "the teagan", "melancholic ruminator", "the literature sage"]},
            {"label": "c) One that leaves me feeling emotionally satisfied.",
             "types": ["the hopeless romantic", "the leering diva", "the yearner"]},
            {"label": "d) One with a shocking twist I didn't see coming!",
             "types": ["the thriller seeker", "the deducer dudette", "the plot pilot", "the reverie"]},
            {"label": "e) One that provides a thorough analysis of the events/topic from a historical perspective.",
             "types": ["the history nerd"]},
        ]
    },
    {
        "id": 3,
        "question": "If you could have dinner with any author (living or dead), who would you choose and why?",
        "options": [
            {"label": "a) Someone who created an incredible world I'd love to know more about.",
             "types": ["the tale whisperer", "the reverie", "the plot pilot", "the geeky chap", "the history nerd"]},
            {"label": "b) Someone whose ideas have profoundly impacted me.",
             "types": ["the contemplator", "melancholic ruminator", "the literature sage", "the teagan",
                       "the growth guru", "the joyful activist", "the workaholic"]},
            {"label": "c) Someone whose characters feel like real people, and relatable.",
             "types": ["melancholic ruminator", "the literature sage", "the hopeless romantic", "the tale whisperer"]},
            {"label": "d) Someone known for their witty storytelling.",
             "types": ["the literature sage", "the geeky chap", "the deducer dudette"]},
        ]
    },
    {
        "id": 4,
        "question": "Do you take notes or highlight when you read?",
        "options": [
            {"label": "a) Never, it disrupts the flow.",
             "types": ["the plot pilot", "the tale whisperer", "the reverie", "the thriller seeker",
                       "the leering diva"]},
            {"label": "b) Sometimes, for memorable quotes or important info.",
             "types": ["the chill guy", "the workaholic", "the hopeless romantic", "the jack of all trades",
                       "the yearner", "the growth guru"]},
            {"label": "c) Yes, especially for non-fiction or complex novels.",
             "types": ["the geeky chap", "the deducer dudette", "the joyful activist", "the history nerd"]},
            {"label": "d) Yes, always to organize my thoughts.",
             "types": ["melancholic ruminator", "the literature sage", "the contemplator", "the history nerd"]},
        ]
    },
    {
        "id": 5,
        "question": "Long series or standalone novels?",
        "options": [
            {"label": "a) Long series – I love to stay in a world for a while.",
             "types": ["the geeky chap", "the tale whisperer", "the plot pilot", "the reverie", "the yearner"]},
            {"label": "b) Standalone – I like a complete story in one go.",
             "types": ["the teagan", "the workaholic", "the jack of all trades"]},
            {"label": "c) No preference.", "types": []},
        ]
    },
    {
        "id": 6,
        "question": "Plot or Characters: Which is more crucial for your enjoyment?",
        "options": [
            {"label": "a) Plot – I need a compelling story.",
             "types": ["the plot pilot", "the deducer dudette", "the tale whisperer", "the reverie",
                       "the history nerd"]},
            {"label": "b) Characters – I need to connect with the people.",
             "types": ["the hopeless romantic", "melancholic ruminator"]},
            {"label": "c) Both are equally important.",
             "types": ["the geeky chap", "the yearner", "the literature sage"]},
            {"label": "d) No preference.", "types": []},
        ]
    },
    {
        "id": 7,
        "question": "You have 30 seconds to pick a book. You can only read the first sentence, which book are you choosing?",
        "options": [
            {
                "label": "a) The old gods stirred in their slumber, for when they are disturbed, the forests sense their presence. Beware, since the trees always listen.",
                "types": ["the tale whisperer"]},
            {
                "label": "b) The last message from Earth blinked out just as the Stardust cleared Mars's orbit, leaving humanity’s fate in the trembling hands of a skeleton crew.",
                "types": ["the geeky chap"]},
            {
                "label": "c) I'd always thought my small town was boring until the new guy, with eyes like chipped ice and a secret he clearly carried, walked into my biology class.",
                "types": ["the yearner", "the hopeless romantic", "the leering diva"]},
            {
                "label": "d) The muffled scream from the apartment across the hall was the last thing she expected to hear on a Tuesday morning, especially since the tenant had been dead for a week.",
                "types": ["the plot pilot", "the deducer dudette"]},
            {
                "label": "e) My therapist said writing would help, but all I've got so far is a blank page and the lingering taste of yesterday's bad decisions.",
                "types": ["the literature sage", "melancholic ruminator"]},
            {
                "label": "f) The crown a cold weight, King Alaric watched his army stir beneath a sky threatening dawn and war, each soldier a life wagered on his command.",
                "types": ["the history nerd"]},
        ]
    },
    {
        "id": 8,
        "question": "If a book disappoints you, you feel:",
        "options": [
            {"label": "a) Frustrated that you wasted your time.", "types": ["the growth guru", "the chill guy"]},
            {"label": "b) Sad, like a friend let you down.", "types": ["the hopeless romantic", "the yearner"]},
            {"label": "c) Curious about why it didn't work for you.", "types": ["the literature sage", "the teagan"]},
            {"label": "d) Indifferent, and just move on to the next.",
             "types": ["the jack of all trades", "the workaholic"]},
        ]
    },
    {
        "id": 9,
        "question": "Which main character would you relate to the most?",
        "options": [
            {
                "label": "a) A young person who tries to navigate life through the ups and downs, emotional rollercoasters and challenging encounters.",
                "types": ["the hopeless romantic", "the reverie", "the yearner"]},
            {
                "label": "b) A passionate woman trying to find love in life while searching for a meaning and taking chances about a stranger that will drastically alter her life.",
                "types": ["the leering diva", "the hopeless romantic"]},
            {
                "label": "c) A humanoid exploring the unfamiliar culture of the unknown new world, where everything is alien and the only thing that remains from the past is a cryptic signal received from their homeland.",
                "types": ["the geeky chap", "the deducer dudette"]},
            {"label": "d) Forgotten son of a pharaoh who was raised by a farmer family.",
             "types": ["the history nerd"]},
            {"label": "e) A forest nymphet, whose world is now threatened by a stranger doing forbidden magic.",
             "types": ["the tale whisperer"]},
            {
                "label": "f) A revolutionary figure, on the verge of a new Age, battling silent combats against the system.",
                "types": ["the history nerd", "the contemplator"]},
        ]
    },
    {
        "id": 10,
        "question": "You could not finish a book, and you put it down. What was the main reason? (pick 3 the most)",
        "options": [
            {"label": "a) Predictable plot", "types": ["the deducer dudette", "the plot pilot"]},
            {"label": "b) Shallow/flat characters", "types": ["melancholic ruminator", "the literature sage"]},
            {"label": "c) Unlikeable characters", "types": ["the leering diva", "the hopeless romantic"]},
            {"label": "d) Poor writing",
             "types": ["the literature sage", "the geeky chap", "the tale whisperer", "the history nerd",
                       "the teagan"]},
            {"label": "e) Dense writing", "types": ["the chill guy", "the yearner", "the reverie"]},
            {"label": "f) Gore/horror", "types": ["the reverie", "the yearner", "the thriller seeker"]},
            {"label": "g) Lost interest",
             "types": ["the jack of all trades", "the joyful activist", "the workaholic", "the growth guru",
                       "the chill guy"]},
        ],
        "multiple": True,
        "max_select": 3
    },
    {
        "id": 11,
        "question": "If you had the chance to fight against something in the world, what would it be?",
        "options": [
            {"label": "a) Climate change.", "types": ["the joyful activist"]},
            {"label": "b) My inner demons", "types": ["melancholic ruminator", "the growth guru"]},
            {"label": "c) The system. Revolution will rise.", "types": ["the contemplator"]},
            {"label": "d) The stock market.", "types": ["the workaholic"]},
            {"label": "e) Incurable diseases.", "types": ["the chill guy", "the hopeless romantic"]},
        ]
    },
    {
        "id": 12,
        "question": "Which gift would you appreciate most?",
        "options": [
            {"label": "a) A rare, first-edition history book", "types": ["the history nerd"]},
            {"label": "b) A signed copy of a the poetry collection", "types": ["the teagan"]},
            {"label": "c) A fan-merch or gaming accessory", "types": ["the geeky chap"]},
            {"label": "d) A handmade eco-friendly product", "types": ["the joyful activist"]},
            {"label": "e) Escape room tickets", "types": ["the deducer dudette", "the thriller seeker"]},
            {"label": "f) Scented candles and incense sticks", "types": ["the hopeless romantic", "the yearner"]},
        ]
    },
    {
        "id": 13,
        "question": "Which movie excites you the most?",
        "options": [
            {"label": "a) Oppenheimer (A movie about the famous physicist, inventor of the atomic bomb)",
             "types": ["the history nerd", "the geeky chap"]},
            {
                "label": "b) A Quiet Place (A family must live in complete silence to avoid deadly creatures that hunt by sound, struggling to survive in a post-apocalyptic world.)",
                "types": ["the thriller seeker"]},
            {
                "label": "c) Deadpool and Wolverine (When the anti-hero Deadpool disrupts the multiverse, he joins forces with a reluctant Wolverine to battle new threats and rewrite both their fates.)",
                "types": ["the chill guy"]},
            {
                "label": "d) The Substance (A mysterious new product that promises perfection spirals into a visceral nightmare, revealing the grotesque cost of transforming the self.)",
                "types": ["the contemplator"]},
            {
                "label": "e) Pride and Prejudice(The turbulent relationship between Elizabeth Bennet, the daughter of a country gentleman, and Fitzwilliam Darcy, a rich aristocratic landowner)",
                "types": ["the hopeless romantic"]},
            {
                "label": "f) Seven(Taking place in a nameless city, Se7en follows the story of two homicide detectives tracking down a sadistic serial killer who chooses his victims according to the seven deadly sins.)",
                "types": ["the deducer dudette"]},
        ]
    },
    {
        "id": 14,
        "question": "If you were to replace someone (fiction/real alive/dead) for one day who would that be?",
        "options": [
            {"label": "a) Legolas", "types": ["the tale whisperer", "the reverie"]},
            {"label": "b) Nelson Mandela", "types": ["the contemplator", "the joyful activist", "the history nerd"]},
            {"label": "c) Carl Sagan", "types": ["the contemplator", "the geeky chap"]},
            {"label": "d) Sherlock Holmes", "types": ["the deducer dudette", "the thriller seeker"]},
            {"label": "e) Kate Middleton",
             "types": ["the hopeless romantic", "the leering diva", "the tale whisperer"]},
            {"label": "f) Jeff Bezos", "types": ["the growth guru", "the workaholic"]},
            {"label": "g) Alexander The Great", "types": ["the history nerd"]},
        ]
    },
    {
        "id": 15,
        "question": "Other than reading books, what do you do in your spare time?",
        "options": [
            {"label": "a) Thrifting for hidden gems", "types": ["the joyful activist"]},
            {"label": "b) Gaining knowledge for future business ventures", "types": ["the workaholic"]},
            {"label": "c) Putting together challenging puzzles", "types": ["the deducer dudette"]},
            {"label": "d) Relaxing and doing self care", "types": ["the chill guy", "the growth guru"]},
            {"label": "e) Writing fan fiction and reading fan theories",
             "types": ["the geeky chap", "the leering diva", "the reverie", "the yearner"]},
        ]
    },
]

# app_vol3.py dosyanıza eklenecek tam READER_TYPE_INFO sözlüğü

READER_TYPE_INFO = {
    "the contemplator": {
        "name": "🧠 The Contemplator",
        "description": "You’re deep, thoughtful, and love books that challenge your beliefs or stretch your worldview. You’re the person who pauses mid-chapter to jot down a profound quote or question the nature of existence.",
        "preferred_genres": ["political", "philosophy", "science"]
    },
    "the reverie": {
        "name": "🌙 The Reverie",
        "description": "A dreamer at heart, you crave stories that sweep you away into magical lands, epic quests, or swoon-worthy romances. Reality’s nice — but imagination is better.",
        "preferred_genres": ["action-adventure", "fantasy-fiction", "mythology", "young-adult", "romance"]
    },
    "the tale whisperer": {
        "name": "📚 The Tale Whisperer",
        "description": "You live for beautifully told stories. Whether it’s dragons, daring escapes, or heartfelt journeys, you want to feel deeply and believe wildly.",
        "preferred_genres": ["action-adventure", "fantasy-fiction", "romance", "feel-good", "fantasy"]
    },
    "the plot pilot": {
        "name": "🧭 The Plot Pilot",
        "description": "You want twists! Turns! Thrills! You don’t read — you navigate. You crave high-stakes drama and juicy mysteries with every chapter keeping you guessing.",
        "preferred_genres": ["action-adventure", "romance", "mystery", "drama", "bestseller", "suspense"]
    },
    "melancholic ruminator": {
        "name": "🌧 Melancholic Ruminator",
        "description": "You're introspective, a quiet observer of life’s bittersweet complexities. You love characters who reflect, break, rebuild — and sometimes just... feel.",
        "preferred_genres": ["classics", "drama", "contemporary", "poetry"]
    },
    "the hopeless romantic": {
        "name": "💞 The Hopeless Romantic",
        "description": "You're a softie — and proud of it. You adore love stories that make your heart flutter and characters that feel like soulmates. Happy tears? Yes, please.",
        "preferred_genres": ["romance", "drama", "feel-good", "spiritual-religious"]
    },
    "the leering diva": {
        "name": "💋 The Leering Diva",
        "description": "Drama? Scandal? Forbidden passion? You’re here for it. You love your fiction with flair, seduction, and a sprinkle of chaos.",
        "preferred_genres": ["fantasy-fiction", "romance", "drama", "erotica", "bestseller"]
    },
    "the workaholic": {
        "name": "💼 The Workaholic",
        "description": "You read like you work — with purpose. Self-growth, big ideas, and a hunger for knowledge guide your shelves. Hustle meets hardcover.",
        "preferred_genres": ["political", "business-finance", "personal-development", "health-and-nutrition"]
    },
    "the teagan": {
        "name": "✒️ The Teagan",
        "description": "You’re poetic, a little nostalgic, and a lover of literature’s quietest moments. The world slows down when you read — and that’s just how you like it.",
        "preferred_genres": ["classics", "romance", "drama", "poetry"]
    },
    "the history nerd": {
        "name": "🏛 The History Nerd",
        "description": "You’re basically a time traveler with a library card. Whether it's pharaohs, philosophers, or folklore, you want to know what came before — in detail.",
        "preferred_genres": ["historical-fiction", "fantasy-fiction", "mythology", "classics", "history"]
    },
    "the growth guru": {
        "name": "🌿 The Growth Guru",
        "description": "You’re here to evolve. Books are your teachers, and you’re always flipping pages on your journey toward inner peace, deeper purpose, and sharper perspective.",
        "preferred_genres": ["spiritual-religious", "philosophy", "personal-development"]
    },
    "the joyful activist": {
        "name": "✊ The Joyful Activist",
        "description": "You believe books can change the world — and you. You read with your heart and your fists, inspired by justice, humanity, and voices that demand to be heard.",
        "preferred_genres": ["spiritual-religious", "philosophy", "arts", "health-and-nutrition", "feminism"]
    },
    "the jack of all trades": {
        "name": "🎨 The Jack of All Trades",
        "description": "You're curious about everything — and you read like it. One day it's science, the next day it's sculpture, then suddenly it's Norse mythology. You're a genre globetrotter.",
        "preferred_genres": ["mythology", "philosophy", "arts", "science"]
    },
    "the literature sage": {
        "name": "🧐 The Literature Sage",
        "description": "A lover of depth, meaning, and language itself, you thrive on prose that stings, sings, and stays with you. You quote Camus in casual conversation.",
        "preferred_genres": ["dystopian", "classics", "contemporary", "poetry"]
    },
    "the geeky chap": {
        "name": "🧪 The Geeky Chap",
        "description": "You’re the first to pre-order a new space opera or annotate a time travel paradox. Smart, loyal, and always one plot twist ahead.",
        "preferred_genres": ["science-fiction", "fantasy-fiction", "mystery", "science"]
    },
    "the chill guy": {
        "name": "😎 The Chill Guy",
        "description": "Reading is your escape. You like stories that flow easily but still pack a punch. You're not high-maintenance — just highly readable.",
        "preferred_genres": ["action-adventure", "crime", "romance", "feel-good", "bestseller"]
    },
    "the yearner": {
        "name": "💫 The Yearner",
        "description": "You want to feel something. Deep connection, big dreams, the ache of what-if — that’s your bookish bread and butter.",
        "preferred_genres": ["fantasy-fiction", "young-adult", "romance", "feel-good", "bestseller"]
    },
    "the thriller seeker": {
        "name": "🔪 The Thriller Seeker",
        "description": "You chase danger from the safety of your blanket. Crime scenes, monsters, psychological chaos — nothing’s too dark or twisted for you.",
        "preferred_genres": ["horror", "mystery", "true-crime", "gore", "erotica"]
    },
    "the deducer dudette": {
        "name": "🕵️ The Deducer Dudette",
        "description": "You're the armchair detective of your friend group. You notice everything, love a puzzle, and crave the thrill of the final reveal.",
        "preferred_genres": ["crime", "thriller", "mystery", "true-crime", "gore"]
    }
}

# --- Rotalar (Sayfa Yönlendirmeleri) ---
@app.route('/')
def home():
    return render_template('home.html')


@app.route('/quiz')
def quiz():
    return render_template('quiz_form_vol2.html', questions=quiz_questions)


@app.route('/result', methods=['POST'])
def result():
    scores = {ptype: 0 for ptype in READER_TYPE_INFO.keys()}

    for q in quiz_questions:
        qid = str(q['id'])
        if q.get("multiple"):
            selected_indices = request.form.getlist(f"question_{qid}")
            if "max_select" in q and len(selected_indices) > q["max_select"]:
                selected_indices = selected_indices[:q["max_select"]]

            for idx_str in selected_indices:
                try:
                    idx = int(idx_str)
                    if 0 <= idx < len(q['options']):
                        option = q['options'][idx]
                        for ptype in option['types']:
                            if ptype in scores:
                                scores[ptype] += 1
                except ValueError:
                    pass
        else:
            selected_idx_str = request.form.get(f"question_{qid}")
            if selected_idx_str is not None:
                try:
                    idx = int(selected_idx_str)
                    if 0 <= idx < len(q['options']):
                        option = q['options'][idx]
                        for ptype in option['types']:
                            if ptype in scores:
                                scores[ptype] += 1
                except ValueError:
                    pass

    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_3 = sorted_scores[:3]

    return render_template('quiz_result_vol3.html', top_types=top_3, reader_type_info=READER_TYPE_INFO)

# BU LİSTE, TÜM KARAKTERLER İÇİN GEÇERLİ OLAN, GENEL FİLTREDİR.
# Çocuk kitapları, teknik raporlar gibi evrensel olarak istenmeyen etiketleri içerir.
GLOBAL_EXCLUDED_TAGS = [
    # Teknik ve Ders Kitapları
    "textbooks", "guides", "evaluation", "radiographic-positioning",

    # Devlet ve Hukuk Metinleri
    "government-publication", "law", "audit", "treaties", "regulations",

    # Çocuk Kitapları (YA ile karışmayacak kadar net olanlar)
    "picture-books", "the-very-hungry-caterpillar",

    # Diğer Alakasızlar
    "catalogue", "sermons"
]

# BU SÖZLÜK, HER KARAKTERİN KENDİNE ÖZGÜ ZAYIF NOKTALARINI HEDEFLER.
CHARACTER_SPECIFIC_EXCLUSIONS = {
    "the contemplator": [
        "fiction", "fantasy", "horror", "romance", "manga", "comics"
    ],
    "the reverie": [
        "non-fiction", "history", "criticism", "biography", "science-fiction"
    ],
    "the tale whisperer": [
        "non-fiction", "poetry", "philosophy", "thriller", "mystery"
    ],
    "the plot pilot": [
        "non-fiction", "philosophy", "science", "poetry", "children"
    ],
    "melancholic ruminator": [
        "young-adult", "children", "humor", "adventure"
    ],
    "the hopeless romantic": [
        "thriller", "mystery", "crime", "horror", "science-fiction", "fantasy",
        "non-fiction", "philosophy", "history", "political", "paranormal"
    ],
    "the leering diva": [
        "non-fiction", "science", "history", "children", "young-adult",
        "science-fiction"
    ],
    "the workaholic": [
        "fiction", "novel", "drama", "poetry", "romance", "fantasy", "mystery",
        "thriller", "horror", "young-adult", "children"
    ],
    "the teagan": [
        "science-fiction", "horror", "mystery", "thriller", "children"
    ],
    "the history nerd": [
        "romance", "young-adult", "children", "erotica", "contemporary"
    ],
    "the growth guru": [
        "fiction", "novel", "drama", "poetry", "horror", "romance", "fantasy"
    ],
    "the joyful activist": [
        "thriller", "crime", "mystery", "horror", "erotica"
    ],
    "the jack of all trades": [
        "romance", "erotica", "children", "young-adult"
    ],
    "the literature sage": [
        "young-adult", "children", "dork-diaries", "romance", "adventure"
    ],
    "the geeky chap": [
        "romance", "drama", "poetry", "biography", "history", "non-fiction", "erotica"
        # Manga ve Comics bu karakter için engellenmedi.
    ],
    "the chill guy": [
        "non-fiction", "philosophy", "classics", "poetry", "tragedy", "history",
        "textbooks"
    ],
    "the yearner": [
        "non-fiction", "history", "criticism", "philosophy", "thriller", "horror",
        "inspirational", "religion"
    ],
    "the thriller seeker": [
        "non-fiction", "biography", "history", "romance", "poetry", "classics", "arts"
    ],
    "the deducer dudette": [
        "fantasy", "manga", "romance", "biography", "history", "non-fiction",
        "poetry", "arts", "politics"
    ]
}

# app_1_one_combination.py dosyanıza ekleyin veya mevcut olanı bununla değiştirin.

TAG_WEIGHTS = {
    "the contemplator": {
        "philosophy": 3, "science": 3, "political": 2,
        "fiction": -3, "novel": -3, "romance": -5, "fantasy": -5, "young-adult": -5
    },
    "the reverie": {
        "young-adult": 3, "fantasy-fiction": 3, "action-adventure": 2, "romance": 1,
        "mythology": 1, "feel-good": 1, "fantasy": 1,
        "classics": -2, "philosophy": -3, "poetry": -3, "non-fiction": -5, "drama": -1
    },
    "the tale whisperer": {
        "fantasy": 3, "fantasy-fiction": 3, "action-adventure": 2, "feel-good": 2, "romance": 1,
        "non-fiction": -5, "thriller": -2, "mystery": -2, "poetry": -3
    },
    "the plot pilot": {
        "mystery": 3, "suspense": 3, "thriller": 3, "action-adventure": 2, "crime": 2,
        "bestseller": 1, "drama": 1,
        "philosophy": -3, "poetry": -3, "non-fiction": -5, "classics": -1
    },
    "melancholic ruminator": {
        "classics": 3, "poetry": 3, "drama": 2, "contemporary": 1, "philosophy": 1,
        "humor": -2, "action-adventure": -3, "young-adult": -3, "feel-good": -5
    },
    "the hopeless romantic": {
        "romance": 3, "feel-good": 3, "drama": 1,
        "thriller": -5, "mystery": -5, "crime": -5, "horror": -5, "philosophy": -3,
        "non-fiction": -5, "action-adventure": -4
    },
    "the leering diva": {
        "erotica": 3, "romance": 3, "drama": 2, "fantasy-fiction": 1, "bestseller": 1,
        "non-fiction": -5, "science": -4, "history": -3, "children": -5, "young-adult": -2
    },
    "the workaholic": {
        "personal-development": 3, "business-finance": 3, "health-and-nutrition": 2, "political": 1,
        "fiction": -5, "novel": -5, "drama": -5, "poetry": -5, "romance": -5, "fantasy": -5
    },
    "the teagan": {
        "poetry": 3, "classics": 3, "drama": 2, "romance": 2,
        "science-fiction": -3, "horror": -2, "mystery": -3, "action-adventure": -3
    },
    "the history nerd": {
        "history": 3, "historical-fiction": 3, "classics": 2, "mythology": 1,
        "romance": -3, "young-adult": -3, "contemporary": -4, "erotica": -5
    },
    "the growth guru": {
        "personal-development": 3, "philosophy": 2, "spiritual-religious": 1,
        "fiction": -5, "novel": -5, "fantasy": -5, "romance": -5
    },
    "the joyful activist": {
        "feminism": 3, "arts": 2, "health-and-nutrition": 2, "philosophy": 1,
        "spiritual-religious": 1,
        "thriller": -4, "crime": -4, "horror": -5, "erotica": -5
    },
    "the jack of all trades": {
        "science": 3, "philosophy": 3, "arts": 2, "history": 1, "mythology": 1,
        "romance": -4, "erotica": -5, "young-adult": -3
    },
    "the literature sage": {
        "classics": 3, "poetry": 2, "contemporary": 2, "dystopian": 2, "drama": 1,
        "young-adult": -4, "children": -5, "adventure": -3, "romance": -2
    },
    "the geeky chap": {
        "science-fiction": 3, "science": 2, "fantasy-fiction": 2, "mystery": 1, "manga": 1,
        "romance": -3, "drama": -3, "poetry": -4, "non-fiction": -2, "erotica": -5, "philosophy": -5
    },
    "the chill guy": {
        "feel-good": 3, "action-adventure": 2, "bestseller": 2, "crime": 1, "romance": 1,
        "non-fiction": -3, "philosophy": -4, "classics": -2, "poetry": -4, "tragedy": -5
    },
    "the yearner": {
        "romance": 3, "young-adult": 3, "feel-good": 2, "fantasy-fiction": 1, "bestseller": 1,
        "non-fiction": -5, "history": -4, "philosophy": -4, "thriller": -3
    },
    "the thriller seeker": {
        "horror": 3, "thriller": 3, "mystery": 2, "crime": 2, "true-crime": 2, "gore": 1,
        "erotica": 1,
        "romance": -3, "feel-good": -5, "non-fiction": -2, "biography": -2
    },
    "the deducer dudette": {
        "true-crime": 3, "mystery": 3, "crime": 3, "thriller": 2, "suspense": 2,
        "fantasy": -4, "romance": -4, "biography": -3, "history": -3, "non-fiction": -2
    }
}

# app_1_one_combination.py -> inside the @app.route('/recommendations') function

# app_1_one_combination.py dosyasındaki mevcut /recommendations fonksiyonunu bununla değiştirin.

# app_1_one_combination.py dosyasındaki /recommendations rotasını bununla değiştirin.

@app.route('/recommendations')
def recommendations():
    user_reader_type = request.args.get('type')
    # Kontrolü ve veri alımını yeni READER_TYPE_INFO yapısından yapıyoruz
    if not user_reader_type or user_reader_type not in READER_TYPE_INFO:
        return "Geçersiz okuyucu tipi veya tip belirtilmedi. <a href='/'>Ana Sayfa</a>"

    preferred_genres = READER_TYPE_INFO[user_reader_type]['preferred_genres']

    # Filtreleme ve ağırlıklandırma mantığı aynı kalıyor
    final_excluded_tags = set(GLOBAL_EXCLUDED_TAGS)
    specific_exclusions = CHARACTER_SPECIFIC_EXCLUSIONS.get(user_reader_type, [])
    final_excluded_tags.update(specific_exclusions)

    character_weights = TAG_WEIGHTS.get(user_reader_type, {})

    # Fonksiyon çağrısı aynı kalıyor (sadece import ettiğimiz dosyanın adı değişti)
    recommended_books = get_recommendations_with_weighted_scoring(
        preferred_genres,
        final_limit=12,
        excluded_tags=list(final_excluded_tags),
        tag_weights=character_weights
    )

    # Bu rota ortak 'recommendations.html' dosyasını kullanabilir, değişiklik gerekmez.
    return render_template('recommendations.html', reader_type=user_reader_type, books=recommended_books)


# app_vol3.py dosyasının sonuna (if __name__...'den önce) ekleyin

# --- KULLANICI YÖNETİMİ ROTALARI ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Formdan gelen e-posta ile kullanıcıyı veritabanında ara
        user = User.query.filter_by(email=request.form.get('email')).first()
        # Kullanıcı varsa ve şifre doğruysa...
        if user and user.check_password(request.form.get('password')):
            login_user(user)  # Kullanıcının oturumunu başlat
            return redirect(url_for('dashboard'))  # Başarılı giriş sonrası panoya yönlendir
        else:
            flash('Invalid email or password')  # Hata mesajı göster
    # GET isteği için veya hatalı giriş sonrası login sayfasını göster
    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')

        # Bu e-posta daha önce alınmış mı diye kontrol et
        if User.query.filter_by(email=email).first():
            flash('Email address already exists')
            return redirect(url_for('signup'))

        # Yeni kullanıcıyı oluştur ve veritabanına kaydet
        new_user = User(username=username, email=email)
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        # Kayıt başarılı, şimdi giriş yapsın
        return redirect(url_for('login'))
    # GET isteği için kayıt sayfasını göster
    return render_template('signup.html')


@app.route('/logout')
@login_required  # Bu sayfaya sadece giriş yapmış kullanıcılar erişebilir
def logout():
    logout_user()  # Kullanıcının oturumunu sonlandır
    return redirect(url_for('home'))  # Ana sayfaya yönlendir


@app.route('/dashboard')
@login_required  # Bu sayfaya sadece giriş yapmış kullanıcılar erişebilir
def dashboard():
    # Bu sayfayı daha sonra dolduracağız.
    # Şimdilik sadece giriş yapan kullanıcının adını gösterelim.
    return render_template('dashboard.html', name=current_user.username)



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')