import os
import sqlite3


def setup_database() -> str:
    db_path = os.path.join(os.path.dirname(__file__), "colegio.db")
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS estudiantes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            asistencias REAL NOT NULL,
            nota_matematica REAL NOT NULL,
            nota_lenguaje REAL NOT NULL,
            participacion REAL NOT NULL
        )
        """
    )

    connection.commit()
    connection.close()
    return db_path


if __name__ == "__main__":
    path = setup_database()
    print(f"Base de datos creada/configurada en: {path}")
