import json

def writeActivityDict(_activity_list):
    full_data = []
    for activity in _activity_list:
        full_col_list = []
        for key, value in activity.to_dict().items():
            full_col_list.append(key)
        new_data = [activity.to_dict().get(x) for x in full_col_list]
        full_data.append(new_data)

        with open("ref/activity_dict.json", "w", encoding='utf-8') as file:
            json.dump(activity.to_dict(), file, ensure_ascii=False, indent=4)
        break


def writeShoeData(_athlete):
    athlete_shoes = _athlete.shoes
    shoe_data = []
    shoe_id_list = []
    for shoe in athlete_shoes:
        shoe_dict = shoe.to_dict()
        shoe_data.append(shoe_dict)
        shoe_id_list.append(shoe.to_dict()['id'])
        # shoe_id_list.append(shoe['id'])
    with open("ref/shoe_data.json", "w", encoding='utf-8') as file:
        json.dump(shoe_data, file, ensure_ascii=False, indent=4)

    return shoe_id_list