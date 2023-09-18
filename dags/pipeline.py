from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
import pandas as pd
import pendulum



with DAG(dag_id="flight-data-pipeline", start_date=pendulum.datetime(year=2023, month=1, day=25, hour=15, minute=45)):

    def clean_countries(**context):
        countries_df = pd.read_csv("gs://europe-west3-composer-env-5968837e-bucket/data/countries_bronze.csv")

        # Remove NaN rows
        countries_df = countries_df[pd.notna(countries_df["dafif_code"])]

        # Drop rows with null values (\N in data) 
        countries_df[countries_df["iso_code"] != "\\N"]

        # Type cast objects to string
        countries_df["name"] = pd.Series(countries_df["name"], dtype="string")
        countries_df["iso_code"] = pd.Series(countries_df["iso_code"], dtype="string")
        countries_df["dafif_code"] = pd.Series(countries_df["dafif_code"], dtype="string")
        countries_df.to_csv("gs://europe-west3-composer-env-5968837e-bucket/data/countries_silver.csv")

    def clean_airlines(**context):
        airlines_df = pd.read_csv("gs://europe-west3-composer-env-5968837e-bucket/data/airlines_bronze.csv")

        # Drop rows with null values (\N in data)
        airlines_df = airlines_df.drop(columns=["alias"])
        airlines_df = airlines_df[airlines_df["icao_code"] != "\\N"]

        # Remove NaN rows
        airlines_df = airlines_df[pd.notna(airlines_df["call_sign"])]
        airlines_df = airlines_df[pd.notna(airlines_df["iata_code"])]

        # Type cast objects to string
        airlines_df["id"] = pd.Series(airlines_df["id"], dtype="int64")
        airlines_df["name"] = pd.Series(airlines_df["name"], dtype="string")
        airlines_df["iata_code"] = pd.Series(airlines_df["iata_code"], dtype="string")
        airlines_df["icao_code"] = pd.Series(airlines_df["icao_code"], dtype="string")
        airlines_df["call_sign"] = pd.Series(airlines_df["call_sign"], dtype="string")
        airlines_df["country"] = pd.Series(airlines_df["country"], dtype="string")
        airlines_df["active"] = pd.Series(airlines_df["active"], dtype="string")
        airlines_df.to_csv("gs://europe-west3-composer-env-5968837e-bucket/data/airlines_silver.csv")

    def clean_routes(**context):
        routes_df = pd.read_csv("gs://europe-west3-composer-env-5968837e-bucket/data/routes_bronze.csv")

        # Drop unnecessary columns
        routes_df = routes_df.drop(columns=["no_of_stops"])

        # Drop rows with null values (\N in data)
        routes_df = routes_df[routes_df["destination_airport_id"] != '\\N']
        routes_df = routes_df[routes_df["source_airport_id"] != '\\N']
        routes_df = routes_df[routes_df["airline_id"] != '\\N']

        # Type cast objects to string
        routes_df["airline"] = pd.Series(routes_df["airline"], dtype="string")
        routes_df["airline_id"] = pd.Series(routes_df["airline_id"], dtype="int64")
        routes_df["source_airport"] = pd.Series(routes_df["source_airport"], dtype="string")
        routes_df["source_airport_id"] = pd.Series(routes_df["source_airport_id"], dtype="int64")
        routes_df["destination_airport"] = pd.Series(routes_df["destination_airport"], dtype="string")
        routes_df["destination_airport_id"] = pd.Series(routes_df["destination_airport_id"], dtype="int64")
        routes_df.to_csv("gs://europe-west3-composer-env-5968837e-bucket/data/routes_silver.csv")

    def join_countries_and_airlines(**context):
        # Load dataframes
        airlines_plus_df = pd.read_csv("gs://europe-west3-composer-env-5968837e-bucket/data/airlines_silver.csv")
        countries_plus_df = pd.read_csv("gs://europe-west3-composer-env-5968837e-bucket/data/countries_silver.csv")
        
        # Join operation in pandas
        join_df = pd.merge(airlines_plus_df, countries_plus_df, left_on="country", right_on="name")
        join_df["country"] = join_df["name_y"]
        join_df["airline"] = join_df["name_x"]

        # Which country has highest number of airlines ?
        num_of_airlines_gby = join_df.groupby("country")["airline"].count()
        num_of_airlines_df = pd.DataFrame(num_of_airlines_gby.items(), columns=["country", "num_of_airlines"])
        num_of_airlines_df.to_csv("gs://europe-west3-composer-env-5968837e-bucket/data/airlines_per_country_gold.csv", index=False)

    def join_airlines_and_routes(**context):
        # Load dataframes
        airlines_plus_df = pd.read_csv("gs://europe-west3-composer-env-5968837e-bucket/data/airlines_silver.csv")
        routes_plus_df = pd.read_csv("gs://europe-west3-composer-env-5968837e-bucket/data/routes_silver.csv")
        
        # Join operation in pandas
        join_df = pd.merge(airlines_plus_df, routes_plus_df, left_on="id", right_on="airline_id")

        # Which airline has highest number of routes ?
        num_of_routes_gby = join_df.groupby("name")["airline_id"].count()
        num_of_routes_df = pd.DataFrame(num_of_routes_gby.items(), columns=["airline", "num_of_routes"])
        num_of_routes_df.to_csv("gs://europe-west3-composer-env-5968837e-bucket/data/routes_per_airline_gold.csv", index=False)

    task_1 = BashOperator(task_id="start", bash_command="echo starting cleaning operations for countries, flights and, routes. ")

    task_2 = PythonOperator(
        task_id="clean_countries",
        python_callable=clean_countries,
        provide_context=True
    )

    task_3 = PythonOperator(
        task_id="clean_airlines",
        python_callable=clean_airlines,
        provide_context=True
    )

    task_4 = PythonOperator(
        task_id="clean_routes",
        python_callable=clean_routes,
        provide_context=True
    )

    task_5 = BashOperator(task_id="join", bash_command="echo Join operations are going to begin")

    task_6 = PythonOperator(
        task_id="join_countries_and_airlines",
        python_callable=join_countries_and_airlines,
        provide_context=True
    )

    task_7 = PythonOperator(
        task_id="join_airlines_and_routes",
        python_callable=join_airlines_and_routes,
        provide_context=True
    )

    task_8 = BashOperator(task_id="end", bash_command="echo Gold tables are successfully generated")

    # Run clean operations then join operations in parallel
    task_1 >> [task_2, task_3, task_4] >> task_5 >> [task_6, task_7] >> task_8
