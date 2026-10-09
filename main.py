"""Точка входа: создание таблиц, загрузка данных и вывод результатов."""

from db_manager import DBManager, create_tables, get_connection, load_aircraft, load_countries


def main() -> None:
    """Запускает загрузку данных и демонстрирует работу DBManager."""
    connection = get_connection()

    try:
        print("Создание таблиц...")
        create_tables(connection)

        print("Загрузка данных о странах...")
        load_countries(connection)

        print("Загрузка данных о самолётах...")
        load_aircraft(connection)
    finally:
        connection.close()

    manager = DBManager()

    try:
        print("\nСтраны и количество самолётов:")
        for country, aircraft_count in manager.get_countries_and_aeroplanes_count():
            print(f"{country}: {aircraft_count}")

        average_speed = manager.get_avg_speed()
        print(f"\nСредняя скорость самолётов: {average_speed:.2f}")

        print("\nСамолёты со скоростью выше средней (первые 10):")
        for aircraft in manager.get_aeroplanes_with_higher_speed()[:10]:
            print(aircraft)

        print("\nСамолёты с 'ACA' в позывном:")
        for aircraft in manager.get_aeroplanes_with_keyword("ACA"):
            print(aircraft)
    finally:
        manager.close()


if __name__ == "__main__":
    main()