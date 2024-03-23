import requests
from sql import add_project
from db import get_db_connection


def worker(id, project_id):
    # print(project_id)

    url = f"http://127.0.0.1:8080/get_children?item_id={id}"
    response = requests.request("GET", url)
    data = response.json()
    conn = get_db_connection()
    cursor = conn.cursor()
    for item in data:
        if "isFolder" not in item:
            break
        if item["isFolder"] == True:
            worker(item["id"], project_id)
        else:
            id = item["id"]
            name = item["name"]
            # print(id, name, project_id)
            try:
                cursor.execute(
                    f"INSERT INTO file (id, name, project_id, visibility_flag) VALUES ('{id}', '{name}', '{project_id}', true);"
                )
            except Exception as e:
                print(e)
    conn.commit()
    cursor.close()
    conn.close()


def update_file(id, project_id):
    worker(id, project_id)
    print("File updated successfully!")


if __name__ == "__main__":
    project_id = "01PWT4KLWBBFX6P4FNPVA2CVJNZRFMPMV4"
    # add_project()
    update_file(project_id, project_id)

# project2 = "01PWT4KLR7T7PMAKSIPJALGQEDCEF63UDJ"
# project1 = "01PWT4KLWBBFX6P4FNPVA2CVJNZRFMPMV4"
