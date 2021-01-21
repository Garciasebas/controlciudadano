"""
This dags downloads the pdf from the contralory page.

There are more that 800.000 files, so we need to download then in batches, and if possible, don't download it all.

1. To allow parallelization we can use the id of the file
2. To prevent re-downloads we can request a HEAD and get the file size and check with the local copy
3. To allow multiple versions of the same id, we will store the data in another table win this format:

Table `staging.djbr_downloaded_files`:
 * id: id of the table staging.djbr_raw_data
 * file_size: size of the downloaded file
 * hash: hash of the file
 * file_name: the name of the file in our local storage ("hash_document.pdf")

"""
import os
import tempfile
from datetime import datetime
from datetime import timedelta
from typing import Dict, Union, List

from airflow.hooks.postgres_hook import PostgresHook
from airflow.models import DAG, Variable
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.postgres_operator import PostgresOperator
from airflow.operators.python_operator import PythonOperator
from airflow.utils.dates import days_ago

from ds_table_operations import calculate_hash_of_file
from file_system_helper import move
from network_operators import download_file, get_head

try:
    target_dir = os.path.join(Variable.get("CGR_PDF_FOLDER"))
except KeyError:
    target_dir = os.path.join(os.sep, "tmp", "contralory", "raw")

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email": ["arturovolpe@gmail.com"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retry_delay": timedelta(hours=1),
    "params": {
        "url": "https://portaldjbr.contraloria.gov.py/portal-djbr/api/consulta/descargarpdf/",
        "target_dir": target_dir
    },
}

dag = DAG(
    dag_id="contralory_declaration_download_pdfs",
    default_args=default_args,
    description="Downloads links from https://portaldjbr.contraloria.gov.py/ and stores it in a table",
    start_date=days_ago(1),
    schedule_interval=timedelta(weeks=1),
)


def list_navigator(id_ends_with: int, cursor: any):
    """
    Fetch a flow of values that ends with a specific number

    :param id_ends_with: the last digit of the id
    :return: yields a page, ends when the list is an empty array
    """
    batch_size = 2000
    should_continue = True
    max_iterations = 100 # to prevent a infinite loop
    current_iter = 1

    while should_continue:
        cursor.execute("""
        SELECT 
            raw.id, 
            raw.cedula, 
            raw.remote_id, 
            jsonb_agg(jsonb_build_object(
                'file_size', COALESCE(downloaded.file_size, 0),
                'hash', COALESCE(downloaded.hash, '')
            )) as downloaded_files
        FROM staging.djbr_raw_data raw
        LEFT JOIN staging.djbr_downloaded_files downloaded ON raw.id = downloaded.raw_data_id
        WHERE mod(raw.id, 10) = %s 
          AND downloaded IS NULL -- we should remove this to allow re-download files if changed
        GROUP BY raw.id, raw.cedula, raw.remote_id
        LIMIT %s
        """, [id_ends_with, batch_size])
        # fetchall to dictionary
        desc = cursor.description
        column_names = [col[0] for col in desc]
        to_yield = [dict(zip(column_names, row)) for row in cursor.fetchall()]

        print(f"Fetched {len(to_yield)} from id {id_ends_with}")
        yield to_yield

        current_iter = current_iter + 1
        should_continue = len(to_yield) == 0 or current_iter >= max_iterations


def get_upsert_query() -> str:
    return """
        INSERT INTO staging.djbr_downloaded_files (raw_data_id, file_size, hash, file_name, download_date)
        VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING;
    """


def find_in_list(size: str, data: List[Dict[str, str]]):
    for datum in data:
        if str(datum["file_size"]) == str(size):
            return datum
    return None


def download_pdf(remote_id: str,
                 base_path: str,
                 target_dir: str,
                 already_downloaded: List[Dict[str, any]],
                 temp_dir: str
                 ) -> Union[Dict[str, str], None]:
    """
    Downloads a pdf if necessary and returns the 'hash', 'file_size' and path of the downloaded file

    :param remote_id: the id of the file to download
    :param base_path: the base url to which we will append the remote_id
    :param target_dir: the final folder destination of the file
    :param already_downloaded: data about the previously downloaded files
    :param temp_dir: a temp dir when we can put temporarily files
    :return: a dict with the 'hash', 'file_size' and 'path keys
    """

    final_url = f"{base_path}{remote_id}"
    file_info = get_head(final_url, verify=False)
    file_size = file_info["Content-Length"]
    # We can also check if the file exists in disk and then compare the size
    find_downloaded = find_in_list(file_size, already_downloaded)

    if find_downloaded is not None:
        print(f"The file {final_url} already downloaded")
        # We already has a copy of this file
        return None

    temp_target_path = f"{temp_dir}{remote_id}.pdf"
    download_file(final_url, temp_target_path, False, False)
    file_hash = calculate_hash_of_file(temp_target_path)
    final_name = f"{remote_id}_{file_hash}.pdf"
    final_path = os.path.join(target_dir, final_name)
    move(temp_target_path, final_path)

    return {
        'hash': file_hash,
        'file_size': file_size,
        'file_name': final_name,
        'path': final_path
    }


def do_work(number: int, url: str, target_dir: str):
    print(f"Downloading documents that end with {number} from {url}")

    db_hook = PostgresHook(postgres_conn_id="postgres_default", schema="db")
    db_conn = db_hook.get_conn()
    db_cursor = db_conn.cursor()

    sql = get_upsert_query()

    temp_dir = tempfile.mkdtemp()

    for records in list_navigator(number, db_cursor):
        to_insert = []
        for record in records:
            data = download_pdf(record["remote_id"], url, target_dir, record["downloaded_files"], temp_dir)
            if data is not None:
                to_insert.append([
                    record["id"],
                    data["file_size"],
                    data["hash"],
                    data["file_name"],
                    datetime.now()
                ])

        print(f"Sending {len(to_insert)} for upsert")
        db_cursor.executemany(sql, to_insert)
        db_conn.commit()


with dag:
    launch = DummyOperator(task_id="start")
    done = DummyOperator(task_id="done")

    ensure_table_created = PostgresOperator(task_id='ensure_table_created',
                                            sql='''CREATE TABLE IF NOT EXISTS staging.djbr_downloaded_files
                                        (
                                            id              bigserial primary key,
                                            raw_data_id     bigint,
                                            file_size       bigint,
                                            hash            text,
                                            file_name       text,
                                            download_date   timestamp,
                                            CONSTRAINT "djbr_downloaded_files_to_raw_rada" 
                                            FOREIGN KEY(raw_data_id) REFERENCES staging.djbr_raw_data(id)
                                        )
                                        ''')

    # for digit in range(0, 10):
    for digit in range(0, 1):
        # Get list from webpage
        download_number = PythonOperator(
            task_id=f"""download_number_{digit}""",
            python_callable=do_work,
            op_kwargs={
                "number": digit,
                "url": "{{ params.url }}",
                "target_dir": "{{ params.target_dir }}"
            },
        )

        ensure_table_created >> download_number >> done

    launch >> ensure_table_created

if __name__ == "__main__":
    dag.clear(reset_dag_runs=True)
    dag.run()
