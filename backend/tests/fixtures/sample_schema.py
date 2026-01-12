SAMPLE_SCHEMA: dict = {
    "tables": {
        "customers": {
            "columns": {
                "id": {"type": "uuid", "nullable": False, "primary_key": True, "default": None},
                "name": {
                    "type": "character varying",
                    "nullable": False,
                    "primary_key": False,
                    "default": None,
                },
                "email": {
                    "type": "character varying",
                    "nullable": False,
                    "primary_key": False,
                    "default": None,
                },
                "country": {
                    "type": "character varying",
                    "nullable": True,
                    "primary_key": False,
                    "default": None,
                },
                "created_at": {
                    "type": "timestamp with time zone",
                    "nullable": False,
                    "primary_key": False,
                    "default": "now()",
                },
            },
            "foreign_keys": [],
        },
        "orders": {
            "columns": {
                "id": {"type": "uuid", "nullable": False, "primary_key": True, "default": None},
                "customer_id": {
                    "type": "uuid",
                    "nullable": False,
                    "primary_key": False,
                    "default": None,
                },
                "total_amount": {
                    "type": "numeric",
                    "nullable": False,
                    "primary_key": False,
                    "default": None,
                },
                "status": {
                    "type": "character varying",
                    "nullable": False,
                    "primary_key": False,
                    "default": None,
                },
                "created_at": {
                    "type": "timestamp with time zone",
                    "nullable": False,
                    "primary_key": False,
                    "default": "now()",
                },
            },
            "foreign_keys": [
                {"from_column": "customer_id", "to_table": "customers", "to_column": "id"}
            ],
        },
        "products": {
            "columns": {
                "id": {"type": "uuid", "nullable": False, "primary_key": True, "default": None},
                "name": {
                    "type": "character varying",
                    "nullable": False,
                    "primary_key": False,
                    "default": None,
                },
                "price": {
                    "type": "numeric",
                    "nullable": False,
                    "primary_key": False,
                    "default": None,
                },
                "category": {
                    "type": "character varying",
                    "nullable": True,
                    "primary_key": False,
                    "default": None,
                },
            },
            "foreign_keys": [],
        },
    }
}
