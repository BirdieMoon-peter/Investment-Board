from app.core.settings import Settings
from app.db.services import seed_demo_data
from app.db.session import create_db_and_tables, make_engine, make_session



def main() -> None:
    settings = Settings()
    engine = make_engine(settings)
    create_db_and_tables(engine)

    with make_session(engine) as session:
        seed_demo_data(session)


if __name__ == "__main__":
    main()
