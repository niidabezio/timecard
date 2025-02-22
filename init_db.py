from app import app, db

# アプリのコンテキスト内でデータベースを作成
with app.app_context():
    db.create_all()
    print("✅ データベースを初期化しました！")
