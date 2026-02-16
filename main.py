from db.table_operations import create_table, delete_table
from db.item_operations import put_item, scan_items, delete_item

# create_table("Users")
# put_item("Users", {"id": "1", "name": "Damien"})
# delete_item("Users", {"id": "1"})
# print(scan_items("Users"))
delete_table("Users")
