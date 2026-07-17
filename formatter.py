def format_system(system):
    """Converts a raw system dict from generator.py into the JSON output schema."""
    star = system["star"]

    output = {
        "key":            star["key"],
        "name":           star["name"],
        "class":          star["class"],
        "color":          star["color"],
        "Star_Mo":        star["Star_Mo"],
        "Star_Ro":        star["Star_Ro"],
        "Star_km":        star["Star_km"],
        "Star_Lo":        star["Star_Lo"],
        "Star_T":         star["Star_T"],
        "Star_Metallicity": star["Star_Metallicity"],
        "Star_Mbol":      star["Star_Mbol"],
        "Star_Mv":        star["Star_Mv"],
        "Star_SOI":       star["Star_SOI"],
        "Star_Position":  star["Star_Position"],
        "zones":          star["zones"],
        "bodies":         [format_body(body) for body in system["bodies"]],
        "inner_belt":     [format_body(d) for d in system["inner_belt"]],
        "outer_belt":     [format_body(d) for d in system["outer_belt"]],
    }
    return output

def format_body(body):
    """Converts a raw body dict from generator.py into the JSON output schema."""
    return {
        "name": body["name"],
        "data": {
            "type":           body["type"],
            "subclass":       body.get("subclass"),
            "mass":           {"value": body["mass"],           "unit": "Me"},
            "radius":         {"value": body["radius"],         "unit": "Re"},
            "volume":         {"value": body["volume"],         "unit": "km^3"},
            "density":        {"value": body["density"],        "unit": "kg/km^3"},
            "SMA":            {"value": body["SMA"],            "unit": "AU"},
            "surface_gravity":{"value": body["surface_gravity"],"unit": "m/s^2"},
        },
        "core":        body["core"],
        "orbit":       body["orbit"],
        "atmosphere":  body["atmosphere"],
        "tectonics":   body["tectonics"],
        "habitability":body["habitability"],
        "moons":       body.get("moons", []),
        "rings":       body.get("rings", {"present": False, "roche_failures": 0}),
    }
